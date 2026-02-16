"""
Base parser class and result data structure.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class Platform(Enum):
    """Supported platforms"""
    DOUYIN = "抖音"
    KUAISHOU = "快手"
    TAOBAO = "淘宝"
    JD = "京东"
    UNKNOWN = "未知"


class ContentType(Enum):
    """Content type"""
    LIVE_STREAM = "直播"
    SHORT_VIDEO = "短视频"
    PRODUCT = "商品"
    STORE = "店铺"
    UNKNOWN = "未知"


@dataclass
class ParseResult:
    """Result of parsing shared text"""
    platform: Platform
    content_type: ContentType
    url: str = ""
    account_id: str = ""
    account_name: str = ""
    store_name: str = ""
    product_name: str = ""
    raw_text: str = ""
    success: bool = False
    error_message: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export"""
        return {
            "平台": self.platform.value,
            "类型": self.content_type.value,
            "链接": self.url,
            "账号ID": self.account_id,
            "账号名称": self.account_name,
            "店铺名称": self.store_name,
            "商品名称": self.product_name,
        }
    
    def get_display_info(self) -> List[tuple]:
        """Get displayable key-value pairs"""
        info = [
            ("平台", self.platform.value),
            ("类型", self.content_type.value),
            ("链接", self.url),
        ]
        
        if self.account_id:
            info.append(("账号ID", self.account_id))
        if self.account_name:
            info.append(("账号名称", self.account_name))
        if self.store_name:
            info.append(("店铺名称", self.store_name))
        if self.product_name:
            info.append(("商品名称", self.product_name))
            
        return info


class BaseParser:
    """Base class for platform parsers"""
    
    platform: Platform = Platform.UNKNOWN
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """
        Parse shared text and extract information.
        Returns ParseResult if successful, None if this parser doesn't match.
        """
        raise NotImplementedError("Subclasses must implement parse()")
    
    def can_parse(self, text: str) -> bool:
        """Check if this parser can handle the given text"""
        raise NotImplementedError("Subclasses must implement can_parse()")
    
    def _clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        url = url.strip()
        # Remove trailing punctuation that might be captured
        while url and url[-1] in '.,;:!?，。；：！？':
            url = url[:-1]
        return url
