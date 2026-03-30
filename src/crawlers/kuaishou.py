"""
Kuaishou (快手) crawler for searching and extracting live streams and videos.
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


class KuaishouCrawler(BaseCrawler):
    """Crawler for Kuaishou platform"""
    
    platform = Platform.KUAISHOU
    supported_types = [ContentType.LIVE, ContentType.VIDEO]
    
    # Kuaishou URLs
    BASE_URL = "https://www.kuaishou.com"
    LIVE_URL = "https://live.kuaishou.com"
    # Kuaishou search URLs - main site search with live/video type
    SEARCH_LIVE_URL = "https://www.kuaishou.com/search/live?searchKey={keyword}"
    SEARCH_VIDEO_URL = "https://www.kuaishou.com/search/video?searchKey={keyword}"
    
    def __init__(self):
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
    
    async def _init_browser(self, headless: bool = False, browser_type: str = "自动"):
        """Initialize browser"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright未安装。请运行: pip install playwright && playwright install chromium")
        
        self._update_progress(message=f"正在启动浏览器 ({browser_type})...")
        
        self._playwright = await async_playwright().start()
        
        # Use browser helper for smart browser selection
        from ..utils.browser_helper import create_browser_context
        
        try:
            self._context, self._page, self._browser = await create_browser_context(
                self._playwright, headless=headless, browser_type=browser_type
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
                     max_results: int = 50, headless: bool = False,
                     browser_type: str = "自动") -> List[CrawlResult]:
        """
        Search Kuaishou for keyword and crawl results.
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            await self._init_browser(headless=headless, browser_type=browser_type)
            
            self._update_progress(message="正在打开快手首页...")
            try:
                await self._page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
            except Exception:
                pass
            
            # Use kuaishou.com search with keyword
            if content_type == ContentType.LIVE:
                url = self.SEARCH_LIVE_URL.format(keyword=quote(keyword))
                self._update_progress(message=f"正在搜索快手直播: {keyword}...")
            else:
                url = self.SEARCH_VIDEO_URL.format(keyword=quote(keyword))
                self._update_progress(message=f"正在搜索快手短视频: {keyword}...")
            
            await self._page.goto(url, wait_until='domcontentloaded', timeout=90000)
            try:
                await self._page.wait_for_load_state('networkidle', timeout=25000)
            except Exception:
                pass
            await asyncio.sleep(4)
            
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⏸️ 请登录/加载结果后，地址栏加 #go 回车；或等待自动开始（约3分钟）"
            )
            
            max_wait = 180
            waited = 0
            while waited < max_wait and not self._cancelled:
                await asyncio.sleep(2)
                waited += 2
                if await page_has_go_signal(self._page):
                    self._update_progress(message="✓ 用户确认，开始抓取...")
                    await asyncio.sleep(1)
                    break
                if waited % 10 == 0:
                    self._update_progress(
                        status=CrawlStatus.WAITING,
                        message=f"⏸️ 可加 #go 立即开始，或等待自动继续 ({max_wait - waited}秒)"
                    )
            
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
        """Crawl live stream results from Kuaishou search page"""
        self._update_progress(message="正在抓取快手直播间...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(150, max_results // 3)
        no_new_results_count = 0
        seen_urls = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            await self._check_pause()
            
            live_data = await self._page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const links = document.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    let isLive = false;
                    if (/\\/u\\/[^\\/?]+/.test(href)) isLive = true;
                    else if (/\\/profile\\/[^\\/?]+/.test(href)) isLive = true;
                    else if (/\\/live\\/[^\\/?]+/.test(href)) isLive = true;
                    else if (/live\\.kuaishou\\.com\\/u\\//i.test(href)) isLive = true;
                    else if (/live\\.kuaishou\\.com\\/l\\//i.test(href)) isLive = true;
                    else if (href.includes('live.kuaishou') && /\\/(u|profile|live)\\//.test(href)) isLive = true;
                    if (isLive) {
                        let cleanHref = href.split('?')[0];
                        if (cleanHref.startsWith('//')) cleanHref = 'https:' + cleanHref;
                        else if (cleanHref.startsWith('/')) cleanHref = 'https://www.kuaishou.com' + cleanHref;
                        if (/^https?:\\/\\/live\\.kuaishou\\.com\\/?$/i.test(cleanHref)) continue;
                        if (seen.has(cleanHref)) continue;
                        seen.add(cleanHref);
                        let parent = link.closest('[class*="card"]') || link.closest('[class*="Card"]') ||
                                     link.closest('[class*="item"]') || link.closest('li') ||
                                     link.parentElement?.parentElement?.parentElement;
                        let parentText = '';
                        try { parentText = parent ? parent.innerText : link.innerText; } catch(e) {}
                        results.push({ href: cleanHref, parentText: parentText });
                    }
                }
                return results;
            }''')
            
            self._update_progress(
                total=max_results, current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"页面发现 {len(live_data)} 个直播间链接，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for item in live_data:
                if collected >= max_results or self._cancelled:
                    break
                
                href = item.get('href', '')
                if not href or href in seen_urls:
                    continue
                
                try:
                    match = re.search(r'/u/([^/?]+)', href)
                    if not match:
                        match = re.search(r'/(?:live|profile|l)/([^/?]+)', href)
                    if not match:
                        match = re.search(r'live\.kuaishou\.com/[^/]+/([^/?]+)', href)
                    user_id = match.group(1) if match else ""
                    if not user_id:
                        continue
                    
                    seen_urls.add(href)
                    
                    parent_text = item.get('parentText', '')
                    lines = [l.strip() for l in parent_text.split('\n') if l.strip() and len(l.strip()) > 1]
                    skip_words = ['直播', '观看', '在线', '人', '万', '关注']
                    text_lines = []
                    for l in lines:
                        clean = l.replace(',', '').replace('万', '').replace('人', '')
                        if not clean.isdigit() and not any(w in l for w in skip_words):
                            text_lines.append(l)
                    
                    account_name = ""
                    title = ""
                    if text_lines:
                        for line in sorted(text_lines, key=len):
                            if 2 < len(line) < 30:
                                account_name = line
                                break
                        for line in text_lines:
                            if line != account_name and len(line) > 5:
                                title = line
                                break
                    
                    display_name = account_name[:30] if account_name else f"快手号{user_id}"
                    share_text = f"#快手直播#【{display_name}】正在直播，来和我一起支持Ta吧！复制下方链接，打开【快手】观看直播！ {href}"
                    
                    result = CrawlResult(
                        platform=self.platform, content_type=ContentType.LIVE,
                        url=href, share_text=share_text,
                        title=title[:100] if title else "",
                        account_id=user_id,
                        account_name=account_name[:50] if account_name else "",
                    )
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
                if no_new_results_count >= 3:
                    self._update_progress(message=f"滚动加载更多... (尝试 {no_new_results_count}/15)")
            else:
                no_new_results_count = 0
            
            if no_new_results_count >= 15:
                self._update_progress(message="没有更多新结果了")
                break
            
            scroll_amount = 800 + (scroll_count % 4) * 300
            await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(2.5)
            
            if scroll_count % 5 == 4:
                await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
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
                    # Try to find specific author/nickname selectors first
                    parent = await link_elem.evaluate_handle('el => el.closest("[class*=\'card\']") || el.closest("[class*=\'Card\']") || el.closest("div[class]") || el.parentElement.parentElement')
                    
                    if parent:
                        # Look for author name element
                        for selector in ['[class*="author"]', '[class*="nickname"]', '[class*="name"]', '[class*="user"]', 'span[class]']:
                            try:
                                name_elem = await parent.evaluate_handle(f'el => el.querySelector("{selector}")')
                                if name_elem:
                                    name_text = await name_elem.evaluate('el => el.innerText')
                                    if name_text and name_text.strip() and len(name_text.strip()) < 50:
                                        # Verify it's a name, not a number or common UI text
                                        clean_name = name_text.strip()
                                        if not clean_name.replace(',', '').replace('万', '').replace('人', '').replace('在线', '').isdigit():
                                            if '直播' not in clean_name and '观看' not in clean_name:
                                                account_name = clean_name
                                                break
                            except:
                                continue
                        
                        # Fallback: parse all text
                        if not account_name:
                            text = await parent.evaluate('el => el.innerText')
                            lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 1]
                            
                            # Filter out numbers and common UI elements
                            text_lines = []
                            for l in lines:
                                clean = l.replace(',', '').replace('万', '').replace('人', '')
                                if not clean.isdigit() and '直播' not in l and '观看' not in l and '在线' not in l:
                                    text_lines.append(l)
                            
                            if text_lines:
                                # Shortest text that looks like a name
                                for line in sorted(text_lines, key=len):
                                    if 2 < len(line) < 30:
                                        account_name = line
                                        break
                                # Title is usually longer
                                for line in text_lines:
                                    if line != account_name and len(line) > 5:
                                        title = line
                                        break
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
        """Crawl video results from kuaishou.com search - scroll+extract approach"""
        self._update_progress(message="正在抓取快手短视频...")
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(150, max_results // 3)
        no_new_results_count = 0
        seen_ids = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            await self._check_pause()
            
            video_data = await self._page.evaluate('''() => {
                const results = [];
                const seen = new Set();
                const links = document.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    let m = href.match(/\\/(?:short-video|photo|video)\\/([^\\/?]+)/);
                    if (!m) m = href.match(/\\/fw\\/photo\\/([^\\/?]+)/);
                    if (!m) continue;
                    const videoId = m[1];
                    if (seen.has(videoId)) continue;
                    seen.add(videoId);
                    let parent = link.closest('[class*="card"]') || link.closest('[class*="Card"]') ||
                                 link.closest('[class*="item"]') || link.closest('[class*="feed"]') ||
                                 link.closest('li') || link.parentElement?.parentElement?.parentElement;
                    let parentText = '';
                    try { parentText = parent ? parent.innerText : link.innerText; } catch(e) {}
                    let fullHref = href;
                    if (href.startsWith('//')) fullHref = 'https:' + href;
                    else if (href.startsWith('/')) fullHref = 'https://www.kuaishou.com' + href;
                    results.push({ href: fullHref, videoId: videoId, parentText: parentText });
                }
                // Also try extracting from URL if on a video page
                const urlMatch = window.location.href.match(/\\/(?:short-video|photo)\\/([^\\/?]+)/);
                if (urlMatch && !seen.has(urlMatch[1])) {
                    let author = '', title = '';
                    try {
                        const ae = document.querySelector('[class*="author"], [class*="nickname"], [class*="name"]');
                        if (ae) author = ae.innerText.replace('@', '').trim();
                    } catch(e) {}
                    try {
                        const te = document.querySelector('[class*="caption"], [class*="desc"], [class*="title"]');
                        if (te) title = te.innerText.trim();
                    } catch(e) {}
                    results.push({ href: window.location.href, videoId: urlMatch[1], parentText: author + '\\n' + title });
                }
                return results;
            }''')
            
            self._update_progress(
                total=max_results, current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"页面发现 {len(video_data)} 个视频，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for item in video_data:
                if collected >= max_results or self._cancelled:
                    break
                try:
                    video_id = item.get('videoId', '')
                    url = item.get('href', '')
                    if not video_id or video_id in seen_ids or not url:
                        continue
                    seen_ids.add(video_id)
                    
                    parent_text = item.get('parentText', '')
                    lines = [l.strip() for l in parent_text.split('\n') if l.strip() and len(l.strip()) > 1]
                    skip_words = ['点赞', '评论', '分享', '关注', '万', '次播放', '转发', '观看']
                    filtered = [l for l in lines
                                if not any(w in l for w in skip_words)
                                and not l.replace('.', '').replace('万', '').replace('w', '').isdigit()]
                    
                    author = ""
                    title = ""
                    if filtered:
                        for line in filtered:
                            if line.startswith('@'):
                                author = line[1:]
                                break
                            elif not author and len(line) < 30:
                                author = line
                        sorted_by_len = sorted(filtered, key=len, reverse=True)
                        if sorted_by_len:
                            title = sorted_by_len[0]
                            if title == author and len(sorted_by_len) > 1:
                                title = sorted_by_len[1]
                    
                    display_name = author[:30] if author else f"视频{video_id[:8]}"
                    title_text = title[:50] if title else '精彩视频'
                    share_text = f"#快手短视频# 来看看【{display_name}】的精彩视频！ {title_text} {url}"
                    
                    result = CrawlResult(
                        platform=self.platform, content_type=ContentType.VIDEO,
                        url=url, share_text=share_text,
                        title=title[:100] if title else "",
                        account_id=video_id,
                        account_name=author[:50] if author else "",
                    )
                    self._add_result(result)
                    collected += 1
                    new_results_this_round += 1
                    self._update_progress(
                        current=collected,
                        percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                        message=f"已抓取 {collected}/{max_results} 个短视频"
                    )
                except Exception as e:
                    print(f"提取视频信息失败: {e}")
                    continue
            
            if new_results_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 3:
                    self._update_progress(message=f"滚动加载更多... (尝试 {no_new_results_count}/15)")
            else:
                no_new_results_count = 0
            
            if no_new_results_count >= 15:
                self._update_progress(message="没有更多新视频了")
                break
            
            scroll_amount = 800 + (scroll_count % 4) * 300
            await self._page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(2.5)
            
            if scroll_count % 5 == 4:
                await self._page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
            
            scroll_count += 1
