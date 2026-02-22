"""
Web crawlers for different platforms.
Automatically search and extract data from Douyin, Kuaishou, Taobao, JD.
Supports both web scraping and Android emulator automation.
"""

from .base import BaseCrawler, CrawlResult, CrawlProgress
from .douyin import DouyinCrawler
from .kuaishou import KuaishouCrawler
from .taobao import TaobaoCrawler
from .jd import JDCrawler

# Emulator-based crawlers (for APP share links)
try:
    from .emulator_base import ADBController, EmulatorConfig, EmulatorType
    from .douyin_emulator import DouyinEmulatorCrawler, check_emulator_ready
    from .kuaishou_emulator import KuaishouEmulatorCrawler, check_kuaishou_emulator_ready
    HAS_EMULATOR = True
except ImportError:
    HAS_EMULATOR = False

__all__ = [
    'BaseCrawler',
    'CrawlResult', 
    'CrawlProgress',
    'DouyinCrawler',
    'KuaishouCrawler',
    'TaobaoCrawler',
    'JDCrawler',
    'DouyinEmulatorCrawler',
    'KuaishouEmulatorCrawler',
    'check_emulator_ready',
    'check_kuaishou_emulator_ready',
    'HAS_EMULATOR',
]
