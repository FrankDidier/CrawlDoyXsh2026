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
    
    async def _init_browser(self, headless: bool = False, browser_type: str = "自动"):
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
        
        self._update_progress(message=f"正在启动浏览器 ({browser_type})...")
        
        self._playwright = await async_playwright().start()
        TaobaoCrawler._shared_playwright = self._playwright
        
        # Use browser helper for smart browser selection
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless, browser_type=browser_type
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
        """Clean store name - remove prefixes like "几年老店", "天猫", extra labels, etc."""
        if not name:
            return ""
        
        name = name.strip()
        
        # Split by newlines and take the last meaningful part (usually the actual store name)
        lines = [l.strip() for l in name.split('\n') if l.strip()]
        if len(lines) > 1:
            # Filter out labels like "回头客1万", "皇冠", etc.
            for line in reversed(lines):
                if not re.match(r'^(回头客|皇冠|钻石|海钻|金冠|蓝冠|红冠|好评|销量|月销|年销|\d+万|\d+人)', line):
                    if len(line) > 2 and '店' in line or '旗舰' in line or '专卖' in line:
                        name = line
                        break
            else:
                # If no good match, take last non-numeric line
                for line in reversed(lines):
                    if not line.replace('万', '').replace('人', '').isdigit():
                        name = line
                        break
        
        # Remove common prefixes/suffixes
        patterns_to_remove = [
            r'^\d+年老店\s*',          # "5年老店 "
            r'^天猫\s*',               # "天猫 "
            r'^淘宝店铺\s*',           # "淘宝店铺 "
            r'^企业店铺\s*',           # "企业店铺 "
            r'^个人店铺\s*',           # "个人店铺 "
            r'^\[.*?\]\s*',            # "[标签] "
            r'^回头客\d+[万人]*\s*',   # "回头客1万 "
            r'^皇冠\s*',               # "皇冠 "
            r'^钻石\s*',               # "钻石 "
            r'^海钻\s*',               # "海钻 "
            r'^金冠\s*',               # "金冠 "
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
    def _normalize_store_url(self, url: str) -> str:
        """Normalize store URL - keep it short but recognizable"""
        if not url:
            return ""
        
        # Make sure URL starts with https://
        if url.startswith('//'):
            url = 'https:' + url
        
        # Format 1: https://shop123456.taobao.com/...
        match = re.search(r'shop(\d+)\.taobao\.com', url)
        if match:
            return f"https://shop{match.group(1)}.taobao.com/"
        
        # Format 2: storename.tmall.com (best format!)
        match = re.search(r'//([a-zA-Z0-9]+)\.tmall\.com', url)
        if match and match.group(1) not in ['detail', 'item', 'login', 'pages', 'www']:
            return f"https://{match.group(1)}.tmall.com/"
        
        # Format 3: store.taobao.com with user_number_id -> convert to shop format
        match = re.search(r'user_number_id=(\d+)', url)
        if match:
            return f"https://shop{match.group(1)}.taobao.com/"
        
        # Format 4: store.taobao.com/shop/view_shop.htm?appUid=XXX
        # This is the long format - we'll keep it but clean it up
        if 'store.taobao.com' in url and 'appUid=' in url:
            match = re.search(r'appUid=([a-zA-Z0-9]+)', url)
            if match:
                return f"https://store.taobao.com/shop/view_shop.htm?appUid={match.group(1)}"
        
        # Clean up any URL to remove extra parameters
        parsed = urlparse(url)
        if parsed.netloc and ('taobao' in parsed.netloc or 'tmall' in parsed.netloc):
            # Keep scheme and netloc, minimal path
            if 'shop' in parsed.path or 'view_shop' in parsed.path:
                return url.split('&spm')[0].split('&scm')[0]  # Remove tracking params
        
        return url
    
    async def _get_real_store_url(self, page, store_link_url: str) -> str:
        """
        Visit store link and get the final redirected URL.
        This gets the clean storename.tmall.com format.
        """
        try:
            # Open in new tab
            new_page = await self._context.new_page()
            
            # Navigate with short timeout
            await new_page.goto(store_link_url, wait_until='domcontentloaded', timeout=10000)
            await asyncio.sleep(1)
            
            # Get final URL after redirect
            final_url = new_page.url
            
            # Close the tab
            await new_page.close()
            
            # Normalize the final URL
            return self._normalize_store_url(final_url)
            
        except Exception as e:
            print(f"获取真实店铺URL失败: {e}")
            # Fall back to normalizing the original URL
            return self._normalize_store_url(store_link_url)
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False,
                     browser_type: str = "自动") -> List[CrawlResult]:
        """
        Search Taobao for stores or products.
        Implements pagination to get all results.
        Keeps browser open for manual operation.
        
        Args:
            browser_type: "Chrome", "Edge", "IE", "360浏览器", "QQ浏览器", or "自动"
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=False, browser_type=browser_type)  # Always visible for Taobao
            
            # Taobao search URL - must include page=1 and tab=all for results to load
            # Without these parameters, the page may show empty/loading state
            url = f"{self.SEARCH_URL}?page=1&q={quote(keyword)}&tab=all"
            self._update_progress(message="正在打开淘宝搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Check for login requirement
            await self._handle_login()
            
            # Wait for user to apply filters - check for user signal
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⏸️ 请在浏览器中设置筛选条件\n📌 完成后在浏览器地址栏末尾添加 #go 然后按回车开始抓取\n⏳ 或等待60秒后自动开始..."
            )
            
            # Wait for user signal or timeout
            for i in range(60):
                await asyncio.sleep(1)
                current_url = self._page.url
                if '#go' in current_url:
                    # User signaled ready, remove the #go from URL
                    clean_url = current_url.replace('#go', '')
                    await self._page.goto(clean_url, wait_until='domcontentloaded')
                    await asyncio.sleep(2)
                    break
                if self._cancelled:
                    return self.results
            
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
        """Extract stores from current page - use multiple selectors for complete extraction"""
        count = 0
        seen_urls = set()  # Track unique URLs
        
        # Invalid store names to filter out
        invalid_names = {
            '开店', '阿里旺旺', '淘宝', '天猫', '登录', '注册', '购物车',
            '我的淘宝', '收藏夹', '客服', '帮助', '首页', '分类', '搜索',
            '免费开店', '淘宝开店', '天猫开店', '开直播店', '更多',
            '进店逛逛', '进店', '逛逛', '查看', '详情', '相似', '找相似',
            '加购', '收藏', '对比', '宝贝', '购买', '立即购买',
        }
        
        # Use multiple selectors to find all store links
        # Each selector targets different page structures
        selectors = [
            'a[href*="store.taobao.com/shop"]',           # Standard taobao store link
            'a[href*=".taobao.com/shop/view_shop"]',      # View shop format
            'a[href*="shop"][href*=".taobao.com"]',       # Shop in taobao domain
            '[class*="shopname"] a',                       # Class contains shopname
            '[class*="shop-name"] a',                      # Class shop-name
            '[class*="store-name"] a',                     # Class store-name
            '[data-spm*="shop"] a',                        # Data attribute with shop
            '.Card--doubleCard a[href*="taobao.com"]',     # Card structure
            '.content--content a[href*="shop"]',           # Content structure
        ]
        
        all_shop_links = []
        seen_elements = set()  # To avoid processing same element twice
        
        for selector in selectors:
            try:
                links = await self._page.query_selector_all(selector)
                for link in links:
                    # Get unique identifier for element
                    elem_id = await link.evaluate('el => el.outerHTML.substring(0, 200)')
                    if elem_id not in seen_elements:
                        seen_elements.add(elem_id)
                        all_shop_links.append(link)
            except:
                continue
        
        print(f"Found {len(all_shop_links)} shop links using multiple selectors")
        
        for link in all_shop_links:
            if count >= limit or self._cancelled:
                break
            
            try:
                href = await link.get_attribute('href') or ""
                if not href or 'store.taobao.com/shop' not in href:
                    continue
                
                # Get store name from link text
                store_name = await link.inner_text() or ""
                store_name = self._clean_store_name(store_name)
                
                # Filter invalid names
                if not store_name or len(store_name) < 2:
                    continue
                if store_name in invalid_names:
                    continue
                
                # Normalize URL
                store_url = self._normalize_store_url(href)
                
                if not store_url:
                    continue
                
                # Skip duplicates (by URL, more reliable than name)
                if store_url in seen_urls:
                    continue
                
                # Also skip if name already seen (handles tmall vs taobao same store)
                if store_name in seen_stores:
                    continue
                
                seen_urls.add(store_url)
                seen_stores.add(store_name)
                
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
                print(f"提取店铺链接失败: {e}")
                continue
        
        # Method 2: Also check for tmall store links if not enough results
        if count < limit:
            tmall_links = await self._page.query_selector_all('a[href*=".tmall.com"]')
            print(f"Found {len(tmall_links)} tmall links on page")
            
            # Invalid store names to filter out
            invalid_names = {
                '开店', '阿里旺旺', '淘宝', '天猫', '登录', '注册', '购物车',
                '我的淘宝', '收藏夹', '客服', '帮助', '首页', '分类', '搜索',
                '免费开店', '淘宝开店', '天猫开店', '开直播店', '更多',
            }
            
            for link in tmall_links:
                if count >= limit or self._cancelled:
                    break
                
                try:
                    href = await link.get_attribute('href') or ""
                    
                    # Skip non-store links
                    if 'detail.tmall.com' in href or 'item.htm' in href or 'item.taobao' in href:
                        continue
                    if 'ishop.taobao' in href or 'zhaoshang.tmall' in href:
                        continue
                    if 'login' in href.lower() or 'member' in href.lower():
                        continue
                    
                    # Only accept store/shop links
                    if not any(x in href for x in ['store.taobao', '.tmall.com/']):
                        continue
                    
                    # Get store name
                    store_name = await link.inner_text() or ""
                    store_name = self._clean_store_name(store_name)
                    
                    # Filter invalid names
                    if not store_name or len(store_name) < 2:
                        continue
                    if store_name in invalid_names:
                        continue
                    if not any(c.isalnum() for c in store_name):
                        continue
                    
                    # Must look like a store name (usually contains these)
                    if not any(x in store_name for x in ['店', '旗舰', '专卖', '官方', '专营']):
                        # If doesn't have store keywords, must be at least 4 chars
                        if len(store_name) < 4:
                            continue
                    
                    # Normalize URL
                    store_url = self._normalize_store_url(href)
                    
                    if not store_url or store_url in seen_urls:
                        continue
                    
                    if store_name in seen_stores:
                        continue
                    
                    seen_urls.add(store_url)
                    seen_stores.add(store_name)
                    
                    share_text = f"【天猫店铺】{store_name} {store_url}"
                    
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
                    continue
        
        print(f"Extracted {count} stores from this page")
        return count
    
    async def _scroll_page(self):
        """Scroll page to load ALL content (49 items per page)"""
        # Multiple selectors to count items
        item_selectors = [
            'a[href*="store.taobao.com/shop"]',
            'a[href*=".tmall.com/"][href*="shop"]',
            '[class*="Card"]',  # Product cards
            '.content--content',  # Content items
        ]
        
        prev_count = 0
        max_scrolls = 20  # More scrolls to ensure all 49 items load
        stable_count = 0  # Track how many times count stayed same
        
        for i in range(max_scrolls):
            # Scroll down with varying amounts
            scroll_amount = 500 + (i % 3) * 200  # 500, 700, 900, 500, ...
            await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(0.4)
            
            # Count items using multiple selectors
            current_count = 0
            for selector in item_selectors:
                try:
                    items = await self._page.query_selector_all(selector)
                    current_count = max(current_count, len(items))
                except:
                    continue
            
            if current_count == prev_count:
                stable_count += 1
                if stable_count >= 3 and i > 8:
                    # Count stable for 3 iterations after 8 scrolls
                    break
            else:
                stable_count = 0
            
            prev_count = current_count
        
        # Scroll to very bottom to trigger any remaining lazy loads
        await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        
        # Scroll up a bit and down again to trigger more lazy loads
        await self._page.evaluate('window.scrollBy(0, -300)')
        await asyncio.sleep(0.3)
        await self._page.evaluate('window.scrollBy(0, 500)')
        await asyncio.sleep(0.5)
        
        # Scroll back to top for consistent behavior
        await self._page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
        
        # Final count
        final_links = await self._page.query_selector_all('a[href*="store.taobao.com/shop"], a[href*=".tmall.com/"]')
        print(f"After scrolling: {len(final_links)} shop/tmall links visible")
    
    async def _go_to_next_page(self) -> bool:
        """Go to next page, return True if successful"""
        try:
            # Method 1: Modify URL directly (most reliable)
            # Current URL format: https://s.taobao.com/search?page=1&q=keyword&tab=all
            current_url = self._page.url
            
            if 'page=' in current_url:
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    current_page = int(match.group(1))
                    next_page = current_page + 1
                    new_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
                    
                    await self._page.goto(new_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(3)
                    
                    # Check if page actually has content
                    shop_links = await self._page.query_selector_all('a[href*="store.taobao.com/shop"]')
                    if len(shop_links) > 0:
                        return True
                    else:
                        print(f"Page {next_page} has no results, stopping")
                        return False
            
            # Method 2: Find and click "下一页" button (fallback)
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
            
            # Method 3: Try clicking next page number
            try:
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
