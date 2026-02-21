"""
Taobao (淘宝) crawler for searching and extracting store information.
Web version - saves login session for future use.
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
    
    def __init__(self):
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser with persistent profile to save login"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        self._update_progress(message="正在启动浏览器...")
        
        self._playwright = await async_playwright().start()
        
        # Use browser helper for smart browser selection
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless
            )
        except Exception as e:
            raise RuntimeError(f"启动浏览器失败: {e}")
        
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
    
    async def _close_browser(self):
        """Close browser"""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    def _clean_store_name(self, name: str) -> str:
        """
        Clean store name - remove prefixes like "几年老店", "天猫", etc.
        """
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
        """
        Normalize store URL to clean format like: https://shop123456.taobao.com/
        """
        if not url:
            return ""
        
        # Make sure URL starts with https://
        if url.startswith('//'):
            url = 'https:' + url
        
        # Extract shop ID from various URL formats
        shop_id = None
        
        # Format 1: https://shop123456.taobao.com/...
        match = re.search(r'(shop\d+)\.taobao\.com', url)
        if match:
            shop_id = match.group(1)
        
        # Format 2: https://store.taobao.com/shop/view_shop.htm?user_number_id=123456
        if not shop_id:
            match = re.search(r'user_number_id=(\d+)', url)
            if match:
                return f"https://shop{match.group(1)}.taobao.com/"
        
        # Format 3: Look for shop ID in any part of URL
        if not shop_id:
            match = re.search(r'shop(\d+)', url)
            if match:
                shop_id = f"shop{match.group(1)}"
        
        # Format 4: tmall.com store
        if 'tmall.com' in url:
            # Keep tmall URLs as-is but clean up
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}/"
        
        # Return clean shop URL if we found shop ID
        if shop_id:
            return f"https://{shop_id}.taobao.com/"
        
        # Otherwise return original URL
        return url
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """
        Search Taobao for stores or products.
        Implements pagination to get all results.
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
            
            self._update_progress(message="正在加载搜索结果...")
            
            if content_type == ContentType.STORE:
                await self._crawl_stores_with_pagination(keyword, max_results)
            else:
                await self._crawl_products_with_pagination(keyword, max_results)
            
            if len(self.results) > 0:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message=f"✓ 完成! 共抓取 {len(self.results)} 条结果"
                )
            else:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message="⚠️ 完成，但未找到结果。可能需要重新登录。"
                )
            
        except Exception as e:
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"错误: {str(e)}"
            )
            raise
        finally:
            await self._close_browser()
        
        return self.results
    
    async def _handle_login(self):
        """Handle Taobao login if needed"""
        current_url = self._page.url
        if 'login' in current_url.lower():
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 需要登录淘宝账号，请在浏览器中登录...\n💡 登录后将自动保存，下次无需重复登录"
            )
            # Wait for user to login (up to 3 minutes)
            for i in range(90):
                await asyncio.sleep(2)
                current_url = self._page.url
                if 's.taobao.com' in current_url or 'taobao.com/search' in current_url:
                    self._update_progress(message="✓ 登录成功！继续抓取...")
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
        
        while collected < max_results and not self._cancelled:
            self._update_progress(
                message=f"正在抓取第 {page_num} 页... (已获取 {collected} 个店铺)"
            )
            
            # Wait for page to load
            await asyncio.sleep(2)
            
            # Find all store elements on current page
            stores_found = await self._extract_stores_from_page(max_results - collected, seen_stores)
            
            if stores_found == 0:
                # No new stores found, try scrolling first
                await self._scroll_page()
                stores_found = await self._extract_stores_from_page(max_results - collected, seen_stores)
                
                if stores_found == 0:
                    self._update_progress(message=f"第 {page_num} 页已无更多店铺")
                    break
            
            collected = len(self.results)
            
            self._update_progress(
                current=collected,
                total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"已抓取 {collected}/{max_results} 个店铺"
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
        
        # First scroll to load all items on current page
        for _ in range(3):
            await self._page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(0.5)
        
        # Back to top
        await self._page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
        
        # Find all items with store info
        items = await self._page.query_selector_all('[class*="Card--"], [class*="item"], [class*="Item"]')
        
        for item in items:
            if count >= limit or self._cancelled:
                break
            
            try:
                # Try multiple selectors for store link
                store_link = None
                store_name = ""
                store_url = ""
                
                # Method 1: Direct store link
                for selector in [
                    'a[href*="store.taobao"]',
                    'a[href*="shop"][href*=".taobao.com"]',
                    '[class*="shopName"] a',
                    '[class*="shop-name"] a',
                    '[class*="shop_"] a',
                ]:
                    store_link = await item.query_selector(selector)
                    if store_link:
                        break
                
                if store_link:
                    store_url = await store_link.get_attribute('href') or ""
                    store_name = await store_link.inner_text() or ""
                else:
                    # Method 2: Text-based search for store name
                    for selector in [
                        '[class*="shopName"]',
                        '[class*="shop-name"]',
                        '[class*="shop_"]',
                        '[class*="store-name"]',
                    ]:
                        elem = await item.query_selector(selector)
                        if elem:
                            store_name = await elem.inner_text() or ""
                            if store_name:
                                break
                
                if not store_name:
                    continue
                
                # Clean store name (remove "几年老店" etc.)
                store_name = self._clean_store_name(store_name)
                
                if not store_name or store_name in seen_stores:
                    continue
                
                seen_stores.add(store_name)
                
                # Normalize store URL to clean format
                store_url = self._normalize_store_url(store_url)
                
                if not store_url:
                    # Try to find URL by clicking through
                    store_url = f"https://s.taobao.com/search?q={quote(store_name)}&search_type=shop"
                
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
        for _ in range(5):
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(1)
    
    async def _go_to_next_page(self) -> bool:
        """Go to next page, return True if successful"""
        try:
            # Try to find and click "下一页" button
            next_btn = await self._page.query_selector('button:has-text("下一页"), a:has-text("下一页"), [class*="next"]')
            
            if next_btn:
                is_disabled = await next_btn.get_attribute('disabled')
                if is_disabled:
                    return False
                
                await next_btn.click()
                await asyncio.sleep(2)
                return True
            
            # Alternative: Look for pagination
            pages = await self._page.query_selector_all('[class*="pagination"] a, [class*="page"] a')
            current_page = await self._page.query_selector('[class*="current"], [class*="active"]')
            
            if current_page:
                current_text = await current_page.inner_text()
                try:
                    current_num = int(current_text)
                    # Find next page number
                    for page in pages:
                        page_text = await page.inner_text()
                        try:
                            if int(page_text) == current_num + 1:
                                await page.click()
                                await asyncio.sleep(2)
                                return True
                        except:
                            continue
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
        
        while collected < max_results and not self._cancelled:
            self._update_progress(
                message=f"正在抓取第 {page_num} 页... (已获取 {collected} 个商品)"
            )
            
            await asyncio.sleep(2)
            
            # Scroll to load all items
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
                message=f"已抓取 {collected}/{max_results} 个商品"
            )
            
            if new_count == 0:
                break
            
            # Go to next page
            if collected < max_results:
                has_next = await self._go_to_next_page()
                if not has_next:
                    break
                page_num += 1
