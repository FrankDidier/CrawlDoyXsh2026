"""
Kuaishou (快手) crawler for searching and extracting live streams and videos.
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


class KuaishouCrawler(BaseCrawler):
    """Crawler for Kuaishou platform"""
    
    platform = Platform.KUAISHOU
    supported_types = [ContentType.LIVE, ContentType.VIDEO]
    
    # Kuaishou URLs
    BASE_URL = "https://www.kuaishou.com"
    LIVE_URL = "https://live.kuaishou.com"
    
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
        import sys
        
        # Use persistent context for session management
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
                    '--disable-dev-shm-usage',
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
        Search Kuaishou for keyword and crawl results.
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=False)
            
            # Use live.kuaishou.com for live streams
            if content_type == ContentType.LIVE:
                url = f"{self.LIVE_URL}/"
                self._update_progress(message="正在打开快手直播页面...")
            else:
                url = f"{self.BASE_URL}/search/video?searchKey={quote(keyword)}"
                self._update_progress(message="正在打开快手搜索页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            self._update_progress(message="正在加载搜索结果...")
            
            if content_type == ContentType.LIVE:
                await self._crawl_live_streams(max_results)
            else:
                await self._crawl_videos(max_results, keyword)
            
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
                    message="⚠️ 完成，但未找到结果。"
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
    
    async def _crawl_live_streams(self, max_results: int):
        """Crawl live stream results from live.kuaishou.com"""
        self._update_progress(message="正在抓取快手直播间...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        no_new_results_count = 0
        seen_urls = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find all live room links - format: /u/{user_id}
            all_links = await self._page.query_selector_all('a[href*="/u/"]')
            
            unique_hrefs = set()
            for link in all_links:
                href = await link.get_attribute('href')
                if href and '/u/' in href:
                    # Clean and normalize URL
                    if href.startswith('/'):
                        href = self.LIVE_URL + href
                    unique_hrefs.add(href.split('?')[0])  # Remove query params
            
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {len(unique_hrefs)} 个直播间，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for href in unique_hrefs:
                if collected >= max_results or self._cancelled:
                    break
                
                if href in seen_urls:
                    continue
                
                try:
                    result = await self._extract_live_info(href)
                    if result:
                        seen_urls.add(href)
                        self._add_result(result)
                        collected += 1
                        new_results_this_round += 1
                        self._update_progress(
                            current=collected,
                            percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                            message=f"已抓取 {collected}/{max_results} 个直播间"
                        )
                except Exception as e:
                    print(f"提取快手直播信息失败: {e}")
                    continue
            
            if new_results_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 8:
                    self._update_progress(message="没有更多新结果了")
                    break
            else:
                no_new_results_count = 0
            
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(2)
            scroll_count += 1
    
    async def _extract_live_info(self, url: str) -> Optional[CrawlResult]:
        """Extract live stream info from URL"""
        try:
            # Extract user ID from URL
            match = re.search(r'/u/([^/?]+)', url)
            user_id = match.group(1) if match else ""
            
            # Try to find the card element with this link to get account name
            account_name = ""
            title = ""
            
            try:
                link_elem = await self._page.query_selector(f'a[href*="/u/{user_id}"]')
                if link_elem:
                    parent = await link_elem.evaluate_handle('el => el.closest("div[class]") || el.parentElement.parentElement')
                    if parent:
                        text = await parent.evaluate('el => el.innerText')
                        lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 1]
                        
                        # Filter out common UI elements
                        text_lines = [l for l in lines if not l.replace(',', '').replace('万', '').isdigit()]
                        
                        if text_lines:
                            account_name = text_lines[0] if text_lines else ""
                            if len(text_lines) > 1:
                                title = text_lines[1]
            except:
                pass
            
            # Generate APP-style share text
            display_name = account_name[:30] if account_name else f"快手号{user_id}"
            share_text = f"#快手直播#【{display_name}】正在直播，来和我一起支持Ta吧！复制下方链接，打开【快手】观看直播！ {url}"
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.LIVE,
                url=url,
                share_text=share_text,
                title=title[:100] if title else "",
                account_id=user_id,
                account_name=account_name[:50] if account_name else "",
            )
        except Exception as e:
            print(f"提取快手直播失败: {e}")
            return None
    
    async def _crawl_videos(self, max_results: int, keyword: str):
        """Crawl video results from kuaishou.com search"""
        self._update_progress(message="正在抓取快手短视频...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 10)
        no_new_results_count = 0
        seen_urls = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find video links
            video_links = await self._page.query_selector_all('a[href*="/short-video/"]')
            
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {len(video_links)} 个视频，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for link in video_links:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    href = await link.get_attribute('href')
                    if not href or href in seen_urls:
                        continue
                    
                    if href.startswith('/'):
                        href = self.BASE_URL + href
                    
                    # Extract video ID
                    match = re.search(r'/short-video/([^/?]+)', href)
                    video_id = match.group(1) if match else ""
                    
                    # Get text content
                    parent = await link.evaluate_handle('el => el.closest("div") || el.parentElement')
                    text = ""
                    account_name = ""
                    if parent:
                        text = await parent.evaluate('el => el.innerText')
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        if lines:
                            account_name = lines[-1] if len(lines) > 1 else ""
                    
                    # Generate share text
                    display_name = account_name[:30] if account_name else f"视频{video_id}"
                    share_text = f"#快手短视频# 来看看【{display_name}】的精彩视频！ {href}"
                    
                    result = CrawlResult(
                        platform=self.platform,
                        content_type=ContentType.VIDEO,
                        url=href,
                        share_text=share_text,
                        title=text[:100] if text else "",
                        account_id=video_id,
                        account_name=account_name[:50] if account_name else "",
                    )
                    
                    seen_urls.add(href)
                    self._add_result(result)
                    collected += 1
                    new_results_this_round += 1
                    
                except Exception as e:
                    print(f"提取快手视频信息失败: {e}")
                    continue
            
            if new_results_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 5:
                    break
            else:
                no_new_results_count = 0
            
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(2)
            scroll_count += 1
