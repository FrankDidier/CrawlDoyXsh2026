"""
JD.com (京东) parser for extracting share links and store/product information.
"""

import re
from typing import Optional
from .base import BaseParser, ParseResult, Platform, ContentType


class JDParser(BaseParser):
    """Parser for JD.com shared content"""
    
    platform = Platform.JD
    
    # URL patterns for JD
    URL_PATTERNS = [
        r'https?://[A-Za-z0-9]+\.jd\.com/[^\s]+',  # General JD links
        r'https?://item\.jd\.com/\d+\.html',  # Product page
        r'https?://mall\.jd\.com/index-\d+\.html',  # Store page
        r'https?://shop\.jd\.com/[^\s]+',  # Shop page
        r'https?://u\.jd\.com/[A-Za-z0-9]+',  # Short share link
        r'https?://3\.cn/[A-Za-z0-9-]+',  # Super short link
        r'https?://item\.m\.jd\.com/product/\d+\.html',  # Mobile product
    ]
    
    # Pattern to detect JD content
    DETECTION_PATTERNS = [
        r'京东',
        r'jd\.com',
        r'u\.jd\.com',
        r'3\.cn',
    ]
    
    def can_parse(self, text: str) -> bool:
        """Check if text contains JD content"""
        text_lower = text.lower()
        for pattern in self.DETECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """Parse JD shared text"""
        if not self.can_parse(text):
            return None
        
        result = ParseResult(
            platform=self.platform,
            content_type=ContentType.PRODUCT,
            raw_text=text,
            success=False
        )
        
        # Extract URL
        url = self._extract_url(text)
        if url:
            result.url = url
        
        # Determine if it's a store or product
        if 'shop' in text.lower() or 'mall' in text.lower() or '店铺' in text:
            result.content_type = ContentType.STORE
        else:
            result.content_type = ContentType.PRODUCT
        
        # Extract store name
        store_name = self._extract_store_name(text)
        if store_name:
            result.store_name = store_name
        
        # Extract product name
        product_name = self._extract_product_name(text)
        if product_name:
            result.product_name = product_name
        
        result.success = bool(result.url)
        if not result.success:
            result.error_message = "无法提取京东链接"
        
        return result
    
    def _extract_url(self, text: str) -> str:
        """Extract JD URL from text"""
        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, text)
            if match:
                url = match.group(0)
                # Clean up - remove trailing Chinese characters
                url = re.sub(r'[\u4e00-\u9fff]+$', '', url)
                return self._clean_url(url)
        return ""
    
    def _extract_store_name(self, text: str) -> str:
        """Extract store name from text"""
        patterns = [
            r'店铺[：:]\s*([^\s,，]+)',
            r'【([^】]+)】(?:店铺|旗舰店|自营)',
            r'([^\s]+)(?:京东自营|旗舰店|专卖店|官方店)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_product_name(self, text: str) -> str:
        """Extract product name from text"""
        patterns = [
            r'「([^」]+)」',  # Japanese-style quotes
            r'【([^】]+)】(?!京东|店铺)',  # Chinese brackets
            r'"([^"]+)"',  # Double quotes
            r'《([^》]+)》',  # Book-style brackets
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and match not in ['京东', '分享', '店铺', '自营']:
                    if len(match) > 5:
                        return match.strip()
        return ""
