"""
Douyin (抖音) crawler for searching and extracting live streams and videos.
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


class DouyinCrawler(BaseCrawler):
    """Crawler for Douyin platform"""
    
    platform = Platform.DOUYIN
    supported_types = [ContentType.LIVE, ContentType.VIDEO]
    
    # Douyin URLs
    BASE_URL = "https://www.douyin.com"
    SEARCH_URL = "https://www.douyin.com/search/{keyword}?type={type}"
    
    # Search type mapping
    TYPE_MAP = {
        ContentType.LIVE: "live",
        ContentType.VIDEO: "video",
    }
    
    def __init__(self):
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        self._update_progress(message="正在启动浏览器...")
        
        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # Create context with anti-detection
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        
        self._page = await self._context.new_page()
        
        # Additional anti-detection
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
    
    async def _close_browser(self):
        """Close browser"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """
        Search Douyin for keyword and crawl results.
        
        Args:
            keyword: Search keyword
            content_type: LIVE or VIDEO
            max_results: Maximum results to crawl
            headless: Run browser in headless mode
            
        Returns:
            List of CrawlResult
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=headless)
            
            # Build search URL
            search_type = self.TYPE_MAP[content_type]
            url = self.SEARCH_URL.format(
                keyword=quote(keyword),
                type=search_type
            )
            
            self._update_progress(message=f"正在打开搜索页面...")
            
            # Navigate to search page
            await self._page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for results to load
            await asyncio.sleep(3)
            
            # Scroll and collect results
            if content_type == ContentType.LIVE:
                await self._crawl_live_streams(max_results)
            else:
                await self._crawl_videos(max_results)
            
            self._update_progress(
                status=CrawlStatus.COMPLETED,
                message=f"完成! 共抓取 {len(self.results)} 条结果"
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
        """Crawl live stream results"""
        self._update_progress(message="正在抓取直播间...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = 20
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find live stream cards
            # Douyin live search results have specific structure
            cards = await self._page.query_selector_all('[data-e2e="search-live-card"], .search-live-card, [class*="LiveCard"]')
            
            if not cards:
                # Try alternative selectors
                cards = await self._page.query_selector_all('div[class*="live"] a[href*="/live/"]')
            
            self._update_progress(
                total=max_results,
                current=collected,
                message=f"找到 {len(cards)} 个直播间，已处理 {collected} 个"
            )
            
            for card in cards:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    result = await self._extract_live_info(card)
                    if result and result.url not in [r.url for r in self.results]:
                        self._add_result(result)
                        collected += 1
                        self._update_progress(current=collected)
                except Exception as e:
                    print(f"提取直播信息失败: {e}")
                    continue
            
            # Scroll to load more
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(1.5)
            scroll_count += 1
    
    async def _extract_live_info(self, card) -> Optional[CrawlResult]:
        """Extract information from a live stream card"""
        try:
            # Get link
            link_elem = await card.query_selector('a[href*="/live/"]')
            if not link_elem:
                link_elem = card
            
            href = await link_elem.get_attribute('href')
            if not href:
                return None
            
            # Build full URL
            if href.startswith('/'):
                url = self.BASE_URL + href
            else:
                url = href
            
            # Get title/anchor name
            title = ""
            title_elem = await card.query_selector('[class*="title"], [class*="name"], h2, h3, span')
            if title_elem:
                title = await title_elem.inner_text()
            
            # Get account name
            account_name = ""
            name_elem = await card.query_selector('[class*="author"], [class*="nickname"], [class*="user"]')
            if name_elem:
                account_name = await name_elem.inner_text()
            
            # If we couldn't get title, try to get it from the whole card
            if not title and not account_name:
                all_text = await card.inner_text()
                lines = [l.strip() for l in all_text.split('\n') if l.strip()]
                if lines:
                    account_name = lines[0]
                    if len(lines) > 1:
                        title = lines[1]
            
            # Extract live room ID from URL
            live_id_match = re.search(r'/live/(\d+)', url)
            live_id = live_id_match.group(1) if live_id_match else ""
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.LIVE,
                url=url,
                title=title.strip() if title else "",
                account_id=live_id,
                account_name=account_name.strip() if account_name else "",
            )
        except Exception as e:
            print(f"提取失败: {e}")
            return None
    
    async def _crawl_videos(self, max_results: int):
        """Crawl video results"""
        self._update_progress(message="正在抓取短视频...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = 20
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find video cards
            cards = await self._page.query_selector_all('[data-e2e="search-video-card"], .search-video-card, [class*="VideoCard"]')
            
            if not cards:
                cards = await self._page.query_selector_all('a[href*="/video/"]')
            
            self._update_progress(
                total=max_results,
                current=collected,
                message=f"找到 {len(cards)} 个视频，已处理 {collected} 个"
            )
            
            for card in cards:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    result = await self._extract_video_info(card)
                    if result and result.url not in [r.url for r in self.results]:
                        self._add_result(result)
                        collected += 1
                        self._update_progress(current=collected)
                except Exception as e:
                    print(f"提取视频信息失败: {e}")
                    continue
            
            # Scroll to load more
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(1.5)
            scroll_count += 1
    
    async def _extract_video_info(self, card) -> Optional[CrawlResult]:
        """Extract information from a video card"""
        try:
            # Get link
            link_elem = await card.query_selector('a[href*="/video/"]')
            if not link_elem:
                if await card.get_attribute('href'):
                    link_elem = card
                else:
                    return None
            
            href = await link_elem.get_attribute('href')
            if not href:
                return None
            
            # Build full URL
            if href.startswith('/'):
                url = self.BASE_URL + href
            else:
                url = href
            
            # Get video title
            title = ""
            title_elem = await card.query_selector('[class*="title"], [class*="desc"], p, span')
            if title_elem:
                title = await title_elem.inner_text()
            
            # Get author name
            account_name = ""
            author_elem = await card.query_selector('[class*="author"], [class*="nickname"], [class*="user"]')
            if author_elem:
                account_name = await author_elem.inner_text()
            
            # Extract video ID from URL
            video_id_match = re.search(r'/video/(\d+)', url)
            video_id = video_id_match.group(1) if video_id_match else ""
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.VIDEO,
                url=url,
                title=title.strip() if title else "",
                account_id=video_id,
                account_name=account_name.strip() if account_name else "",
            )
        except Exception as e:
            print(f"提取失败: {e}")
            return None
