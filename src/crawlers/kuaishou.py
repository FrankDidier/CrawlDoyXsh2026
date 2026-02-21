"""
Kuaishou (快手) crawler for searching and extracting live streams and videos.
"""

import asyncio
import re
import hashlib
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
            
            # Use live.kuaishou.com for live streams, recommend page for videos
            if content_type == ContentType.LIVE:
                url = f"{self.LIVE_URL}/"
                self._update_progress(message="正在打开快手直播页面...")
            else:
                # Use recommend page instead of search (search often has errors)
                url = f"{self.BASE_URL}/new-reco"
                self._update_progress(message="正在打开快手推荐页面...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(5)  # Wait for video feed to load
            
            self._update_progress(message="正在加载内容...")
            
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
        """Crawl video results from kuaishou.com feed interface"""
        self._update_progress(message="正在抓取快手短视频...")
        
        # Kuaishou uses a TikTok-style feed - need to extract from page state
        collected = 0
        scroll_count = 0
        max_scrolls = max(max_results * 2, 50)  # May need multiple scrolls per video
        no_new_results_count = 0
        seen_ids = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            try:
                # Try to extract current video info from page
                video_info = await self._extract_current_video()
                
                if video_info and video_info['id'] not in seen_ids:
                    seen_ids.add(video_info['id'])
                    
                    # Build URL
                    url = f"https://www.kuaishou.com/short-video/{video_info['id']}"
                    
                    # Generate share text
                    display_name = video_info.get('author', '')[:30] or f"视频{video_info['id'][:8]}"
                    title = video_info.get('title', '')[:50] or '精彩视频'
                    share_text = f"#快手短视频# 来看看【{display_name}】的精彩视频！ {title} {url}"
                    
                    result = CrawlResult(
                        platform=self.platform,
                        content_type=ContentType.VIDEO,
                        url=url,
                        share_text=share_text,
                        title=video_info.get('title', '')[:100],
                        account_id=video_info['id'],
                        account_name=video_info.get('author', '')[:50],
                    )
                    
                    self._add_result(result)
                    collected += 1
                    
                    self._update_progress(
                        total=max_results,
                        current=collected,
                        percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                        message=f"已抓取 {collected}/{max_results} 个短视频"
                    )
                    
                    no_new_results_count = 0
                else:
                    no_new_results_count += 1
                    if no_new_results_count >= 15:
                        self._update_progress(message="没有更多新视频了")
                        break
                
                # Scroll down to next video (Kuaishou feed style)
                await self._page.keyboard.press('ArrowDown')
                await asyncio.sleep(1.5)
                scroll_count += 1
                
            except Exception as e:
                print(f"抓取视频失败: {e}")
                no_new_results_count += 1
                await asyncio.sleep(1)
                scroll_count += 1
    
    async def _extract_current_video(self) -> Optional[dict]:
        """Extract info from currently displayed video"""
        try:
            # Get video info from page content
            info = {}
            
            # Look for author name - typically has @ prefix
            author_elem = await self._page.query_selector('[class*="author"], [class*="nickname"], [class*="name"]')
            if author_elem:
                author_text = await author_elem.inner_text()
                info['author'] = author_text.replace('@', '').strip()[:50]
            
            # Look for video title/description
            title_elem = await self._page.query_selector('[class*="caption"], [class*="desc"], [class*="title"]')
            if title_elem:
                title_text = await title_elem.inner_text()
                info['title'] = title_text.strip()[:100]
            
            # Try to get video ID from URL or page content
            current_url = self._page.url
            match = re.search(r'/(?:short-video|photo)/([^/?]+)', current_url)
            if match:
                info['id'] = match.group(1)
            else:
                # Try extracting from page state via JavaScript
                video_id = await self._page.evaluate('''() => {
                    // Look for video ID in various places
                    const url = window.location.href;
                    let match = url.match(/\\/(?:short-video|photo)\\/([^\\/?]+)/);
                    if (match) return match[1];
                    
                    // Try video element
                    const video = document.querySelector('video');
                    if (video && video.src) {
                        match = video.src.match(/photoId=([^&]+)/);
                        if (match) return match[1];
                    }
                    
                    return null;
                }''')
                if video_id:
                    info['id'] = video_id
            
            if not info.get('id'):
                # Generate unique ID from content
                import hashlib
                content = (info.get('author', '') + info.get('title', ''))
                if content:
                    info['id'] = hashlib.md5(content.encode()).hexdigest()[:12]
            
            return info if info.get('id') else None
            
        except Exception as e:
            print(f"提取视频信息失败: {e}")
            return None
