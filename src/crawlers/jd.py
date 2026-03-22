"""
JD.com (京东) crawler for searching and extracting store and product information.
Web version - keeps browser open to maintain login session.
"""

import asyncio
import re
from typing import List, Optional
from urllib.parse import quote

from .base import BaseCrawler, CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType
from ..utils.crawl_helpers import page_has_go_signal

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
    
    async def _init_browser(self, headless: bool = False, browser_type: str = "自动"):
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
        
        self._update_progress(message=f"正在启动浏览器 ({browser_type})...")
        
        self._playwright = await async_playwright().start()
        JDCrawler._shared_playwright = self._playwright
        
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless, browser_type=browser_type
            )
            JDCrawler._shared_context = self._context
            JDCrawler._shared_page = self._page
        except Exception as e:
            raise RuntimeError(f"启动浏览器失败: {e}")
        
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined, configurable: true
            });
            delete navigator.__proto__.webdriver;
            if (!window.chrome) {
                window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            }
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
                     max_results: int = 50, headless: bool = False,
                     browser_type: str = "自动") -> List[CrawlResult]:
        """Search JD for stores or products."""
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=False, browser_type=browser_type)
            
            import random
            
            # 先访问京东首页，模拟真实用户行为
            self._update_progress(message="正在打开京东首页...")
            await self._page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 模拟人类行为
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 500)
                await self._page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            url = f"{self.SEARCH_URL}?keyword={quote(keyword)}"
            self._update_progress(message="正在打开京东搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Longer initial wait with randomness to avoid detection
            wait_time = random.uniform(5, 8)
            await asyncio.sleep(wait_time)
            
            # Check for rate limiting or login
            await self._handle_rate_limit_and_login()
            
            # Wait for user to apply filters - check for user signal
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⏸️ 请在浏览器中设置筛选条件\n📌 完成后在浏览器地址栏末尾添加 #go 然后按回车开始抓取\n⏳ 或等待60秒后自动开始..."
            )
            
            for i in range(90):
                await asyncio.sleep(1)
                if await page_has_go_signal(self._page):
                    clean_url = await self._page.evaluate(
                        """() => window.location.href.split('#')[0]"""
                    )
                    try:
                        await self._page.goto(clean_url, wait_until='domcontentloaded', timeout=60000)
                        await asyncio.sleep(2)
                    except Exception:
                        pass
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
    
    async def _scroll_to_load_all(self):
        """JD loads bottom ~30 items only after scrolling - trigger full page load"""
        prev_height = 0
        for i in range(20):
            await self._page.evaluate(f'window.scrollBy(0, {500 + (i % 3) * 200})')
            await asyncio.sleep(0.6)
            current_height = await self._page.evaluate('document.body.scrollHeight')
            if current_height == prev_height and i > 8:
                break
            prev_height = current_height
        
        await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1.5)
        await self._page.evaluate('window.scrollBy(0, -300)')
        await asyncio.sleep(0.5)
        await self._page.evaluate('window.scrollBy(0, 600)')
        await asyncio.sleep(1)
        await self._page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
    
    async def _jd_go_to_next_page(self, current_page: int) -> bool:
        """Navigate to next page on JD search results"""
        next_page = current_page + 1
        try:
            current_url = self._page.url
            if 'page=' in current_url:
                new_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
            elif '?' in current_url:
                new_url = current_url + f'&page={next_page}'
            else:
                new_url = current_url + f'?page={next_page}'
            
            if 's=' in new_url:
                new_url = re.sub(r's=\d+', f's={(next_page - 1) * 60}', new_url)
            
            await self._page.goto(new_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            item_count = await self._page.evaluate('''() => {
                return document.querySelectorAll('li.gl-item, div[data-sku], [class*="gl-item"]').length;
            }''')
            if item_count > 0:
                print(f"✓ JD翻页成功! 第{next_page}页有{item_count}个商品")
                return True
        except Exception as e:
            print(f"JD URL翻页失败: {e}")
        
        try:
            next_selectors = [
                'a.pn-next:not(.disabled)',
                'a:has-text("下一页"):not(.disabled)',
                '[class*="next"]:not(.disabled)',
            ]
            for selector in next_selectors:
                try:
                    btn = await self._page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(3)
                        return True
                except:
                    continue
        except Exception as e:
            print(f"JD按钮翻页失败: {e}")
        
        return False
    
    async def _crawl_stores(self, max_results: int):
        """Crawl store info from JD search results with pagination"""
        import random
        self._update_progress(message="正在抓取京东店铺...")
        
        collected = 0
        page_num = 1
        max_pages = (max_results // 30) + 5
        seen_stores = set()
        consecutive_empty = 0
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            await self._check_pause()
            
            self._update_progress(
                message=f"📄 正在抓取第 {page_num} 页... (已获取 {collected} 个店铺)"
            )
            
            await asyncio.sleep(random.uniform(2, 4))
            await self._scroll_to_load_all()
            
            store_data = await self._page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const items = document.querySelectorAll('li.gl-item, .gl-i-wrap, div[data-sku], [class*="gl-item"]');
                for (const item of items) {
                    // Try multiple selectors for store links
                    const storeLink = item.querySelector(
                        'a.curr-shop, a.hd-shopname, a[href*="mall.jd.com"], a[href*="shop.jd.com"], ' +
                        '[class*="shop"] a, [class*="store"] a, .p-shop a, .shop-name a'
                    );
                    if (!storeLink) continue;
                    let storeName = storeLink.innerText.trim();
                    let storeUrl = storeLink.getAttribute('href') || '';
                    if (!storeName || storeName.length < 2 || !storeUrl) continue;
                    if (seen.has(storeName)) continue;
                    seen.add(storeName);
                    if (storeUrl.startsWith('//')) storeUrl = 'https:' + storeUrl;
                    results.push({ name: storeName, url: storeUrl });
                }
                // Also try standalone shop links not in product items
                const shopLinks = document.querySelectorAll('a[href*="mall.jd.com"], a[href*="shop.jd.com"]');
                for (const link of shopLinks) {
                    const name = link.innerText.trim();
                    let url = link.getAttribute('href') || '';
                    if (!name || name.length < 2 || seen.has(name)) continue;
                    if (url.startsWith('//')) url = 'https:' + url;
                    if (url.includes('mall.jd.com') || url.includes('shop.jd.com')) {
                        seen.add(name);
                        results.push({ name: name, url: url });
                    }
                }
                return results;
            }''')
            
            print(f"第{page_num}页JS提取到 {len(store_data)} 个店铺")
            
            new_this_round = 0
            for item in store_data:
                if collected >= max_results or self._cancelled:
                    break
                try:
                    store_name = item.get('name', '').strip()
                    store_url = item.get('url', '').strip()
                    if not store_name or store_name in seen_stores or not store_url:
                        continue
                    seen_stores.add(store_name)
                    
                    share_text = f"【京东店铺】{store_name} {store_url}"
                    result = CrawlResult(
                        platform=self.platform, content_type=ContentType.STORE,
                        url=store_url, share_text=share_text,
                        title="", account_id="", account_name="",
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
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    self._update_progress(message=f"连续{consecutive_empty}页无新店铺，停止")
                    break
            else:
                consecutive_empty = 0
            
            if collected < max_results:
                has_next = await self._jd_go_to_next_page(page_num)
                if not has_next:
                    self._update_progress(message="🏁 已到最后一页")
                    break
                page_num += 1
                await asyncio.sleep(random.uniform(1, 3))
    
    async def _crawl_products(self, max_results: int):
        """Crawl product info from JD search results with pagination"""
        import random
        self._update_progress(message="正在抓取京东商品...")
        
        collected = 0
        page_num = 1
        max_pages = (max_results // 30) + 5
        seen_urls = set()
        consecutive_empty = 0
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            await self._check_pause()
            
            self._update_progress(
                message=f"📄 正在抓取第 {page_num} 页... (已获取 {collected} 个商品)"
            )
            
            await asyncio.sleep(random.uniform(2, 4))
            await self._scroll_to_load_all()
            
            product_data = await self._page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const items = document.querySelectorAll('li.gl-item, .gl-i-wrap, div[data-sku], [class*="gl-item"]');
                for (const item of items) {
                    const productLink = item.querySelector('a[href*="item.jd.com"]');
                    if (!productLink) continue;
                    let productUrl = productLink.getAttribute('href') || '';
                    if (!productUrl) continue;
                    if (productUrl.startsWith('//')) productUrl = 'https:' + productUrl;
                    const cleanUrl = productUrl.split('?')[0];
                    if (seen.has(cleanUrl)) continue;
                    seen.add(cleanUrl);
                    let title = '';
                    const titleEl = item.querySelector('.p-name em, .p-name a, [class*="title"] em, [class*="title"] a');
                    if (titleEl) title = titleEl.innerText.trim();
                    if (!title) title = productLink.innerText.trim();
                    let storeName = '';
                    const storeEl = item.querySelector('a.curr-shop, a.hd-shopname, [class*="shop"] a, .p-shop a');
                    if (storeEl) storeName = storeEl.innerText.trim();
                    let price = '';
                    const priceEl = item.querySelector('.p-price i, [class*="price"] i, [class*="price"] span');
                    if (priceEl) price = priceEl.innerText.trim();
                    results.push({ url: productUrl, title: title || '', storeName: storeName || '', price: price || '' });
                }
                return results;
            }''')
            
            print(f"第{page_num}页JS提取到 {len(product_data)} 个商品")
            
            new_this_round = 0
            for item in product_data:
                if collected >= max_results or self._cancelled:
                    break
                try:
                    product_url = item.get('url', '')
                    title = item.get('title', '').strip()[:100]
                    store_name = item.get('storeName', '').strip()
                    price = item.get('price', '').strip()
                    
                    if not product_url or product_url in seen_urls:
                        continue
                    if not title:
                        continue
                    seen_urls.add(product_url)
                    
                    share_text = f"【京东】{title} {product_url}"
                    result = CrawlResult(
                        platform=self.platform, content_type=ContentType.PRODUCT,
                        url=product_url, share_text=share_text,
                        title=title, product_name=title,
                        store_name=store_name, price=price,
                    )
                    self._add_result(result)
                    collected += 1
                    new_this_round += 1
                except Exception as e:
                    print(f"提取商品信息失败: {e}")
                    continue
            
            self._update_progress(
                current=collected, total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"✓ 已抓取 {collected}/{max_results} 个商品 (第{page_num}页完成)"
            )
            
            if new_this_round == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    self._update_progress(message=f"连续{consecutive_empty}页无新商品，停止")
                    break
            else:
                consecutive_empty = 0
            
            if collected < max_results:
                has_next = await self._jd_go_to_next_page(page_num)
                if not has_next:
                    self._update_progress(message="🏁 已到最后一页")
                    break
                page_num += 1
                await asyncio.sleep(random.uniform(1, 3))
