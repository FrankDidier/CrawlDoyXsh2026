"""
Douyin (抖音) parser for extracting share links and account information.
"""

import re
from typing import Optional
from .base import BaseParser, ParseResult, Platform, ContentType


class DouyinParser(BaseParser):
    """Parser for Douyin shared content"""
    
    platform = Platform.DOUYIN
    
    # URL patterns for Douyin - updated to capture full URLs with underscores
    URL_PATTERNS = [
        r'https?://v\.douyin\.com/[A-Za-z0-9_-]+/?',  # Short share link (with underscores)
        r'https?://www\.douyin\.com/video/\d+',        # Direct video link
        r'https?://live\.douyin\.com/\d+',             # Live stream link
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
        
        # Extract account ID (抖音号) if present in text
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
                url = match.group(0)
                # Clean trailing slash if present
                return self._clean_url(url)
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
        """
        Extract account ID (抖音号) if present in text.
        
        Note: 抖音号 is usually NOT in the share text.
        Users need to click ⋯ on the profile page to see it.
        If user pastes text with "抖音号: xxx", we can extract it.
        """
        # Look for patterns like 抖音号:xxx or 抖音号：xxx
        patterns = [
            r'抖音号[：:]\s*([A-Za-z0-9_]+)',  # 抖音号: wyp6666688688
            r'ID[：:]\s*([A-Za-z0-9_]+)',      # ID: xxx
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                account_id = match.group(1).strip()
                # Validate - 抖音号 is usually alphanumeric, at least 4 chars
                if len(account_id) >= 4:
                    return account_id
        return ""
