"""
Taobao (淘宝) crawler for searching and extracting store information.
Web version - keeps browser open to maintain login session.
"""

import asyncio
import re
import os
from typing import List, Optional
from urllib.parse import quote, urlparse, parse_qs

from .base import BaseCrawler, CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class TaobaoCrawler(BaseCrawler):
    """Crawler for Taobao platform - stores and products"""
    
    platform = Platform.TAOBAO
    supported_types = [ContentType.STORE, ContentType.PRODUCT]
    
    # Taobao URLs
    BASE_URL = "https://www.taobao.com"
    SEARCH_URL = "https://s.taobao.com/search"
    
    # Class-level browser to keep it open across crawls
    _shared_context = None
    _shared_page = None
    _shared_playwright = None
    
    def __init__(self):
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._keep_browser_open = True  # Keep browser open after crawl
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser with persistent profile to save login"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        # Reuse existing browser if available
        if TaobaoCrawler._shared_context and TaobaoCrawler._shared_page:
            try:
                # Check if page is still valid
                await TaobaoCrawler._shared_page.title()
                self._context = TaobaoCrawler._shared_context
                self._page = TaobaoCrawler._shared_page
                self._playwright = TaobaoCrawler._shared_playwright
                self._update_progress(message="使用已有浏览器窗口...")
                return
            except:
                # Browser was closed, need to recreate
                TaobaoCrawler._shared_context = None
                TaobaoCrawler._shared_page = None
        
        self._update_progress(message="正在启动浏览器...")
        
        self._playwright = await async_playwright().start()
        TaobaoCrawler._shared_playwright = self._playwright
        
        # Use browser helper for smart browser selection
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless
            )
            # Save for reuse
            TaobaoCrawler._shared_context = self._context
            TaobaoCrawler._shared_page = self._page
        except Exception as e:
            raise RuntimeError(f"启动浏览器失败: {e}")
        
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
    
    async def _close_browser(self):
        """Close browser - but keep it open if _keep_browser_open is True"""
        if self._keep_browser_open:
            # Don't close, just clear local references
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            return
        
        # Actually close the browser
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
            TaobaoCrawler._shared_context = None
            TaobaoCrawler._shared_page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            TaobaoCrawler._shared_playwright = None
    
    def _clean_store_name(self, name: str) -> str:
        """Clean store name - remove prefixes like "几年老店", "天猫", etc."""
        if not name:
            return ""
        
        name = name.strip()
        
        # Remove common prefixes
        prefixes_to_remove = [
            r'^\d+年老店\s*',          # "5年老店 "
            r'^天猫\s*',               # "天猫 "
            r'^淘宝店铺\s*',           # "淘宝店铺 "
            r'^企业店铺\s*',           # "企业店铺 "
            r'^个人店铺\s*',           # "个人店铺 "
            r'^\[.*?\]\s*',            # "[标签] "
        ]
        
        for pattern in prefixes_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _normalize_store_url(self, url: str) -> str:
        """Normalize store URL to clean format like: https://shop123456.taobao.com/"""
        if not url:
            return ""
        
        # Make sure URL starts with https://
        if url.startswith('//'):
            url = 'https:' + url
        
        # Extract shop ID from various URL formats
        
        # Format 1: https://shop123456.taobao.com/...
        match = re.search(r'shop(\d+)\.taobao\.com', url)
        if match:
            return f"https://shop{match.group(1)}.taobao.com/"
        
        # Format 2: https://store.taobao.com/shop/view_shop.htm?user_number_id=123456
        match = re.search(r'user_number_id=(\d+)', url)
        if match:
            return f"https://shop{match.group(1)}.taobao.com/"
        
        # Format 3: Look for any numeric ID in URL that could be shop ID
        match = re.search(r'[=/](\d{6,12})[&/\?]?', url)
        if match:
            shop_id = match.group(1)
            return f"https://shop{shop_id}.taobao.com/"
        
        # Format 4: tmall.com store - extract shop ID
        if 'tmall.com' in url:
            match = re.search(r'(\w+)\.tmall\.com', url)
            if match:
                return f"https://{match.group(1)}.tmall.com/"
        
        # Can't extract shop ID, return as-is but cleaned
        parsed = urlparse(url)
        if parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}/"
        
        return url
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """
        Search Taobao for stores or products.
        Implements pagination to get all results.
        Keeps browser open for manual operation.
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=False)  # Always visible for Taobao
            
            # Taobao search URL
            url = f"{self.SEARCH_URL}?q={quote(keyword)}"
            self._update_progress(message="正在打开淘宝搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Check for login requirement
            await self._handle_login()
            
            # Wait for user to apply filters if needed
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⏸️ 请在浏览器中设置筛选条件，完成后程序将在10秒后自动开始抓取..."
            )
            await asyncio.sleep(10)
            
            self._update_progress(
                status=CrawlStatus.RUNNING,
                message="开始抓取数据..."
            )
            
            if content_type == ContentType.STORE:
                await self._crawl_stores_with_pagination(keyword, max_results)
            else:
                await self._crawl_products_with_pagination(keyword, max_results)
            
            if len(self.results) > 0:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message=f"✓ 完成! 共抓取 {len(self.results)} 条结果\n💡 浏览器保持打开，下次抓取无需重新登录"
                )
            else:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message="⚠️ 完成，但未找到结果。请检查搜索关键词。"
                )
            
        except Exception as e:
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"错误: {str(e)}"
            )
            raise
        finally:
            await self._close_browser()  # Will keep browser open if _keep_browser_open is True
        
        return self.results
    
    async def _handle_login(self):
        """Handle Taobao login if needed"""
        current_url = self._page.url
        if 'login' in current_url.lower():
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 需要登录淘宝账号，请在浏览器中登录...\n💡 登录后浏览器保持打开，下次无需重新登录"
            )
            # Wait for user to login (up to 5 minutes)
            for i in range(150):
                await asyncio.sleep(2)
                current_url = self._page.url
                if 's.taobao.com' in current_url or 'taobao.com/search' in current_url:
                    self._update_progress(message="✓ 登录成功！")
                    await asyncio.sleep(2)
                    break
                if self._cancelled:
                    return
    
    async def _crawl_stores_with_pagination(self, keyword: str, max_results: int):
        """Crawl stores with pagination support - get ALL pages"""
        self._update_progress(message="正在抓取淘宝店铺...")
        
        collected = 0
        page_num = 1
        seen_stores = set()
        max_pages = (max_results // 40) + 5  # Estimate max pages needed
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            self._update_progress(
                message=f"正在抓取第 {page_num} 页... (已获取 {collected} 个店铺)"
            )
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Scroll to load all items on current page
            await self._scroll_page()
            
            # Find all store elements on current page
            stores_found = await self._extract_stores_from_page(max_results - collected, seen_stores)
            
            if stores_found == 0 and page_num > 1:
                self._update_progress(message=f"第 {page_num} 页已无更多店铺")
                break
            
            collected = len(self.results)
            
            self._update_progress(
                current=collected,
                total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"已抓取 {collected}/{max_results} 个店铺 (第{page_num}页)"
            )
            
            # Try to go to next page
            if collected < max_results:
                has_next = await self._go_to_next_page()
                if not has_next:
                    self._update_progress(message="已到最后一页")
                    break
                page_num += 1
                await asyncio.sleep(3)
    
    async def _extract_stores_from_page(self, limit: int, seen_stores: set) -> int:
        """Extract stores from current page"""
        count = 0
        
        # Find all items with store info - try multiple selectors
        selectors = [
            '.Card--doubleCardWrapper--L2XFE73',
            '[class*="Card--"]',
            '[class*="shopName"]',
            '.m-itemlist .item',
            '[data-nid]',
        ]
        
        items = []
        for selector in selectors:
            try:
                items = await self._page.query_selector_all(selector)
                if items and len(items) > 0:
                    break
            except:
                continue
        
        if not items:
            return 0
        
        for item in items:
            if count >= limit or self._cancelled:
                break
            
            try:
                # Try multiple methods to find store info
                store_name = ""
                store_url = ""
                
                # Method 1: Look for shop link
                for link_sel in ['a[href*="shop"]', 'a[href*="store.taobao"]', '[class*="shop"] a']:
                    try:
                        link = await item.query_selector(link_sel)
                        if link:
                            store_url = await link.get_attribute('href') or ""
                            store_name = await link.inner_text() or ""
                            if store_name:
                                break
                    except:
                        continue
                
                # Method 2: Look for shop name element
                if not store_name:
                    for name_sel in ['[class*="shopName"]', '[class*="shop-name"]', '[class*="store"]']:
                        try:
                            elem = await item.query_selector(name_sel)
                            if elem:
                                store_name = await elem.inner_text() or ""
                                if store_name:
                                    break
                        except:
                            continue
                
                if not store_name:
                    continue
                
                # Clean store name
                store_name = self._clean_store_name(store_name)
                
                if not store_name or store_name in seen_stores:
                    continue
                
                seen_stores.add(store_name)
                
                # Normalize store URL to clean format
                store_url = self._normalize_store_url(store_url)
                
                if not store_url or 'shop' not in store_url.lower():
                    continue  # Skip if URL doesn't look like a shop URL
                
                # Create result
                share_text = f"【淘宝店铺】{store_name} {store_url}"
                
                result = CrawlResult(
                    platform=self.platform,
                    content_type=ContentType.STORE,
                    url=store_url,
                    share_text=share_text,
                    title="",
                    account_id="",
                    account_name="",
                    store_name=store_name,
                )
                
                self._add_result(result)
                count += 1
                
            except Exception as e:
                print(f"提取店铺信息失败: {e}")
                continue
        
        return count
    
    async def _scroll_page(self):
        """Scroll page to load more content"""
        # Scroll down multiple times to load all lazy-loaded content
        for _ in range(5):
            await self._page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(0.8)
        
        # Scroll back to top
        await self._page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
    
    async def _go_to_next_page(self) -> bool:
        """Go to next page, return True if successful"""
        try:
            # Method 1: Find and click "下一页" button
            next_selectors = [
                'button:has-text("下一页")',
                'a:has-text("下一页")',
                '[class*="next"]:not([class*="disabled"])',
                '.next-pagination-item:has-text("下一页")',
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = await self._page.query_selector(selector)
                    if next_btn:
                        is_disabled = await next_btn.get_attribute('disabled')
                        aria_disabled = await next_btn.get_attribute('aria-disabled')
                        if not is_disabled and aria_disabled != 'true':
                            await next_btn.click()
                            await asyncio.sleep(3)
                            return True
                except:
                    continue
            
            # Method 2: Keyboard navigation
            try:
                await self._page.keyboard.press('End')
                await asyncio.sleep(1)
                # Check if there's pagination
                pagination = await self._page.query_selector('[class*="pagination"]')
                if pagination:
                    # Try clicking the next page number
                    current = await self._page.query_selector('[class*="current"], [class*="active"]')
                    if current:
                        current_text = await current.inner_text()
                        next_num = int(current_text) + 1
                        next_page = await self._page.query_selector(f'a:has-text("{next_num}")')
                        if next_page:
                            await next_page.click()
                            await asyncio.sleep(3)
                            return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"翻页失败: {e}")
            return False
    
    async def _crawl_products_with_pagination(self, keyword: str, max_results: int):
        """Crawl products with pagination support"""
        self._update_progress(message="正在抓取淘宝商品...")
        
        collected = 0
        page_num = 1
        seen_urls = set()
        max_pages = (max_results // 40) + 5
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            self._update_progress(
                message=f"正在抓取第 {page_num} 页... (已获取 {collected} 个商品)"
            )
            
            await asyncio.sleep(2)
            await self._scroll_page()
            
            # Find product links
            product_links = await self._page.query_selector_all('a[href*="item.taobao"], a[href*="detail.tmall"]')
            
            new_count = 0
            for link in product_links:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    href = await link.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    
                    if href.startswith('//'):
                        href = 'https:' + href
                    
                    seen_urls.add(href)
                    
                    title = await link.inner_text()
                    title = title.strip()[:100] if title else ""
                    
                    if not title:
                        continue
                    
                    share_text = f"【淘宝】{title} {href}"
                    
                    result = CrawlResult(
                        platform=self.platform,
                        content_type=ContentType.PRODUCT,
                        url=href,
                        share_text=share_text,
                        title=title,
                        product_name=title,
                    )
                    
                    self._add_result(result)
                    collected += 1
                    new_count += 1
                    
                except Exception as e:
                    print(f"提取商品信息失败: {e}")
                    continue
            
            self._update_progress(
                current=collected,
                total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"已抓取 {collected}/{max_results} 个商品 (第{page_num}页)"
            )
            
            if new_count == 0 and page_num > 1:
                break
            
            # Go to next page
            if collected < max_results:
                has_next = await self._go_to_next_page()
                if not has_next:
                    break
                page_num += 1
