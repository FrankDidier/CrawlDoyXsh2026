"""
ShareLink Extractor - Main Entry Point

A desktop application for extracting share links and account information
from Chinese social media and e-commerce platforms.

Supported Platforms:
- Douyin (抖音) - Live streams & Short videos
- Kuaishou (快手) - Live streams & Short videos
- Taobao (淘宝) - Products & Stores
- JD.com (京东) - Products & Stores
"""

import sys
import os

# Add the src directory to path for imports when running as script
if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(src_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.main_window import MainWindow


def main():
    """Main application entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("分享链接提取工具")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ShareLink")
    
    # Set default font
    font = QFont("Microsoft YaHei", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
