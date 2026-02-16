"""
Parser manager that coordinates all platform parsers.
"""

from typing import List, Optional
from ..parsers import (
    DouyinParser, KuaishouParser, TaobaoParser, JDParser,
    BaseParser, ParseResult
)
from ..parsers.base import Platform


class ParserManager:
    """Manages all platform parsers and routes text to appropriate parser"""
    
    def __init__(self):
        self.parsers: List[BaseParser] = [
            DouyinParser(),
            KuaishouParser(),
            TaobaoParser(),
            JDParser(),
        ]
    
    def parse(self, text: str) -> Optional[ParseResult]:
        """
        Parse text using the first matching parser.
        Returns ParseResult if successful, None if no parser matches.
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        for parser in self.parsers:
            if parser.can_parse(text):
                result = parser.parse(text)
                if result and result.success:
                    return result
        
        return None
    
    def parse_all(self, text: str) -> List[ParseResult]:
        """
        Try all parsers and return all successful results.
        Useful when text might contain multiple share links.
        """
        results = []
        
        if not text or not text.strip():
            return results
        
        text = text.strip()
        
        for parser in self.parsers:
            if parser.can_parse(text):
                result = parser.parse(text)
                if result and result.success:
                    results.append(result)
        
        return results
    
    def parse_batch(self, texts: List[str]) -> List[ParseResult]:
        """
        Parse multiple texts and return all successful results.
        """
        results = []
        
        for text in texts:
            result = self.parse(text)
            if result:
                results.append(result)
        
        return results
    
    def detect_platform(self, text: str) -> Platform:
        """
        Detect which platform the text is from without full parsing.
        """
        for parser in self.parsers:
            if parser.can_parse(text):
                return parser.platform
        
        return Platform.UNKNOWN
