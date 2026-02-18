"""
Web crawlers for different platforms.
Automatically search and extract data from Douyin, Kuaishou, Taobao, JD.
"""

from .base import BaseCrawler, CrawlResult, CrawlProgress
from .douyin import DouyinCrawler

__all__ = [
    'BaseCrawler',
    'CrawlResult', 
    'CrawlProgress',
    'DouyinCrawler',
]
