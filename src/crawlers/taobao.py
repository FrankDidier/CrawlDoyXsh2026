"""
Taobao (淘宝) crawler for searching and extracting store information.
Web version - no login required for basic search.
"""

import asyncio
import re
from typing import List, Optional
from urllib.parse import quote

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
        """Initialize browser"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        self._update_progress(message="正在启动浏览器...")
        
        self._playwright = await async_playwright().start()
        
        import os
        
        playwright_user_data = os.path.expanduser('~/.crawler_chrome_profile')
        
        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                playwright_user_data,
                headless=headless,
                channel='chrome',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ],
            )
            self._browser = None
            self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            
        except Exception as e:
            print(f"无法使用Chrome，回退到Chromium: {e}")
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='zh-CN',
            )
            self._page = await self._context.new_page()
        
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
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """
        Search Taobao for stores or products.
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
            current_url = self._page.url
            if 'login' in current_url.lower():
                self._update_progress(
                    message="⚠️ 需要登录淘宝账号，请在浏览器中登录..."
                )
                # Wait for user to login
                for i in range(60):  # Wait up to 2 minutes
                    await asyncio.sleep(2)
                    if 's.taobao.com' in self._page.url:
                        break
                    if self._cancelled:
                        return self.results
            
            self._update_progress(message="正在加载搜索结果...")
            
            if content_type == ContentType.STORE:
                await self._crawl_stores(max_results)
            else:
                await self._crawl_products(max_results)
            
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
                    message="⚠️ 完成，但未找到结果。可能需要登录。"
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
    
    async def _crawl_stores(self, max_results: int):
        """Crawl store results - extract stores from product listings"""
        self._update_progress(message="正在抓取淘宝店铺...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        seen_stores = set()
        no_new_results_count = 0
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find all product items with store info
            items = await self._page.query_selector_all('[class*="Card--"], [class*="item"]')
            
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {len(items)} 个商品，已提取 {collected} 个店铺"
            )
            
            new_this_round = 0
            for item in items:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    # Try to find store link
                    store_link = await item.query_selector('a[href*="shop"], a[href*="tmall.com"], a[href*="store.taobao"]')
                    if not store_link:
                        # Try text-based approach
                        shop_elem = await item.query_selector('[class*="shopName"], [class*="shop-name"], [class*="store"]')
                        if not shop_elem:
                            continue
                    
                    # Get store info
                    store_name = ""
                    store_url = ""
                    
                    if store_link:
                        store_url = await store_link.get_attribute('href')
                        store_name = await store_link.inner_text()
                    else:
                        shop_elem = await item.query_selector('[class*="shopName"], [class*="shop-name"], [class*="store"]')
                        if shop_elem:
                            store_name = await shop_elem.inner_text()
                    
                    # Skip if already seen or no valid data
                    if not store_name or store_name.strip() in seen_stores:
                        continue
                    
                    store_name = store_name.strip()
                    seen_stores.add(store_name)
                    
                    # Normalize store URL
                    if store_url and store_url.startswith('//'):
                        store_url = 'https:' + store_url
                    elif not store_url:
                        store_url = f"https://s.taobao.com/search?q={quote(store_name)}"
                    
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
                    collected += 1
                    new_this_round += 1
                    
                    self._update_progress(
                        current=collected,
                        percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                        message=f"已抓取 {collected}/{max_results} 个店铺"
                    )
                    
                except Exception as e:
                    print(f"提取店铺信息失败: {e}")
                    continue
            
            if new_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 5:
                    break
            else:
                no_new_results_count = 0
            
            # Scroll to load more
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(2)
            scroll_count += 1
    
    async def _crawl_products(self, max_results: int):
        """Crawl product results"""
        self._update_progress(message="正在抓取淘宝商品...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        seen_urls = set()
        no_new_results_count = 0
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find product links
            product_links = await self._page.query_selector_all('a[href*="item.taobao"], a[href*="detail.tmall"]')
            
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {len(product_links)} 个商品链接，已抓取 {collected} 个"
            )
            
            new_this_round = 0
            for link in product_links:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    href = await link.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    
                    # Normalize URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    
                    seen_urls.add(href)
                    
                    # Get product title
                    title = await link.inner_text()
                    title = title.strip()[:100] if title else ""
                    
                    # Get parent element for store name
                    store_name = ""
                    try:
                        parent = await link.evaluate_handle('el => el.closest("div")')
                        store_elem = await parent.evaluate_handle('el => el.querySelector("[class*=\'shop\']")')
                        if store_elem:
                            store_name = await store_elem.evaluate('el => el.innerText')
                    except:
                        pass
                    
                    share_text = f"【淘宝】{title} {href}"
                    
                    result = CrawlResult(
                        platform=self.platform,
                        content_type=ContentType.PRODUCT,
                        url=href,
                        share_text=share_text,
                        title=title,
                        product_name=title,
                        store_name=store_name.strip() if store_name else "",
                    )
                    
                    self._add_result(result)
                    collected += 1
                    new_this_round += 1
                    
                except Exception as e:
                    print(f"提取商品信息失败: {e}")
                    continue
            
            if new_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 5:
                    break
            else:
                no_new_results_count = 0
            
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(2)
            scroll_count += 1
