"""
Douyin APP Automation via Android Emulator
Extracts real APP share links (v.douyin.com format) using ADB.
"""

import time
import re
import os
from typing import List, Optional, Callable
from dataclasses import dataclass

from .base import CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType
from .emulator_base import (
    ADBController, EmulatorConfig, EmulatorType,
    DOUYIN_PACKAGE, check_adb_installed, get_emulator_adb_path, find_any_adb
)


@dataclass
class DouyinEmulatorConfig:
    """Douyin emulator automation config"""
    emulator_type: EmulatorType = EmulatorType.LDPLAYER
    search_delay: float = 2.0  # Delay between searches
    share_delay: float = 1.5   # Delay for share dialog
    scroll_delay: float = 1.0  # Delay between scrolls


class DouyinEmulatorCrawler:
    """
    Crawl Douyin using Android emulator automation.
    Gets real APP share links in v.douyin.com format.
    """
    
    platform = Platform.DOUYIN
    
    # Screen coordinates (for 1080x1920 resolution)
    # These may need adjustment based on actual emulator resolution
    COORDS = {
        # Search
        'search_icon': (970, 130),      # Top right search icon
        'search_input': (540, 130),     # Search input field
        'search_button': (1000, 130),   # Search/confirm button
        
        # Tabs
        'live_tab': (540, 250),         # 直播 tab
        'video_tab': (300, 250),        # 视频 tab
        
        # Content
        'first_item': (540, 600),       # First search result
        
        # Share
        'share_button': (970, 1600),    # Share button (bottom right)
        'copy_link': (540, 1400),       # Copy link option in share menu
        'more_share': (970, 1400),      # More share options
        
        # Navigation
        'back': (60, 130),              # Back button
        'home': (200, 1850),            # Home tab
    }
    
    def __init__(self, config: DouyinEmulatorConfig = None):
        self.config = config or DouyinEmulatorConfig()
        self.adb = None
        self.results: List[CrawlResult] = []
        self._progress_callback: Optional[Callable] = None
        self._result_callback: Optional[Callable] = None
        self._cancelled = False
        self.progress = CrawlProgress()
    
    def set_progress_callback(self, callback: Callable):
        self._progress_callback = callback
    
    def set_result_callback(self, callback: Callable):
        self._result_callback = callback
    
    def _update_progress(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.progress, key):
                setattr(self.progress, key, value)
        if self._progress_callback:
            self._progress_callback(self.progress)
    
    def _add_result(self, result: CrawlResult):
        self.results.append(result)
        if self._result_callback:
            self._result_callback(result)
    
    def cancel(self):
        self._cancelled = True
    
    def reset(self):
        self.results = []
        self._cancelled = False
        self.progress = CrawlProgress()
    
    def connect_emulator(self) -> bool:
        """Connect to Android emulator"""
        self._update_progress(message="正在连接模拟器...")
        
        # Find ADB path - prioritize emulator-specific ADB
        adb_path = get_emulator_adb_path(self.config.emulator_type)
        if not adb_path:
            adb_path = find_any_adb()
        if not adb_path and not check_adb_installed():
            self._update_progress(
                status=CrawlStatus.ERROR,
                message="❌ 未找到ADB！请确保模拟器已安装。"
            )
            return False
        
        # Create ADB controller with found path
        emu_config = EmulatorConfig(emulator_type=self.config.emulator_type)
        if adb_path:
            emu_config.adb_path = adb_path
            print(f"Using ADB: {adb_path}")
        self.adb = ADBController(emu_config)
        
        # Connect
        if not self.adb.connect():
            # Get ports info for error message
            if self.config.emulator_type == EmulatorType.MUMU:
                ports_msg = "16384, 7555, 16416, 7556"
            elif self.config.emulator_type == EmulatorType.LDPLAYER:
                ports_msg = "5555, 5556, 5554"
            else:
                ports_msg = "多个端口"
            
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"❌ 无法连接模拟器！\n\n"
                        f"已尝试端口: {ports_msg}\n\n"
                        f"请确保:\n"
                        f"1. 模拟器已完全启动\n"
                        f"2. MuMu: 设置 → 其他设置 → 开启ADB调试"
            )
            return False
        
        # Check Douyin installed
        if not self.adb.is_app_installed(DOUYIN_PACKAGE):
            self._update_progress(
                status=CrawlStatus.ERROR,
                message="❌ 抖音APP未安装！请在模拟器中安装抖音。"
            )
            return False
        
        self._update_progress(message="✓ 模拟器已连接")
        return True
    
    def search(self, keyword: str, content_type: ContentType,
               max_results: int = 50) -> List[CrawlResult]:
        """
        Search Douyin and extract APP share links.
        """
        self.reset()
        self._update_progress(
            status=CrawlStatus.RUNNING,
            message=f"开始搜索: {keyword}"
        )
        
        try:
            # Connect to emulator
            if not self.connect_emulator():
                return self.results
            
            # Start Douyin app
            self._update_progress(message="正在启动抖音...")
            self.adb.start_app(DOUYIN_PACKAGE)
            time.sleep(3)
            
            # Go to search
            self._update_progress(message="正在搜索...")
            self._perform_search(keyword, content_type)
            
            # Collect results
            self._collect_results(content_type, max_results)
            
            # Done
            if self.results:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message=f"✓ 完成！共获取 {len(self.results)} 条APP分享链接"
                )
            else:
                self._update_progress(
                    status=CrawlStatus.COMPLETED,
                    percentage=100,
                    message="⚠️ 完成，但未获取到结果"
                )
                
        except Exception as e:
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"错误: {str(e)}"
            )
        finally:
            # Go back to home
            if self.adb:
                self.adb.press_home()
        
        return self.results
    
    def _perform_search(self, keyword: str, content_type: ContentType):
        """Perform search in Douyin app"""
        # Tap search icon
        self.adb.tap(*self.COORDS['search_icon'])
        time.sleep(1)
        
        # Input search keyword
        self.adb.tap(*self.COORDS['search_input'])
        time.sleep(0.5)
        self.adb.input_text(keyword)
        time.sleep(0.5)
        
        # Press search/enter
        self.adb._run_adb('shell', 'input', 'keyevent', '66')  # Enter key
        time.sleep(self.config.search_delay)
        
        # Switch to appropriate tab
        if content_type == ContentType.LIVE:
            self.adb.tap(*self.COORDS['live_tab'])
        else:
            self.adb.tap(*self.COORDS['video_tab'])
        time.sleep(1.5)
    
    def _collect_results(self, content_type: ContentType, max_results: int):
        """Collect results from search"""
        collected = 0
        scroll_count = 0
        max_scrolls = max_results * 2  # May need multiple scrolls per item
        
        while collected < max_results and scroll_count < max_scrolls and not self._cancelled:
            # Get share link for current item
            share_link = self._get_share_link()
            
            if share_link:
                # Extract info from share text
                result = self._parse_share_text(share_link, content_type)
                if result:
                    self._add_result(result)
                    collected += 1
                    
                    self._update_progress(
                        current=collected,
                        total=max_results,
                        percentage=min(95, int(collected / max_results * 100)),
                        message=f"已获取 {collected}/{max_results} 条分享链接"
                    )
            
            # Scroll to next item
            if content_type == ContentType.VIDEO:
                # Swipe up for video feed
                self.adb.swipe_up(800)
            else:
                # Scroll in list for live
                self.adb.swipe_up(400)
            
            time.sleep(self.config.scroll_delay)
            scroll_count += 1
    
    def _get_share_link(self) -> Optional[str]:
        """
        Click share button and get the share link text.
        Returns the full share text including v.douyin.com link.
        """
        try:
            # Tap on current item to enter detail view
            self.adb.tap(*self.COORDS['first_item'])
            time.sleep(1.5)
            
            # Tap share button
            self.adb.tap(*self.COORDS['share_button'])
            time.sleep(self.config.share_delay)
            
            # Look for "复制链接" (Copy Link) option
            self.adb.tap(*self.COORDS['copy_link'])
            time.sleep(0.5)
            
            # Get clipboard content
            share_text = self.adb.get_clipboard()
            
            # Go back
            self.adb.press_back()
            time.sleep(0.5)
            self.adb.press_back()
            time.sleep(0.5)
            
            return share_text if share_text else None
            
        except Exception as e:
            print(f"获取分享链接失败: {e}")
            self.adb.press_back()
            time.sleep(0.3)
            return None
    
    def _parse_share_text(self, share_text: str, content_type: ContentType) -> Optional[CrawlResult]:
        """Parse share text to extract info"""
        try:
            # Extract v.douyin.com link
            url_match = re.search(r'https://v\.douyin\.com/[A-Za-z0-9_-]+/?', share_text)
            if not url_match:
                return None
            
            url = url_match.group(0)
            
            # Extract account name from text like 【账号名】
            account_match = re.search(r'【([^】]+)】', share_text)
            account_name = account_match.group(1) if account_match else ""
            
            # Extract title/description
            title = share_text[:100] if share_text else ""
            
            return CrawlResult(
                platform=self.platform,
                content_type=content_type,
                url=url,
                share_text=share_text,
                title=title,
                account_id="",
                account_name=account_name,
            )
            
        except Exception as e:
            print(f"解析分享文本失败: {e}")
            return None


