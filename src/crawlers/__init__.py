"""
Web crawlers for different platforms.
Automatically search and extract data from Douyin, Kuaishou, Taobao, JD.
"""

from .base import BaseCrawler, CrawlResult, CrawlProgress
from .douyin import DouyinCrawler
from .kuaishou import KuaishouCrawler
from .taobao import TaobaoCrawler
from .jd import JDCrawler

__all__ = [
    'BaseCrawler',
    'CrawlResult', 
    'CrawlProgress',
    'DouyinCrawler',
    'KuaishouCrawler',
    'TaobaoCrawler',
    'JDCrawler',
]
