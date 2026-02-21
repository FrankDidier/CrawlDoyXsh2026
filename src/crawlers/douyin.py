"""
Douyin (抖音) crawler for searching and extracting live streams and videos.

Handles CAPTCHA verification automatically by prompting user.
"""

import asyncio
import re
from typing import List, Optional, Callable
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
    LIVE_URL = "https://live.douyin.com"  # Separate live streaming site
    SEARCH_URL = "https://www.douyin.com/search/{keyword}?type={type}"
    
    # Search type mapping
    TYPE_MAP = {
        ContentType.LIVE: "live",
        ContentType.VIDEO: "video",
    }
    
    # CAPTCHA detection selectors
    CAPTCHA_SELECTORS = [
        '//div[contains(text(), "验证")]',  # Contains "验证"
        '//div[contains(text(), "请完成")]',  # Contains "请完成"
        '[class*="captcha"]',
        '[class*="verify"]',
        '[id*="captcha"]',
        '.captcha-container',
    ]
    
    # Login/SMS verification detection
    LOGIN_SELECTORS = [
        '//div[contains(text(), "短信验证")]',  # SMS verification
        '//div[contains(text(), "手机号")]',     # Phone number
        '//div[contains(text(), "登录")]',       # Login
        '//input[@placeholder="手机号"]',        # Phone input
    ]
    
    def __init__(self):
        super().__init__()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None
    
    async def _init_browser(self, headless: bool = False):
        """Initialize browser - uses system Chrome/Edge with fallback"""
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
            self._page = await self._context.new_page()
        
        # Additional anti-detection
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
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
    
    async def _check_and_handle_captcha(self) -> bool:
        """
        Check for CAPTCHA and wait for user to solve it.
        Returns True if CAPTCHA was detected and handled.
        """
        captcha_detected = False
        
        for selector in self.CAPTCHA_SELECTORS:
            try:
                if selector.startswith('//'):
                    # XPath selector
                    elem = await self._page.query_selector(f'xpath={selector}')
                else:
                    elem = await self._page.query_selector(selector)
                
                if elem and await elem.is_visible():
                    captcha_detected = True
                    break
            except:
                continue
        
        if not captcha_detected:
            # Also check page content for verification text
            try:
                content = await self._page.content()
                if '请完成下列验证' in content or '滑动完成验证' in content:
                    captcha_detected = True
            except:
                pass
        
        if captcha_detected:
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 检测到验证码！请在浏览器中手动完成验证..."
            )
            
            # Wait for user to solve CAPTCHA (max 120 seconds)
            max_wait = 120
            waited = 0
            while waited < max_wait and not self._cancelled:
                await asyncio.sleep(2)
                waited += 2
                
                # Check if CAPTCHA is gone
                still_has_captcha = False
                try:
                    content = await self._page.content()
                    if '请完成下列验证' in content or '滑动完成验证' in content:
                        still_has_captcha = True
                except:
                    pass
                
                if not still_has_captcha:
                    self._update_progress(
                        status=CrawlStatus.RUNNING,
                        message="✓ 验证通过！继续抓取..."
                    )
                    await asyncio.sleep(2)  # Wait for page to load after verification
                    return True
                
                self._update_progress(
                    message=f"⚠️ 等待验证完成... ({max_wait - waited}秒)"
                )
            
            if waited >= max_wait:
                raise TimeoutError("验证超时！请重新开始抓取。")
        
        return captcha_detected
    
    async def _check_and_handle_login(self) -> bool:
        """
        Check for login/SMS verification requirement.
        Returns True if login was needed and user completed it.
        """
        login_required = False
        
        for selector in self.LOGIN_SELECTORS:
            try:
                if selector.startswith('//'):
                    elem = await self._page.query_selector(f'xpath={selector}')
                else:
                    elem = await self._page.query_selector(selector)
                
                if elem and await elem.is_visible():
                    login_required = True
                    break
            except:
                continue
        
        if not login_required:
            # Also check page content
            try:
                content = await self._page.content()
                if '短信验证' in content or '请输入手机号' in content:
                    login_required = True
            except:
                pass
        
        if login_required:
            self._update_progress(
                status=CrawlStatus.WAITING,
                message="⚠️ 需要登录！请在浏览器中完成登录或点击取消..."
            )
            
            # Wait for user to login (max 180 seconds)
            max_wait = 180
            waited = 0
            while waited < max_wait and not self._cancelled:
                await asyncio.sleep(3)
                waited += 3
                
                # Check if login dialog is gone
                still_needs_login = False
                try:
                    content = await self._page.content()
                    if '短信验证' in content or '请输入手机号' in content or '请输入验证码' in content:
                        still_needs_login = True
                except:
                    pass
                
                if not still_needs_login:
                    self._update_progress(
                        status=CrawlStatus.RUNNING,
                        message="✓ 登录成功！继续抓取..."
                    )
                    await asyncio.sleep(3)  # Wait for page to reload
                    return True
                
                self._update_progress(
                    message=f"⚠️ 等待登录完成... ({max_wait - waited}秒)"
                )
            
            if waited >= max_wait:
                raise TimeoutError("登录超时！请重新开始抓取。")
        
        return login_required
    
    async def search(self, keyword: str, content_type: ContentType,
                     max_results: int = 50, headless: bool = False) -> List[CrawlResult]:
        """
        Search Douyin for keyword and crawl results.
        
        Args:
            keyword: Search keyword
            content_type: LIVE or VIDEO
            max_results: Maximum results to crawl
            headless: Run browser in headless mode (False recommended for CAPTCHA)
            
        Returns:
            List of CrawlResult
        """
        if content_type not in self.supported_types:
            raise ValueError(f"不支持的类型: {content_type}")
        
        self.reset()
        self._update_progress(status=CrawlStatus.RUNNING, message=f"开始搜索: {keyword}")
        
        try:
            # Always use non-headless for CAPTCHA handling
            await self._init_browser(headless=False)
            
            # Different URL strategy based on content type
            if content_type == ContentType.LIVE:
                # Use live.douyin.com for live streams (no CAPTCHA required)
                url = f"{self.LIVE_URL}/"
                self._update_progress(message="正在打开直播页面...")
            else:
                # Use search for videos
                search_type = self.TYPE_MAP[content_type]
                url = self.SEARCH_URL.format(
                    keyword=quote(keyword),
                    type=search_type
                )
                self._update_progress(message="正在打开搜索页面...")
            
            # Navigate to page
            await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
            
            # Wait for initial load
            await asyncio.sleep(3)
            
            # Check for CAPTCHA
            await self._check_and_handle_captcha()
            
            # Wait more for content after potential CAPTCHA
            await asyncio.sleep(2)
            
            # Check for CAPTCHA again (sometimes appears after first one)
            await self._check_and_handle_captcha()
            
            # Check for login requirement (SMS verification)
            await self._check_and_handle_login()
            
            # Wait for page to fully load
            await asyncio.sleep(2)
            
            self._update_progress(message="正在加载搜索结果...")
            
            # Scroll and collect results
            if content_type == ContentType.LIVE:
                await self._crawl_live_streams(max_results)
            else:
                await self._crawl_videos(max_results)
            
            # Final status
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
                    message="⚠️ 完成，但未找到结果。请尝试其他关键词。"
                )
            
        except TimeoutError as e:
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"超时: {str(e)}"
            )
            raise
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
        """Crawl live stream results from live.douyin.com"""
        self._update_progress(message="正在抓取直播间...")
        
        collected = 0
        scroll_count = 0
        # Scale max_scrolls based on desired results (roughly 20-30 results per scroll)
        max_scrolls = max(50, max_results // 10)  # Allow many more scrolls for large requests
        no_new_results_count = 0
        seen_urls = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Find all live room links on live.douyin.com
            # Pattern: https://live.douyin.com/{room_id}
            all_links = await self._page.query_selector_all('a')
            
            live_links = []
            for link in all_links:
                href = await link.get_attribute('href')
                if href and 'live.douyin.com/' in href:
                    # Check if it's a room link (has numeric ID)
                    import re
                    if re.search(r'live\.douyin\.com/\d+', href):
                        live_links.append(link)
            
            current_count = len(live_links)
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {current_count} 个直播间，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for link in live_links:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    result = await self._extract_live_info_from_link(link)
                    if result and result.url and result.url not in seen_urls:
                        seen_urls.add(result.url)
                        self._add_result(result)
                        collected += 1
                        new_results_this_round += 1
                        self._update_progress(
                            current=collected,
                            percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                            message=f"已抓取 {collected}/{max_results} 个直播间"
                        )
                except Exception as e:
                    print(f"提取直播信息失败: {e}")
                    continue
            
            # Check if we're getting new results
            if new_results_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 3:
                    self._update_progress(message="滚动加载更多...")
            else:
                no_new_results_count = 0
            
            # Stop if no more results after many scrolls
            if no_new_results_count >= 8:
                self._update_progress(message="没有更多新结果了")
                break
            
            # Scroll to load more
            await self._page.evaluate('window.scrollBy(0, 1000)')
            await asyncio.sleep(2)
            scroll_count += 1
    
    async def _convert_to_app_share_links(self):
        """
        Phase 2: Convert web URLs to APP share links (v.douyin.com format).
        This is slower as we need to enter each room.
        """
        total = len(self.results)
        self._update_progress(
            message=f"正在获取APP分享链接 (0/{total})...",
            percentage=0
        )
        
        for i, result in enumerate(self.results):
            if self._cancelled:
                break
            
            # Skip if already has v.douyin.com link
            if 'v.douyin.com' in result.url:
                continue
            
            self._update_progress(
                message=f"正在获取APP分享链接 ({i+1}/{total})...",
                percentage=int((i / total) * 100)
            )
            
            # Try to get APP share link
            share_link = await self._get_app_share_link(result.url)
            
            if share_link:
                # Update the result with the APP share link
                # Store original web URL in a different field if needed
                result.url = share_link
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        self._update_progress(
            message=f"APP分享链接获取完成!",
            percentage=100
        )
    
    async def _extract_live_info_from_link(self, link) -> Optional[CrawlResult]:
        """Extract live stream info from a link element on live.douyin.com"""
        try:
            href = await link.get_attribute('href')
            if not href:
                return None
            
            # Clean up URL
            url = href.split('?')[0]  # Remove query params
            if not url.startswith('http'):
                url = 'https:' + url if url.startswith('//') else self.LIVE_URL + url
            
            # Extract room ID from URL
            import re
            room_match = re.search(r'/(\d+)$', url)
            room_id = room_match.group(1) if room_match else ""
            
            # Try to get account name from parent element
            account_name = ""
            title = ""
            
            try:
                # Get parent container
                parent = await link.evaluate_handle('el => el.closest("div[class]") || el.parentElement')
                if parent:
                    parent_text = await parent.evaluate('el => el.innerText')
                    lines = [l.strip() for l in parent_text.split('\n') if l.strip()]
                    
                    # Filter out numeric-only lines (viewer counts)
                    text_lines = [l for l in lines if not l.replace(',', '').isdigit() and len(l) > 1]
                    
                    if text_lines:
                        # Usually: title, then account name
                        if len(text_lines) >= 2:
                            title = text_lines[0]
                            account_name = text_lines[1]
                        elif len(text_lines) == 1:
                            account_name = text_lines[0]
            except:
                pass
            
            # Generate APP-style share text
            display_name = account_name[:30] if account_name else f"直播间{room_id}"
            share_text = f"#在抖音，记录美好生活#【{display_name}】正在直播，来和我一起支持Ta吧。复制下方链接，打开【抖音】，直接观看直播！ {url}"
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.LIVE,
                url=url,
                share_text=share_text,
                title=title[:100] if title else "",
                account_id=room_id,
                account_name=account_name[:50] if account_name else "",
            )
        except Exception as e:
            print(f"提取直播失败: {e}")
            return None
    
    async def _get_app_share_link(self, room_url: str) -> Optional[str]:
        """
        Get the APP share link (v.douyin.com) for a live room.
        This requires entering the room and clicking share button.
        """
        try:
            # Open the live room in a new tab
            new_page = await self._context.new_page()
            
            try:
                await new_page.goto(room_url, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)
                
                # Look for share button and click it
                share_selectors = [
                    '[class*="share"]',
                    'button:has-text("分享")',
                    '[data-e2e*="share"]',
                    'xpath=//div[contains(text(), "分享")]',
                    'xpath=//*[contains(@class, "share")]',
                ]
                
                share_btn = None
                for sel in share_selectors:
                    try:
                        share_btn = await new_page.query_selector(sel)
                        if share_btn and await share_btn.is_visible():
                            break
                    except:
                        continue
                
                if share_btn:
                    await share_btn.click()
                    await asyncio.sleep(1)
                    
                    # Look for the copy link button or the link text
                    link_selectors = [
                        'input[value*="v.douyin.com"]',
                        '[class*="link"] input',
                        'xpath=//input[contains(@value, "douyin.com")]',
                    ]
                    
                    for sel in link_selectors:
                        try:
                            link_input = await new_page.query_selector(sel)
                            if link_input:
                                share_link = await link_input.get_attribute('value')
                                if share_link and 'v.douyin.com' in share_link:
                                    return share_link
                        except:
                            continue
                    
                    # Try to find link in page content
                    content = await new_page.content()
                    import re
                    match = re.search(r'https://v\.douyin\.com/[A-Za-z0-9_-]+/?', content)
                    if match:
                        return match.group(0)
                
                return None
                
            finally:
                await new_page.close()
                
        except Exception as e:
            print(f"获取分享链接失败: {e}")
            return None
    
    async def _extract_live_info(self, card) -> Optional[CrawlResult]:
        """Extract information from a live stream card"""
        try:
            # Get link - try multiple methods
            href = None
            link_elem = None
            
            # Method 1: Direct link selector
            link_elem = await card.query_selector('a[href*="/live/"]')
            if link_elem:
                href = await link_elem.get_attribute('href')
            
            # Method 2: Check if card itself is a link
            if not href:
                try:
                    href = await card.get_attribute('href')
                except:
                    pass
            
            # Method 3: Find any anchor tag and check href
            if not href:
                all_links = await card.query_selector_all('a')
                for link in all_links:
                    h = await link.get_attribute('href')
                    if h and '/live/' in h:
                        href = h
                        link_elem = link
                        break
            
            if not href or '/live/' not in href:
                return None
            
            # Build full URL
            if href.startswith('//'):
                url = 'https:' + href
            elif href.startswith('/'):
                url = self.BASE_URL + href
            else:
                url = href
            
            # Extract all text from the card
            all_text = ""
            try:
                all_text = await card.inner_text()
            except:
                pass
            
            # Parse text into lines
            lines = [l.strip() for l in all_text.split('\n') if l.strip() and len(l.strip()) > 1]
            
            # Filter out common UI elements
            filtered_lines = []
            skip_patterns = ['正在直播', '观看', '人', '点赞', '分享', '关注', '进入直播间']
            for line in lines:
                if not any(p in line for p in skip_patterns) and not line.isdigit():
                    filtered_lines.append(line)
            
            # Get account name (usually first meaningful line)
            account_name = ""
            title = ""
            if filtered_lines:
                account_name = filtered_lines[0]
                if len(filtered_lines) > 1:
                    title = filtered_lines[1]
            
            # Extract live room ID from URL
            live_id_match = re.search(r'/live/(\d+)', url)
            live_id = live_id_match.group(1) if live_id_match else ""
            
            # Clean up
            account_name = account_name[:50] if account_name else ""
            title = title[:100] if title else ""
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.LIVE,
                url=url,
                title=title.strip(),
                account_id=live_id,
                account_name=account_name.strip(),
            )
        except Exception as e:
            print(f"提取直播失败: {e}")
            return None
    
    async def _crawl_videos(self, max_results: int):
        """Crawl video results"""
        self._update_progress(message="正在抓取短视频...")
        
        # First check for CAPTCHA - this is common on Douyin search pages
        await self._check_and_handle_captcha()
        
        # Wait for content after CAPTCHA
        await asyncio.sleep(3)
        
        collected = 0
        scroll_count = 0
        max_scrolls = max(50, max_results // 5)  # Scale scrolls based on max_results
        no_new_results_count = 0
        seen_urls = set()
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Check for CAPTCHA periodically
            if scroll_count % 3 == 0:
                await self._check_and_handle_captcha()
            
            # Find video cards using multiple strategies
            cards = []
            
            # Strategy 1: Find by data attribute
            cards = await self._page.query_selector_all('[data-e2e*="video"]')
            
            # Strategy 2: Find all video links and get their parent containers
            if not cards:
                links = await self._page.query_selector_all('a[href*="/video/"]')
                for link in links:
                    parent = await link.evaluate_handle('el => el.closest("li") || el.closest("div")')
                    if parent:
                        cards.append(parent)
            
            # Strategy 3: Use XPath
            if not cards:
                cards = await self._page.query_selector_all('xpath=//li[.//a[contains(@href, "/video/")]]')
            
            current_count = len(cards)
            self._update_progress(
                total=max_results,
                current=collected,
                percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0,
                message=f"找到 {current_count} 个视频，已抓取 {collected} 个"
            )
            
            new_results_this_round = 0
            for card in cards:
                if collected >= max_results or self._cancelled:
                    break
                
                try:
                    result = await self._extract_video_info(card)
                    if result and result.url and result.url not in seen_urls:
                        seen_urls.add(result.url)
                        self._add_result(result)
                        collected += 1
                        new_results_this_round += 1
                        self._update_progress(
                            current=collected,
                            percentage=min(95, int(collected / max_results * 100)) if max_results > 0 else 0
                        )
                except Exception as e:
                    print(f"提取视频信息失败: {e}")
                    continue
            
            # Check if we're getting new results
            if new_results_this_round == 0:
                no_new_results_count += 1
                if no_new_results_count >= 5:
                    self._update_progress(message="没有更多新结果了")
                    break
            else:
                no_new_results_count = 0
            
            # Scroll to load more
            await self._page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(2)
            scroll_count += 1
    
    async def _extract_video_info(self, card) -> Optional[CrawlResult]:
        """Extract information from a video card"""
        try:
            # Get link - try multiple methods
            href = None
            link_elem = None
            
            # Method 1: Direct video link selector
            link_elem = await card.query_selector('a[href*="/video/"]')
            if link_elem:
                href = await link_elem.get_attribute('href')
            
            # Method 2: Check if card itself is a link
            if not href:
                try:
                    href = await card.get_attribute('href')
                except:
                    pass
            
            # Method 3: Find any anchor tag and check href
            if not href:
                all_links = await card.query_selector_all('a')
                for link in all_links:
                    h = await link.get_attribute('href')
                    if h and '/video/' in h:
                        href = h
                        link_elem = link
                        break
            
            if not href or '/video/' not in href:
                return None
            
            # Build full URL
            if href.startswith('//'):
                url = 'https:' + href
            elif href.startswith('/'):
                url = self.BASE_URL + href
            else:
                url = href
            
            # Extract all text from the card
            all_text = ""
            try:
                all_text = await card.inner_text()
            except:
                pass
            
            # Parse text into lines
            lines = [l.strip() for l in all_text.split('\n') if l.strip() and len(l.strip()) > 1]
            
            # Filter out common UI elements
            filtered_lines = []
            skip_patterns = ['点赞', '评论', '收藏', '分享', '关注', '万', 'w', '次播放']
            for line in lines:
                is_skip = any(p in line.lower() for p in skip_patterns)
                is_number = line.replace('.', '').replace('万', '').replace('w', '').isdigit()
                if not is_skip and not is_number:
                    filtered_lines.append(line)
            
            # Get title (usually first or longest meaningful line)
            title = ""
            account_name = ""
            if filtered_lines:
                # Title is usually the longest text
                sorted_by_len = sorted(filtered_lines, key=len, reverse=True)
                title = sorted_by_len[0] if sorted_by_len else ""
                
                # Account name might be prefixed with @
                for line in filtered_lines:
                    if line.startswith('@'):
                        account_name = line[1:]
                        break
                    elif line != title and len(line) < 30:
                        account_name = line
            
            # Extract video ID from URL
            video_id_match = re.search(r'/video/(\d+)', url)
            video_id = video_id_match.group(1) if video_id_match else ""
            
            # Clean up
            title = title[:150] if title else ""
            account_name = account_name[:50] if account_name else ""
            
            # Generate APP-style share text
            display_name = account_name if account_name else f"视频{video_id}"
            share_text = f"#在抖音，记录美好生活# {title if title else '精彩视频'} {url}"
            
            return CrawlResult(
                platform=self.platform,
                content_type=ContentType.VIDEO,
                url=url,
                share_text=share_text,
                title=title.strip(),
                account_id=video_id,
                account_name=account_name.strip(),
            )
        except Exception as e:
            print(f"提取视频失败: {e}")
            return None