def check_emulator_ready(emulator_type: str = "mumu") -> dict:
    """
    Check if emulator environment is ready.
    
    Args:
        emulator_type: "ldplayer", "mumu", "noxplayer", or "bluestacks"
    
    Returns dict with status info.
    """
    from .emulator_base import find_any_adb, get_emulator_adb_path, EmulatorConfig, EmulatorType
    
    # Map string to EmulatorType
    type_map = {
        "ldplayer": EmulatorType.LDPLAYER,
        "mumu": EmulatorType.MUMU,
        "noxplayer": EmulatorType.NOXPLAYER,
        "bluestacks": EmulatorType.BLUESTACKS,
    }
    emu_type = type_map.get(emulator_type.lower(), EmulatorType.MUMU)
    
    status = {
        'adb_installed': False,
        'emulator_connected': False,
        'douyin_installed': False,
        'ready': False,
        'message': "",
        'adb_path': "",
        'tried_ports': []
    }
    
    # Check ADB - first try emulator-specific path, then any ADB
    adb_path = get_emulator_adb_path(emu_type)
    if not adb_path:
        adb_path = find_any_adb()
    
    if adb_path:
        status['adb_installed'] = True
        status['adb_path'] = adb_path
        print(f"Using ADB: {adb_path}")
    elif check_adb_installed():
        status['adb_installed'] = True
        status['adb_path'] = "adb"  # System ADB
    else:
        status['message'] = (
            f"找不到ADB！\n\n"
            f"模拟器类型: {emulator_type}\n"
            f"请检查模拟器安装路径\n\n"
            f"常见路径:\n"
            f"• MuMu: D:\\MuMuPlayer\\shell\\adb.exe\n"
            f"• 雷电: C:\\LDPlayer\\LDPlayer9\\adb.exe"
        )
        return status
    
    # Create ADB controller with found path and correct emulator type
    config = EmulatorConfig()
    config.emulator_type = emu_type
    if adb_path:
        config.adb_path = adb_path
    
    adb = ADBController(config)
    
    # Try to connect to emulator
    if adb.connect():
        status['emulator_connected'] = True
    else:
        # Get list of ports we tried
        if emu_type == EmulatorType.MUMU:
            ports_tried = "16384, 7555, 16416, 7556"
        elif emu_type == EmulatorType.LDPLAYER:
            ports_tried = "5555, 5556, 5554"
        else:
            ports_tried = "多个端口"
        
        status['message'] = (
            f"无法连接到{emulator_type}模拟器!\n\n"
            f"已尝试端口: {ports_tried}\n\n"
            f"请确保:\n"
            f"1. 模拟器已完全启动（等待1-2分钟）\n"
            f"2. 模拟器已显示桌面\n"
            f"3. MuMu: 设置 → 其他设置 → 打开ADB调试\n"
            f"4. 再次点击'检查环境'"
        )
        return status
    
    # Check Douyin
    if adb.is_app_installed(DOUYIN_PACKAGE):
        status['douyin_installed'] = True
        status['ready'] = True
        status['message'] = "✓ 环境就绪！可以开始抓取。"
    else:
        status['message'] = "抖音APP未安装。请在模拟器中安装抖音。"
    
    return status
