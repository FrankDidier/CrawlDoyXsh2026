"""
JD.com (京东) crawler for searching and extracting store and product information.
Web version - keeps browser open to maintain login session.
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


class JDCrawler(BaseCrawler):
    """Crawler for JD.com platform - stores and products"""
    
    platform = Platform.JD
    supported_types = [ContentType.STORE, ContentType.PRODUCT]
    
    # JD URLs
    BASE_URL = "https://www.jd.com"
    SEARCH_URL = "https://search.jd.com/Search"
    
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
        self._keep_browser_open = True
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser - reuse existing if available"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        # Reuse existing browser if available
        if JDCrawler._shared_context and JDCrawler._shared_page:
            try:
                await JDCrawler._shared_page.title()
                self._context = JDCrawler._shared_context
                self._page = JDCrawler._shared_page
                self._playwright = JDCrawler._shared_playwright
                self._update_progress(message="使用已有浏览器窗口...")
                return
            except:
                JDCrawler._shared_context = None
                JDCrawler._shared_page = None
        
        self._update_progress(message="正在启动浏览器...")
        
        self._playwright = await async_playwright().start()
        JDCrawler._shared_playwright = self._playwright
        
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless
            )
            JDCrawler._shared_context = self._context
            JDCrawler._shared_page = self._page
        except Exception as e:
            raise RuntimeError(f"启动浏览器失败: {e}")
        
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
    
    async def _close_browser(self):
        """Close browser - but keep it open if _keep_browser_open is True"""
        if self._keep_browser_open:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            return
        
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
            JDCrawler._shared_context = None
            JDCrawler._shared_page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            JDCrawler._shared_playwright = None
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """Search JD for stores or products."""
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=False)
            
            url = f"{self.SEARCH_URL}?keyword={quote(keyword)}"
            self._update_progress(message="正在打开京东搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)
            
            # Check for rate limiting or login
            await self._handle_rate_limit_and_login()
            
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
                    clean_url = current_url.replace('#go', '')
                    await self._page.goto(clean_url, wait_until='domcontentloaded')
                    await asyncio.sleep(2)
                    break
                if self._cancelled:
                    return self.results
            
            self._update_progress(status=CrawlStatus.RUNNING, message="开始抓取数据...")
            
            if content_type == ContentType.STORE:
                await self._crawl_stores(max_results)
            else:
                await self._crawl_products(max_results)
            
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
                    message="⚠️ 完成，但未找到结果。"
                )
            
        except Exception as e:
            self._update_progress(status=CrawlStatus.ERROR, message=f"错误: {str(e)}")
            raise
        finally:
            await self._close_browser()
        
        return self.results
    
    async def _handle_rate_limit_and_login(self):
        """Handle rate limiting and login requirements"""
        content = await self._page.content()
        
        # Check for rate limiting
        if "访问频繁" in content or "无法搜索" in content or "验证" in content:
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 京东访问限制，请在浏览器中完成验证...\n等待完成后自动继续"
            )
            for i in range(120):  # Wait up to 4 minutes
                await asyncio.sleep(2)
                content = await self._page.content()
                if "访问频繁" not in content and "无法搜索" not in content:
                    self._update_progress(message="✓ 验证完成！继续抓取...")
                    await asyncio.sleep(2)
                    break
                if self._cancelled:
                    return
        
        # Check for login requirement
        current_url = self._page.url
        if 'passport.jd.com' in current_url or 'login' in current_url.lower():
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 需要登录京东账号，请扫码登录...\n💡 登录后浏览器保持打开，下次无需重新登录"
            )
            for i in range(150):
                await asyncio.sleep(2)
                current_url = self._page.url
                if 'search.jd.com' in current_url or 'jd.com' in current_url and 'passport' not in current_url:
                    self._update_progress(message="✓ 登录成功！")
                    await asyncio.sleep(2)
                    break
                if self._cancelled:
                    return
    
    async def _crawl_stores(self, max_results: int):
        """Crawl store info from JD search results"""
        self._update_progress(message="正在抓取京东店铺...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        seen_stores = set()
        no_new_results_count = 0
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            await asyncio.sleep(4)  # Longer delay to avoid rate limiting
            
            try:
                items = await self._page.query_selector_all('li.gl-item, .gl-i-wrap, div[data-sku], .J-goods-list .gl-item')
            except Exception as e:
                print(f"查询商品列表失败: {e}")
                await asyncio.sleep(3)
                continue
            
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
                    store_link = await item.query_selector('a.curr-shop, a[href*="mall.jd.com"], a[href*="shop.jd.com"], [class*="shop"] a')
                    if not store_link:
                        continue
                    
                    store_url = await store_link.get_attribute('href')
                    store_name = await store_link.inner_text()
                    
                    if not store_name or not store_url:
                        continue
                    
                    store_name = store_name.strip()
                    
                    if store_name in seen_stores or not store_name:
                        continue
                    
                    seen_stores.add(store_name)
                    
                    if store_url.startswith('//'):
                        store_url = 'https:' + store_url
                    
                    share_text = f"【京东店铺】{store_name} {store_url}"
                    
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
                if no_new_results_count >= 3:
                    break
            else:
                no_new_results_count = 0
            
            await self._page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(3)
            scroll_count += 1
    
    async def _crawl_products(self, max_results: int):
        """Crawl product info from JD search results"""
        self._update_progress(message="正在抓取京东商品...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        seen_urls = set()
        no_new_results_count = 0
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            await asyncio.sleep(4)
            
            try:
                items = await self._page.query_selector_all('li.gl-item, .gl-i-wrap, div[data-sku]')
            except Exception as e:
                print(f"查询商品列表失败: {e}")
                await asyncio.sleep(3)
                continue
            
            new_this_round = 0
            for item in items:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    product_link = await item.query_selector('a[href*="item.jd.com"]')
                    if not product_link:
                        continue
                    
                    product_url = await product_link.get_attribute('href')
                    
                    if not product_url or product_url in seen_urls:
                        continue
                    
                    if product_url.startswith('//'):
                        product_url = 'https:' + product_url
                    
                    seen_urls.add(product_url)
                    
                    title_elem = await item.query_selector('.p-name em, .p-name a, [class*="title"]')
                    title = ""
                    if title_elem:
                        title = await title_elem.inner_text()
                        title = title.strip()[:100] if title else ""
                    
                    store_name = ""
                    store_elem = await item.query_selector('a.curr-shop, [class*="shop"]')
                    if store_elem:
                        store_name = await store_elem.inner_text()
                        store_name = store_name.strip() if store_name else ""
                    
                    share_text = f"【京东】{title} {product_url}"
                    
                    result = CrawlResult(
                        platform=self.platform,
                        content_type=ContentType.PRODUCT,
                        url=product_url,
                        share_text=share_text,
                        title=title,
                        product_name=title,
                        store_name=store_name,
                    )
                    
                    self._add_result(result)
                    collected += 1
                    new_this_round += 1
                    
                except Exception as e:
                    print(f"提取商品信息失败: {e}")
                    continue
            
            self._update_progress(
                current=collected,
                total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"已抓取 {collected}/{max_results} 个商品"
            )
            
            if new_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 3:
                    break
            else:
                no_new_results_count = 0
            
            await self._page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(3)
            scroll_count += 1
