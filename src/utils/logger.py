"""
Logging utility for ShareLink Extractor.
Records all operations for debugging purposes.
Works on both Windows and macOS.
"""

import os
import sys
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional


class AppLogger:
    """Application logger that saves logs to user-specified location"""
    
    _instance: Optional['AppLogger'] = None
    _logger: Optional[logging.Logger] = None
    _log_file_path: Optional[str] = None
    _file_handler: Optional[logging.FileHandler] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """Initialize the logger"""
        self._logger = logging.getLogger('ShareLinkExtractor')
        self._logger.setLevel(logging.DEBUG)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self._logger.addHandler(console_handler)
        
        # Log system info on startup
        self._log_system_info()
    
    def _log_system_info(self):
        """Log system information for debugging"""
        self._logger.info("=" * 60)
        self._logger.info("ShareLink Extractor 启动 / Application Started")
        self._logger.info("=" * 60)
        self._logger.info(f"操作系统 / OS: {platform.system()} {platform.release()}")
        self._logger.info(f"系统版本 / Version: {platform.version()}")
        self._logger.info(f"Python版本 / Python: {sys.version}")
        self._logger.info(f"平台 / Platform: {platform.platform()}")
        self._logger.info(f"机器 / Machine: {platform.machine()}")
        self._logger.info("=" * 60)
    
    def set_log_file(self, file_path: str) -> bool:
        """
        Set the log file path and start file logging.
        
        Args:
            file_path: Full path to the log file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove existing file handler if any
            if self._file_handler:
                self._logger.removeHandler(self._file_handler)
                self._file_handler.close()
            
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Create file handler
            self._file_handler = logging.FileHandler(
                file_path, 
                mode='a', 
                encoding='utf-8'
            )
            self._file_handler.setLevel(logging.DEBUG)
            
            # Detailed format for file logging
            file_format = logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self._file_handler.setFormatter(file_format)
            self._logger.addHandler(self._file_handler)
            
            self._log_file_path = file_path
            self._logger.info(f"日志文件已设置 / Log file set: {file_path}")
            self._log_system_info()
            
            return True
        except Exception as e:
            self._logger.error(f"设置日志文件失败 / Failed to set log file: {e}")
            return False
    
    def get_log_file_path(self) -> Optional[str]:
        """Get current log file path"""
        return self._log_file_path
    
    @staticmethod
    def get_default_log_path() -> str:
        """
        Get the default log file path based on OS.
        Returns Desktop path for both Windows and macOS.
        """
        system = platform.system()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ShareLinkExtractor_log_{timestamp}.txt"
        
        if system == "Windows":
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        else:  # macOS, Linux
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        
        return os.path.join(desktop, filename)
    
    def debug(self, message: str):
        """Log debug message"""
        if self._logger:
            self._logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        if self._logger:
            self._logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        if self._logger:
            self._logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        if self._logger:
            self._logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        if self._logger:
            self._logger.critical(message)
    
    def log_user_action(self, action: str, details: str = ""):
        """Log user actions for debugging"""
        msg = f"用户操作 / User Action: {action}"
        if details:
            msg += f" | 详情 / Details: {details}"
        self.info(msg)
    
    def log_parse_attempt(self, text: str):
        """Log parse attempt"""
        # Truncate long text for logging
        display_text = text[:200] + "..." if len(text) > 200 else text
        self.debug(f"解析输入 / Parse input: {display_text}")
    
    def log_parse_result(self, platform: str, success: bool, url: str = "", 
                         account_name: str = "", account_id: str = "", error: str = ""):
        """Log parse result"""
        if success:
            self.info(f"解析成功 / Parse success: 平台={platform}, URL={url}, "
                     f"账号名称={account_name}, 账号ID={account_id}")
        else:
            self.warning(f"解析失败 / Parse failed: 平台={platform}, 错误={error}")
    
    def log_export(self, export_type: str, file_path: str, success: bool, 
                   record_count: int = 0, error: str = ""):
        """Log export operation"""
        if success:
            self.info(f"导出成功 / Export success: 类型={export_type}, "
                     f"文件={file_path}, 记录数={record_count}")
        else:
            self.error(f"导出失败 / Export failed: 类型={export_type}, 错误={error}")
    
    def log_exception(self, exception: Exception, context: str = ""):
        """Log exception with full details"""
        import traceback
        self.error(f"异常 / Exception in {context}: {type(exception).__name__}: {exception}")
        self.error(f"堆栈跟踪 / Traceback:\n{traceback.format_exc()}")


# Global logger instance
logger = AppLogger()
