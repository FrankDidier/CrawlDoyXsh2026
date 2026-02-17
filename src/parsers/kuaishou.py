"""
Kuaishou (快手) parser for extracting share links and account information.
"""

import re
from typing import Optional
from .base import BaseParser, ParseResult, Platform, ContentType


class KuaishouParser(BaseParser):
    """Parser for Kuaishou shared content"""
    
    platform = Platform.KUAISHOU
    
    # URL patterns for Kuaishou - updated to capture full URLs
    URL_PATTERNS = [
        r'https?://v\.kuaishou\.com/[A-Za-z0-9_-]+/?',  # Short share link
        r'https?://www\.kuaishou\.com/short-video/[A-Za-z0-9_-]+',  # Short video
        r'https?://www\.kuaishou\.com/f/[A-Za-z0-9_-]+',  # Share link
        r'https?://live\.kuaishou\.com/u/[A-Za-z0-9_-]+',  # Live stream
        r'https?://www\.kuaishou\.com/profile/[A-Za-z0-9_-]+',  # Profile
        r'https?://c\.kuaishou\.com/fw/photo/[A-Za-z0-9_-]+',  # Photo/video
    ]
    
    # Pattern to detect Kuaishou content
    DETECTION_PATTERNS = [
        r'快手',
        r'kuaishou\.com',
        r'v\.kuaishou\.com',
    ]
    
    def can_parse(self, text: str) -> bool:
        """Check if text contains Kuaishou content"""
        text_lower = text.lower()
        for pattern in self.DETECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """Parse Kuaishou shared text"""
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
        
        # Determine content type
        if '直播' in text or 'live.kuaishou.com' in text:
            result.content_type = ContentType.LIVE_STREAM
        else:
            result.content_type = ContentType.SHORT_VIDEO
        
        # Extract account name
        account_name = self._extract_account_name(text)
        if account_name:
            result.account_name = account_name
        
        # Extract account ID (快手号)
        account_id = self._extract_account_id(text)
        if account_id:
            result.account_id = account_id
        
        result.success = bool(result.url)
        if not result.success:
            result.error_message = "无法提取快手链接"
        
        return result
    
    def _extract_url(self, text: str) -> str:
        """Extract Kuaishou URL from text"""
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return self._clean_url(match.group(0))
        return ""
    
    def _extract_account_name(self, text: str) -> str:
        """Extract account name from text"""
        patterns = [
            r'【([^】]+)】',  # Chinese brackets
            r'「([^」]+)」',  # Alternative brackets
            r'"([^"]+)"的(?:快手|作品)',  # Quoted name
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Filter common non-name content
                if name not in ['快手', '直播', '视频', '分享']:
                    return name
        return ""
    
    def _extract_account_id(self, text: str) -> str:
        """
        Extract account ID (快手号) if present in text.
        
        Note: 快手号 is usually NOT in the share text.
        Users need to click profile menu to see it.
        """
        patterns = [
            r'快手号[：:]\s*([A-Za-z0-9_]+)',  # 快手号: xxx
            r'ID[：:]\s*([A-Za-z0-9_]+)',      # ID: xxx
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                account_id = match.group(1).strip()
                if len(account_id) >= 4:
                    return account_id
        return ""
