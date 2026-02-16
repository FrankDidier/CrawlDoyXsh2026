"""
Douyin (抖音) parser for extracting share links and account information.
"""

import re
from typing import Optional
from .base import BaseParser, ParseResult, Platform, ContentType


class DouyinParser(BaseParser):
    """Parser for Douyin shared content"""
    
    platform = Platform.DOUYIN
    
    # URL patterns for Douyin
    URL_PATTERNS = [
        r'https?://v\.douyin\.com/[A-Za-z0-9]+/?',  # Short share link
        r'https?://www\.douyin\.com/video/\d+',      # Direct video link
        r'https?://live\.douyin\.com/\d+',           # Live stream link
        r'https?://www\.douyin\.com/user/[A-Za-z0-9_-]+',  # User profile
    ]
    
    # Pattern to detect Douyin content
    DETECTION_PATTERNS = [
        r'抖音',
        r'douyin\.com',
        r'v\.douyin\.com',
    ]
    
    def can_parse(self, text: str) -> bool:
        """Check if text contains Douyin content"""
        text_lower = text.lower()
        for pattern in self.DETECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """Parse Douyin shared text"""
        if not self.can_parse(text):
            return None
        
        result = ParseResult(
            platform=self.platform,
            content_type=ContentType.UNKNOWN,
            raw_text=text,
            success=False
        )
        
        # Extract URL
        url = self._extract_url(text)
        if url:
            result.url = url
        
        # Determine content type and extract account info
        if '直播' in text or 'live.douyin.com' in text:
            result.content_type = ContentType.LIVE_STREAM
        else:
            result.content_type = ContentType.SHORT_VIDEO
        
        # Extract account name from 【】brackets
        account_name = self._extract_account_name(text)
        if account_name:
            result.account_name = account_name
        
        # Extract account ID if present
        account_id = self._extract_account_id(text)
        if account_id:
            result.account_id = account_id
        
        result.success = bool(result.url)
        if not result.success:
            result.error_message = "无法提取抖音链接"
        
        return result
    
    def _extract_url(self, text: str) -> str:
        """Extract Douyin URL from text"""
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return self._clean_url(match.group(0))
        return ""
    
    def _extract_account_name(self, text: str) -> str:
        """Extract account name from brackets like 【账号名】"""
        # Pattern for 【...】 brackets (Chinese)
        patterns = [
            r'【([^】]+)】(?=.*(?:正在直播|直播中|的视频|分享))',  # Context-aware
            r'【([^】]+)】',  # General bracket pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Filter out common non-name content
                if name not in ['抖音', '直播', '视频', '分享']:
                    return name
        return ""
    
    def _extract_account_id(self, text: str) -> str:
        """Extract account ID if present in text"""
        # Look for patterns like @username or 抖音号:xxx
        patterns = [
            r'抖音号[：:]\s*(\w+)',
            r'@([A-Za-z0-9_]+)',
            r'ID[：:]\s*(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""
