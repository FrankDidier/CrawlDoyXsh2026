"""
Kuaishou APP Automation via Android Emulator
Extracts real APP share links (v.kuaishou.com format) using ADB.
"""

import time
import re
import os
from typing import List, Optional, Callable
from dataclasses import dataclass

from .base import CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType
from .emulator_base import (
    ADBController, EmulatorConfig, EmulatorType,
    KUAISHOU_PACKAGE, check_adb_installed, get_emulator_adb_path, find_any_adb
)


@dataclass
class KuaishouEmulatorConfig:
    """Kuaishou emulator automation config"""
    emulator_type: EmulatorType = EmulatorType.LDPLAYER
    search_delay: float = 2.0  # Delay between searches
    share_delay: float = 1.5   # Delay for share dialog
    scroll_delay: float = 1.0  # Delay between scrolls


class KuaishouEmulatorCrawler:
    """
    Kuaishou crawler using Android emulator.
    Extracts real APP share links via ADB automation.
    """
    
    def __init__(self, config: KuaishouEmulatorConfig = None):
        self.config = config or KuaishouEmulatorConfig()
        self.adb: Optional[ADBController] = None
        self.results: List[CrawlResult] = []
        self._cancelled = False
        self._progress_callback: Optional[Callable] = None
        self._result_callback: Optional[Callable] = None
        self.progress = CrawlProgress()
    
    def set_progress_callback(self, callback: Callable):
        self._progress_callback = callback
    
    def set_result_callback(self, callback: Callable):
        self._result_callback = callback
    
    def _update_progress(self, status: CrawlStatus = None, 
                         message: str = "", percentage: int = None):
        if status:
            self.progress.status = status
        if message:
            self.progress.message = message
        if percentage is not None:
            self.progress.percentage = percentage
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
        
        # Check Kuaishou installed
        if not self.adb.is_app_installed(KUAISHOU_PACKAGE):
            self._update_progress(
                status=CrawlStatus.ERROR,
                message="❌ 快手APP未安装！请在模拟器中安装快手。"
            )
            return False
        
        self._update_progress(message="✓ 模拟器已连接")
        return True
    
    def search(self, keyword: str, content_type: ContentType,
               max_results: int = 50) -> List[CrawlResult]:
        """
        Search Kuaishou and extract APP share links.
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
            
            # Start Kuaishou app
            self._update_progress(message="正在启动快手...")
            self.adb.start_app(KUAISHOU_PACKAGE)
            time.sleep(3)
            
            # Go to search
            self._update_progress(message="正在搜索...")
            self._perform_search(keyword, content_type)
            
            # Collect results
            self._update_progress(message="正在提取结果...")
            self._collect_results(content_type, max_results)
            
            self._update_progress(
                status=CrawlStatus.COMPLETED,
                message=f"✓ 完成! 共获取 {len(self.results)} 条结果",
                percentage=100
            )
            
        except Exception as e:
            self._update_progress(
                status=CrawlStatus.ERROR,
                message=f"抓取出错: {str(e)}"
            )
        finally:
            if self.adb:
                self.adb.press_home()
        
        return self.results
    
    def _perform_search(self, keyword: str, content_type: ContentType):
        """Navigate to search and input keyword"""
        # Kuaishou search button is usually at top right
        width, height = self.adb.get_screen_size()
        
        # Tap search icon (top right area)
        search_x = int(width * 0.9)
        search_y = int(height * 0.08)
        self.adb.tap(search_x, search_y)
        time.sleep(1)
        
        # Tap search input box
        self.adb.tap(width // 2, int(height * 0.08))
        time.sleep(0.5)
        
        # Input keyword
        self.adb.input_text(keyword)
        time.sleep(0.5)
        
        # Press enter/search
        self.adb.press_key(66)  # KEYCODE_ENTER
        time.sleep(self.config.search_delay)
        
        # Select content type tab
        if content_type == ContentType.LIVE:
            # Click "直播" tab
            self._click_tab("直播")
        elif content_type == ContentType.VIDEO:
            # Click "视频" tab
            self._click_tab("视频")
        
        time.sleep(1)
    
    def _click_tab(self, tab_name: str):
        """Click on search result tab by name"""
        width, height = self.adb.get_screen_size()
        
        # Tab bar positions (approximate)
        tabs = {
            "综合": 0.15,
            "视频": 0.30,
            "用户": 0.45,
            "直播": 0.60,
            "音乐": 0.75,
        }
        
        if tab_name in tabs:
            tab_x = int(width * tabs[tab_name])
            tab_y = int(height * 0.15)  # Tab bar height
            self.adb.tap(tab_x, tab_y)
            time.sleep(0.5)
    
    def _collect_results(self, content_type: ContentType, max_results: int):
        """Scroll through results and extract share links"""
        collected = 0
        no_new_count = 0
        max_no_new = 5  # Stop after 5 scrolls with no new results
        
        while collected < max_results and not self._cancelled and no_new_count < max_no_new:
            # Get current screen items and share them
            new_count = self._extract_and_share_current(content_type, max_results - collected)
            
            if new_count > 0:
                collected += new_count
                no_new_count = 0
                percentage = min(int(collected * 100 / max_results), 99)
                self._update_progress(
                    percentage=percentage,
                    message=f"已获取 {collected}/{max_results} 条结果"
                )
            else:
                no_new_count += 1
            
            if collected < max_results:
                # Scroll to load more
                self.adb.swipe_up(500)
                time.sleep(self.config.scroll_delay)
    
    def _extract_and_share_current(self, content_type: ContentType, 
                                    remaining: int) -> int:
        """Extract and share items visible on current screen"""
        width, height = self.adb.get_screen_size()
        new_count = 0
        
        # For live streams, click each item and get share link
        if content_type == ContentType.LIVE:
            # Live stream items are usually stacked vertically
            item_positions = [
                (width // 2, int(height * 0.35)),
                (width // 2, int(height * 0.55)),
                (width // 2, int(height * 0.75)),
            ]
            
            for pos_x, pos_y in item_positions:
                if new_count >= remaining or self._cancelled:
                    break
                
                result = self._tap_and_share_item(pos_x, pos_y, ContentType.LIVE)
                if result:
                    self._add_result(result)
                    new_count += 1
        
        elif content_type == ContentType.VIDEO:
            # Video items in search results
            item_positions = [
                (width // 4, int(height * 0.35)),
                (width * 3 // 4, int(height * 0.35)),
                (width // 4, int(height * 0.6)),
                (width * 3 // 4, int(height * 0.6)),
            ]
            
            for pos_x, pos_y in item_positions:
                if new_count >= remaining or self._cancelled:
                    break
                
                result = self._tap_and_share_item(pos_x, pos_y, ContentType.VIDEO)
                if result:
                    self._add_result(result)
                    new_count += 1
        
        return new_count
    
    def _tap_and_share_item(self, x: int, y: int, 
                            content_type: ContentType) -> Optional[CrawlResult]:
        """Tap an item, get share link, then go back"""
        # Tap to enter item
        self.adb.tap(x, y)
        time.sleep(1.5)
        
        # Look for share button
        width, height = self.adb.get_screen_size()
        
        # Kuaishou share button is usually on the right side
        if content_type == ContentType.LIVE:
            # In live room, share might be at bottom
            share_x = int(width * 0.92)
            share_y = int(height * 0.85)
        else:
            # In video, share is usually at right side
            share_x = int(width * 0.92)
            share_y = int(height * 0.5)
        
        self.adb.tap(share_x, share_y)
        time.sleep(self.config.share_delay)
        
        # Look for "复制链接" button in share dialog
        copy_positions = [
            (int(width * 0.85), int(height * 0.65)),  # 复制链接 position
            (int(width * 0.75), int(height * 0.65)),  # Alternative
            (int(width * 0.85), int(height * 0.75)),  # Alternative
        ]
        
        for cx, cy in copy_positions:
            self.adb.tap(cx, cy)
            time.sleep(0.3)
        
        time.sleep(0.5)
        
        # Try to get clipboard content
        share_text = self.adb.get_clipboard()
        
        # Go back
        self.adb.press_back()
        time.sleep(0.5)
        self.adb.press_back()
        time.sleep(0.3)
        
        # Parse share text
        if share_text and ('kuaishou.com' in share_text or 'v.kuaishou' in share_text):
            return self._parse_share_text(share_text, content_type)
        
        return None
    
    def _parse_share_text(self, share_text: str, 
                          content_type: ContentType) -> Optional[CrawlResult]:
        """Parse Kuaishou share text to extract info"""
        # Kuaishou share format:
        # "作品名称 https://v.kuaishou.com/xxxxx 复制此链接打开快手"
        
        # Extract URL
        url_match = re.search(r'(https?://[^\s]+kuaishou\.com[^\s]*)', share_text)
        if not url_match:
            return None
        
        url = url_match.group(1)
        
        # Check for duplicates
        for r in self.results:
            if r.url == url:
                return None
        
        # Extract title/account info
        # Text before URL is usually the title or account info
        text_before_url = share_text[:url_match.start()].strip()
        
        # Try to find account name
        account_name = ""
        title = text_before_url
        
        # Format: "账号名称的直播间" or just title text
        if "的直播间" in text_before_url:
            account_name = text_before_url.replace("的直播间", "").strip()
            title = f"{account_name}直播间"
        elif "的作品" in text_before_url:
            parts = text_before_url.split("的作品")
            account_name = parts[0].strip() if parts else ""
            title = text_before_url
        
        # Extract ID from URL
        account_id = ""
        id_match = re.search(r'/([a-zA-Z0-9]+)/?$', url)
        if id_match:
            account_id = id_match.group(1)
        
        from datetime import datetime
        
        return CrawlResult(
            platform=Platform.KUAISHOU,
            content_type=content_type,
            url=url,
            share_text=share_text,
            account_id=account_id,
            account_name=account_name,
            title=title,
            crawled_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )


def check_kuaishou_emulator_ready(emulator_type: str = "mumu") -> dict:
    """
    Check if emulator environment is ready for Kuaishou.
    """
    from .emulator_base import EmulatorConfig, EmulatorType
    
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
        'kuaishou_installed': False,
        'ready': False,
        'message': "",
        'adb_path': "",
    }
    
    # Check ADB
    adb_path = get_emulator_adb_path(emu_type)
    if not adb_path:
        adb_path = find_any_adb()
    
    if adb_path:
        status['adb_installed'] = True
        status['adb_path'] = adb_path
    elif check_adb_installed():
        status['adb_installed'] = True
        status['adb_path'] = "adb"
    else:
        status['message'] = f"找不到ADB！请检查模拟器安装路径"
        return status
    
    # Create ADB controller
    config = EmulatorConfig()
    config.emulator_type = emu_type
    if adb_path:
        config.adb_path = adb_path
    
    adb = ADBController(config)
    
    # Try to connect
    if adb.connect():
        status['emulator_connected'] = True
    else:
        status['message'] = f"无法连接到{emulator_type}模拟器！请确保模拟器已启动。"
        return status
    
    # Check Kuaishou
    if adb.is_app_installed(KUAISHOU_PACKAGE):
        status['kuaishou_installed'] = True
        status['ready'] = True
        status['message'] = "✓ 环境就绪！可以开始抓取。"
    else:
        status['message'] = "快手APP未安装。请在模拟器中安装快手。"
    
    return status
