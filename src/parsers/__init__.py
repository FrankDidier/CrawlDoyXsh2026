"""
Platform-specific parsers for extracting share links and account information.
Supports: Douyin, Kuaishou, Taobao, JD
"""

from .douyin import DouyinParser
from .kuaishou import KuaishouParser
from .taobao import TaobaoParser
from .jd import JDParser
from .base import BaseParser, ParseResult

__all__ = [
    'DouyinParser',
    'KuaishouParser', 
    'TaobaoParser',
    'JDParser',
    'BaseParser',
    'ParseResult'
]
