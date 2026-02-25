"""
Base crawler class and data structures.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum
from datetime import datetime


class Platform(Enum):
    """Supported platforms"""
    DOUYIN = "抖音"
    KUAISHOU = "快手"
    TAOBAO = "淘宝"
    JD = "京东"


class ContentType(Enum):
    """Content types to search"""
    LIVE = "直播"
    VIDEO = "短视频"
    STORE = "店铺"
    PRODUCT = "商品"


class CrawlStatus(Enum):
    """Crawl operation status"""
    IDLE = "空闲"
    RUNNING = "运行中"
    WAITING = "等待验证"  # Waiting for CAPTCHA
    PAUSED = "暂停"
    COMPLETED = "完成"
    ERROR = "错误"
    CANCELLED = "已取消"


@dataclass
class CrawlResult:
    """Single crawl result item"""
    platform: Platform
    content_type: ContentType
    
    # Common fields
    url: str = ""
    title: str = ""
    
    # For social platforms (Douyin, Kuaishou)
    account_id: str = ""
    account_name: str = ""
    followers: str = ""
    
    # APP share text (formatted like mobile app share)
    share_text: str = ""
    
    # For e-commerce (Taobao, JD)
    store_name: str = ""
    product_name: str = ""
    price: str = ""
    
    # Metadata
    crawled_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export"""
        return {
            "平台": self.platform.value,
            "类型": self.content_type.value,
            "链接": self.url,
            "APP分享文本": self.share_text,
            "标题": self.title,
            "账号ID": self.account_id,
            "账号名称": self.account_name,
            "粉丝数": self.followers,
            "店铺名称": self.store_name,
            "商品名称": self.product_name,
            "价格": self.price,
            "抓取时间": self.crawled_at,
        }


@dataclass
class CrawlProgress:
    """Progress information for crawling"""
    status: CrawlStatus = CrawlStatus.IDLE
    total: int = 0
    current: int = 0
    message: str = ""
    _percentage_override: int = None  # Allow explicit percentage override
    
    @property
    def percentage(self) -> int:
        # Use override if set
        if self._percentage_override is not None:
            return self._percentage_override
        # Otherwise calculate from current/total
        if self.total == 0:
            return 0
        return int((self.current / self.total) * 100)
    
    @percentage.setter
    def percentage(self, value: int):
        self._percentage_override = value


class BaseCrawler:
    """Base class for all platform crawlers"""
    
    platform: Platform = None
    supported_types: List[ContentType] = []
    
    def __init__(self):
        self.results: List[CrawlResult] = []
        self.progress = CrawlProgress()
        self._cancelled = False
        self._progress_callback: Optional[Callable[[CrawlProgress], None]] = None
        self._result_callback: Optional[Callable[[CrawlResult], None]] = None
    
    def set_progress_callback(self, callback: Callable[[CrawlProgress], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    def set_result_callback(self, callback: Callable[[CrawlResult], None]):
        """Set callback for each new result"""
        self._result_callback = callback
    
    def _update_progress(self, status: CrawlStatus = None, total: int = None, 
                         current: int = None, message: str = None, 
                         percentage: int = None):
        """Update progress and notify callback"""
        if status is not None:
            self.progress.status = status
        if total is not None:
            self.progress.total = total
        if current is not None:
            self.progress.current = current
        if message is not None:
            self.progress.message = message
        if percentage is not None:
            self.progress.percentage = percentage
        
        if self._progress_callback:
            self._progress_callback(self.progress)
    
    def _add_result(self, result: CrawlResult):
        """Add a result and notify callback"""
        self.results.append(result)
        if self._result_callback:
            self._result_callback(result)
    
    async def search(self, keyword: str, content_type: ContentType, 
                     max_results: int = 100) -> List[CrawlResult]:
        """
        Search for keyword and crawl results.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement search()")
    
    def cancel(self):
        """Cancel the current crawl operation"""
        self._cancelled = True
        self._update_progress(status=CrawlStatus.CANCELLED, message="已取消")
    
    def pause(self):
        """Pause the current crawl operation"""
        self._paused = True
        self._update_progress(status=CrawlStatus.PAUSED, message="⏸️ 已暂停")
    
    def resume(self):
        """Resume the crawl operation"""
        self._paused = False
        self._update_progress(status=CrawlStatus.RUNNING, message="继续抓取中...")
    
    async def _check_pause(self):
        """Check if paused and wait until resumed"""
        while self._paused and not self._cancelled:
            await asyncio.sleep(0.5)
    
    def reset(self):
        """Reset crawler state"""
        self.results = []
        self.progress = CrawlProgress()
        self._cancelled = False
        self._paused = False