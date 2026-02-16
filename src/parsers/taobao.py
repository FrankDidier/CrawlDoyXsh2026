"""
Taobao (淘宝) parser for extracting share links and store/product information.
"""

import re
from typing import Optional
from .base import BaseParser, ParseResult, Platform, ContentType


class TaobaoParser(BaseParser):
    """Parser for Taobao shared content"""
    
    platform = Platform.TAOBAO
    
    # URL patterns for Taobao
    URL_PATTERNS = [
        r'https?://e\.tb\.cn/[A-Za-z0-9\.]+\?[^\s]+',  # Short share link with params
        r'https?://e\.tb\.cn/[A-Za-z0-9\.]+',  # Short share link
        r'https?://m\.tb\.cn/[A-Za-z0-9\.]+\?[^\s]+',  # Mobile share link
        r'https?://m\.tb\.cn/[A-Za-z0-9\.]+',  # Mobile share link
        r'https?://item\.taobao\.com/item\.htm[^\s]*',  # Item page
        r'https?://detail\.tmall\.com/item\.htm[^\s]*',  # Tmall item
        r'https?://shop\d+\.taobao\.com[^\s]*',  # Store page
        r'https?://[A-Za-z0-9]+\.taobao\.com[^\s]*',  # General Taobao
        r'https?://s\.click\.taobao\.com/[^\s]+',  # Click tracking link
    ]
    
    # Pattern to detect Taobao content
    DETECTION_PATTERNS = [
        r'淘宝',
        r'天猫',
        r'tmall',
        r'taobao\.com',
        r'tb\.cn',
    ]
    
    def can_parse(self, text: str) -> bool:
        """Check if text contains Taobao content"""
        text_lower = text.lower()
        for pattern in self.DETECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """Parse Taobao shared text"""
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
        if 'shop' in text.lower() or '店铺' in text:
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
            result.error_message = "无法提取淘宝链接"
        
        return result
    
    def _extract_url(self, text: str) -> str:
        """Extract Taobao URL from text"""
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
            r'【([^】]+)】(?:店铺|旗舰店)',
            r'([^\s]+)(?:旗舰店|专卖店|官方店)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_product_name(self, text: str) -> str:
        """Extract product name from text"""
        patterns = [
            r'「([^」]+)」',  # Japanese-style quotes (common in Taobao shares)
            r'【([^】]+)】(?!淘宝|天猫|店铺)',  # Chinese brackets (not platform names)
            r'"([^"]+)"',  # Double quotes
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Filter out common non-product strings
                if match and match not in ['淘宝', '天猫', '分享', '店铺']:
                    # Take the longest match as it's likely the product name
                    if len(match) > 5:  # Product names are usually longer
                        return match.strip()
        return ""
