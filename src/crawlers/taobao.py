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
        
        # 添加多层反检测脚本
        await self._page.add_init_script("""
            // 1. 隐藏 webdriver 标识
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // 2. 覆盖 navigator.plugins (让它看起来像真实浏览器)
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 3. 覆盖 navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 4. 覆盖 chrome 对象
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 5. 覆盖权限查询
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 6. 删除自动化相关属性
            delete navigator.__proto__.webdriver;
            
            // 7. 模拟真实的 Connection 对象
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false
                })
            });
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
            
            # 先访问淘宝首页，模拟真实用户行为
            self._update_progress(message="正在打开淘宝首页...")
            await self._page.goto("https://www.taobao.com", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            # 模拟鼠标移动（人类行为）
            await self._simulate_human_behavior()
            
            # Taobao search URL - 使用 s=0 表示从第1个商品开始 (每页约44个)
            url = f"{self.SEARCH_URL}?q={quote(keyword)}&s=0"
            self._update_progress(message="正在打开淘宝搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检测是否被反爬虫拦截
            await self._check_and_handle_block()
            
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
    
    async def _simulate_human_behavior(self):
        """模拟人类行为 - 随机鼠标移动和滚动"""
        import random
        
        try:
            # 随机移动鼠标
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await self._page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # 随机滚动
            await self._page.evaluate(f'window.scrollBy(0, {random.randint(100, 300)})')
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            print(f"模拟人类行为失败: {e}")
    
    async def _check_and_handle_block(self):
        """检测并处理反爬虫拦截"""
        try:
            page_content = await self._page.content()
            current_url = self._page.url
            
            # 检测常见的反爬虫特征
            block_indicators = [
                'punish/deny',
                'rgv587_flag',
                '访问受限',
                '访问过于频繁',
                '滑块验证',
                'captcha',
                'verify',
            ]
            
            is_blocked = any(indicator in page_content or indicator in current_url 
                           for indicator in block_indicators)
            
            if is_blocked:
                self._update_progress(
                    status=CrawlStatus.WAITING,
                    message="⚠️ 检测到反爬虫拦截！\n"
                            "请在浏览器中:\n"
                            "1. 完成滑块验证(如果有)\n"
                            "2. 或手动刷新页面\n"
                            "3. 或手动搜索关键词\n"
                            "完成后等待10秒自动继续..."
                )
                
                # 等待用户处理
                for i in range(60):  # 最多等1分钟
                    await asyncio.sleep(2)
                    new_content = await self._page.content()
                    new_url = self._page.url
                    
                    # 检查是否已经绕过
                    still_blocked = any(indicator in new_content or indicator in new_url 
                                       for indicator in block_indicators)
                    
                    if not still_blocked and 's.taobao.com' in new_url:
                        self._update_progress(message="✓ 已绕过反爬虫检测")
                        await asyncio.sleep(2)
                        return
                    
                    if self._cancelled:
                        return
                
                # 如果还是被拦截，提示用户
                self._update_progress(
                    message="⚠️ 仍被拦截，建议:\n"
                            "1. 换一个IP地址\n"
                            "2. 清除浏览器Cookie\n"
                            "3. 稍后再试"
                )
                
        except Exception as e:
            print(f"检测反爬虫失败: {e}")
    
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
        consecutive_empty = 0  # Track consecutive pages with no new stores
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            await self._check_pause()
            
            self._update_progress(
                message=f"📄 正在抓取第 {page_num} 页... (已获取 {collected} 个店铺)"
            )
            
            print(f"\n{'='*50}")
            print(f"开始抓取第 {page_num} 页")
            print(f"当前URL: {self._page.url[:80]}...")
            print(f"{'='*50}")
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Scroll to load all items on current page
            await self._scroll_page()
            
            # 记录抓取前的数量
            before_count = len(self.results)
            
            # Find all store elements on current page
            stores_found = await self._extract_stores_from_page(max_results - collected, seen_stores)
            
            # 计算本页实际新增的店铺数
            actual_new = len(self.results) - before_count
            print(f"第{page_num}页提取完成: 本页找到{stores_found}个, 实际新增{actual_new}个, 总计{len(self.results)}个")
            
            if actual_new == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    self._update_progress(message=f"连续{consecutive_empty}页无新店铺，停止抓取")
                    print(f"连续{consecutive_empty}页无新店铺，停止")
                    break
            else:
                consecutive_empty = 0
            
            collected = len(self.results)
            
            self._update_progress(
                current=collected,
                total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"✓ 已抓取 {collected}/{max_results} 个店铺 (第{page_num}页完成)"
            )
            
            # Try to go to next page
            if collected < max_results:
                print(f"\n>>> 准备翻到第{page_num + 1}页...")
                has_next = await self._go_to_next_page(page_num)
                if not has_next:
                    self._update_progress(message="🏁 已到最后一页")
                    break
                page_num += 1
                await asyncio.sleep(2)
    
    async def _extract_stores_from_page(self, limit: int, seen_stores: set) -> int:
        """Extract stores from current page using comprehensive JS extraction"""
        count = 0
        seen_urls = set()
        
        invalid_names = {
            '开店', '阿里旺旺', '淘宝', '天猫', '登录', '注册', '购物车',
            '我的淘宝', '收藏夹', '客服', '帮助', '首页', '分类', '搜索',
            '免费开店', '淘宝开店', '天猫开店', '开直播店', '更多',
            '进店逛逛', '进店', '逛逛', '查看', '详情', '相似', '找相似',
            '加购', '收藏', '对比', '宝贝', '购买', '立即购买',
            '天猫超市', '天猫国际', '淘宝直播',
        }
        
        store_data = await self._page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            const allLinks = document.querySelectorAll('a');
            
            for (const link of allLinks) {
                const href = link.getAttribute('href') || '';
                if (!href) continue;
                
                let isStore = false;
                
                // Pattern 1: store.taobao.com (any path)
                if (href.includes('store.taobao.com')) isStore = true;
                // Pattern 2: shopXXXXX.taobao.com
                else if (/shop\\d+\\.taobao\\.com/.test(href)) isStore = true;
                // Pattern 3: xxx.tmall.com (store subdomain)
                else if (/\\/\\/[a-z][a-z0-9-]+\\.tmall\\.com/.test(href) &&
                         !href.includes('detail.tmall') && !href.includes('login') &&
                         !href.includes('pages.tmall') && !href.includes('www.tmall')) isStore = true;
                // Pattern 4: store links with appUid
                else if (href.includes('view_shop') || href.includes('appUid=')) isStore = true;
                // Pattern 5: shop.m.taobao.com
                else if (href.includes('shop.m.taobao.com')) isStore = true;
                
                if (!isStore) continue;
                
                // Skip product/item links that happen to be on taobao/tmall
                if (href.includes('item.htm') || href.includes('detail.tmall') || 
                    href.includes('item.taobao') || href.includes('ishop.taobao') ||
                    href.includes('zhaoshang.tmall') || href.includes('login') ||
                    href.includes('member') || href.includes('cart') ||
                    href.includes('favorite') || href.includes('rate')) continue;
                
                const cleanHref = href.split('&spm')[0].split('&scm')[0];
                if (seen.has(cleanHref)) continue;
                seen.add(cleanHref);
                
                // Get store name - try the link text, then look for nearby store name elements
                let storeName = link.innerText.trim();
                
                // If link text is empty or too short, try parent/sibling
                if (!storeName || storeName.length < 2) {
                    const parent = link.parentElement;
                    if (parent) {
                        // Look for store-name class in parent
                        const nameEl = parent.querySelector('[class*="shopname"], [class*="shop-name"], [class*="store"]');
                        if (nameEl) storeName = nameEl.innerText.trim();
                        // Fallback: try parent text
                        if (!storeName || storeName.length < 2) {
                            storeName = parent.innerText.split('\\n')[0].trim();
                        }
                    }
                }
                
                results.push({
                    href: href,
                    cleanHref: cleanHref,
                    storeName: storeName || ''
                });
            }
            return results;
        }''')
        
        print(f"JS extraction found {len(store_data)} store links")
        
        for item in store_data:
            if count >= limit or self._cancelled:
                break
            
            try:
                href = item.get('href', '')
                store_name = item.get('storeName', '')
                store_name = self._clean_store_name(store_name)
                
                if not store_name or len(store_name) < 2:
                    continue
                if store_name in invalid_names:
                    continue
                if not any(c.isalnum() for c in store_name):
                    continue
                
                store_url = self._normalize_store_url(href)
                if not store_url:
                    continue
                
                if store_url in seen_urls:
                    continue
                if store_name in seen_stores:
                    continue
                
                seen_urls.add(store_url)
                seen_stores.add(store_name)
                
                is_tmall = '.tmall.com' in store_url
                prefix = "天猫店铺" if is_tmall else "淘宝店铺"
                share_text = f"【{prefix}】{store_name} {store_url}"
                
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
        
        print(f"Extracted {count} stores from this page")
        return count
    
    async def _scroll_page(self):
        """Scroll page thoroughly to load ALL content (44-49 items per page)"""
        prev_height = 0
        max_scrolls = 30
        stable_count = 0
        
        for i in range(max_scrolls):
            scroll_amount = 400 + (i % 5) * 200
            await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(0.5)
            
            current_height = await self._page.evaluate('document.body.scrollHeight')
            if current_height == prev_height:
                stable_count += 1
                if stable_count >= 4 and i > 10:
                    break
            else:
                stable_count = 0
            prev_height = current_height
        
        await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1.5)
        
        await self._page.evaluate('window.scrollBy(0, -500)')
        await asyncio.sleep(0.5)
        await self._page.evaluate('window.scrollBy(0, 800)')
        await asyncio.sleep(0.8)
        
        await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(1)
        
        await self._page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)
        
        link_count = await self._page.evaluate('''() => {
            return document.querySelectorAll('a[href*="store.taobao"], a[href*=".tmall.com"], a[href*="shop"]').length;
        }''')
        print(f"After scrolling: {link_count} store/shop links visible")
    
    async def _go_to_next_page(self, current_page_num: int) -> bool:
        """Go to next page using multiple methods for reliability"""
        next_page_num = current_page_num + 1
        print(f"=== 翻页: 第{current_page_num}页 -> 第{next_page_num}页 ===")
        
        # 方法1: 通过URL参数翻页 (淘宝使用 s= 跳过商品数)
        # 淘宝每页约44个商品，所以 page2 = s=44, page3 = s=88
        try:
            current_url = self._page.url
            skip_count = (next_page_num - 1) * 44
            
            # 构建新URL - 淘宝使用 s= 参数而不是 page=
            if 's=' in current_url:
                new_url = re.sub(r's=\d+', f's={skip_count}', current_url)
            elif '?' in current_url:
                new_url = current_url + f'&s={skip_count}'
            else:
                new_url = current_url + f'?s={skip_count}'
            
            # 同时更新 page 参数（如果存在）
            if 'page=' in new_url:
                new_url = re.sub(r'page=\d+', f'page={next_page_num}', new_url)
            
            print(f"方法1: URL翻页 -> {new_url[:100]}...")
            
            await self._page.goto(new_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 滚动加载内容
            await self._page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(1)
            
            # 检查页面是否有新内容
            shop_links = await self._page.query_selector_all('a[href*="store.taobao.com"], a[href*=".tmall.com"]')
            if len(shop_links) > 5:
                print(f"✓ 方法1成功! 第{next_page_num}页有{len(shop_links)}个店铺链接")
                return True
            else:
                print(f"方法1: 只找到{len(shop_links)}个链接，尝试方法2...")
        except Exception as e:
            print(f"方法1失败: {e}")
        
        # 方法2: 点击"下一页"按钮
        try:
            next_selectors = [
                'button:has-text("下一页")',
                'a:has-text("下一页")',
                '.next-btn',
                '[class*="next"]:not([class*="disabled"]):not([disabled])',
                '.next-pagination-item:last-child',
                'button[class*="Next"]',
                'a[class*="Next"]',
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = await self._page.query_selector(selector)
                    if next_btn:
                        is_visible = await next_btn.is_visible()
                        is_disabled = await next_btn.get_attribute('disabled')
                        aria_disabled = await next_btn.get_attribute('aria-disabled')
                        class_name = await next_btn.get_attribute('class') or ''
                        
                        if is_visible and not is_disabled and aria_disabled != 'true' and 'disabled' not in class_name:
                            print(f"方法2: 点击下一页按钮 (selector: {selector})")
                            await next_btn.click()
                            await asyncio.sleep(3)
                            
                            # 验证翻页成功
                            shop_links = await self._page.query_selector_all('a[href*="store.taobao.com"], a[href*=".tmall.com"]')
                            if len(shop_links) > 5:
                                print(f"✓ 方法2成功! 有{len(shop_links)}个店铺链接")
                                return True
                except Exception as e:
                    continue
            
            print("方法2: 未找到可点击的下一页按钮，尝试方法3...")
        except Exception as e:
            print(f"方法2失败: {e}")
        
        # 方法3: 点击页码数字
        try:
            # 直接点击下一个页码
            page_num_selector = f'a:has-text("{next_page_num}"), span:has-text("{next_page_num}")'
            page_btns = await self._page.query_selector_all(page_num_selector)
            
            for btn in page_btns:
                try:
                    # 只点击看起来像页码的元素
                    text = await btn.inner_text()
                    if text.strip() == str(next_page_num):
                        is_visible = await btn.is_visible()
                        if is_visible:
                            print(f"方法3: 点击页码 {next_page_num}")
                            await btn.click()
                            await asyncio.sleep(3)
                            
                            shop_links = await self._page.query_selector_all('a[href*="store.taobao.com"], a[href*=".tmall.com"]')
                            if len(shop_links) > 5:
                                print(f"✓ 方法3成功! 有{len(shop_links)}个店铺链接")
                                return True
                except:
                    continue
            
            print("方法3: 未找到页码按钮")
        except Exception as e:
            print(f"方法3失败: {e}")
        
        # 方法4: 键盘快捷键翻页 (有些网站支持)
        try:
            print("方法4: 尝试键盘翻页...")
            await self._page.keyboard.press('PageDown')
            await asyncio.sleep(1)
            await self._page.keyboard.press('End')
            await asyncio.sleep(1)
            
            # 找分页区域并点击
            pagination = await self._page.query_selector('[class*="pagination"], [class*="Pagination"]')
            if pagination:
                # 滚动到分页区域
                await pagination.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"方法4失败: {e}")
        
        print(f"✗ 所有翻页方法都失败了，可能已到最后一页")
        return False
    
    async def _crawl_products_with_pagination(self, keyword: str, max_results: int):
        """Crawl products with pagination support"""
        self._update_progress(message="正在抓取淘宝商品...")
        
        collected = 0
        page_num = 1
        seen_urls = set()
        max_pages = (max_results // 40) + 5
        consecutive_empty = 0
        
        while collected < max_results and page_num <= max_pages and not self._cancelled:
            await self._check_pause()
            
            self._update_progress(
                message=f"📄 正在抓取第 {page_num} 页... (已获取 {collected} 个商品)"
            )
            
            await asyncio.sleep(2)
            await self._scroll_page()
            
            product_data = await self._page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const links = document.querySelectorAll('a[href*="item.taobao"], a[href*="detail.tmall"], a[href*="item.htm"]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    if (!href) continue;
                    if (!href.includes('item.taobao') && !href.includes('detail.tmall') && !href.includes('item.htm')) continue;
                    const cleanHref = href.split('&spm')[0].split('&scm')[0];
                    if (seen.has(cleanHref)) continue;
                    seen.add(cleanHref);
                    let title = link.innerText.trim();
                    if (!title || title.length < 2) {
                        const parent = link.parentElement;
                        if (parent) {
                            const titleEl = parent.querySelector('[class*="title"], [class*="name"]');
                            if (titleEl) title = titleEl.innerText.trim();
                        }
                    }
                    let fullHref = href;
                    if (href.startsWith('//')) fullHref = 'https:' + href;
                    results.push({ href: fullHref, title: title || '' });
                }
                return results;
            }''')
            
            before_count = len(self.results)
            new_count = 0
            for item in product_data:
                if collected >= max_results or self._cancelled:
                    break
                try:
                    href = item.get('href', '')
                    title = item.get('title', '').strip()[:100]
                    if not href or href in seen_urls or not title:
                        continue
                    seen_urls.add(href)
                    
                    share_text = f"【淘宝】{title} {href}"
                    result = CrawlResult(
                        platform=self.platform, content_type=ContentType.PRODUCT,
                        url=href, share_text=share_text,
                        title=title, product_name=title,
                    )
                    self._add_result(result)
                    collected += 1
                    new_count += 1
                except Exception as e:
                    print(f"提取商品信息失败: {e}")
                    continue
            
            actual_new = len(self.results) - before_count
            self._update_progress(
                current=collected, total=max_results,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"✓ 已抓取 {collected}/{max_results} 个商品 (第{page_num}页完成)"
            )
            
            if actual_new == 0:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    self._update_progress(message=f"连续{consecutive_empty}页无新商品，停止抓取")
                    break
            else:
                consecutive_empty = 0
            
            if collected < max_results:
                has_next = await self._go_to_next_page(page_num)
                if not has_next:
                    break
                page_num += 1
                await asyncio.sleep(2)
