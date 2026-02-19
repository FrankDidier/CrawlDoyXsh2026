"""
Main window for ShareLink Crawler application.
Automatically crawl data from Douyin, Kuaishou, Taobao, JD.
"""

import sys
import os
import asyncio
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QStatusBar, QMessageBox, QFileDialog, QGroupBox, QComboBox,
    QHeaderView, QAbstractItemView, QApplication, QProgressBar,
    QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

from .styles import DARK_THEME
from .help_dialog import HelpDialog
from ..crawlers.base import CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType
from ..crawlers.douyin import DouyinCrawler
from ..utils.exporter import Exporter
from ..utils.logger import logger


class CrawlerWorker(QThread):
    """Worker thread for running crawler"""
    progress_updated = Signal(object)  # CrawlProgress
    result_added = Signal(object)      # CrawlResult
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, crawler, keyword: str, content_type: ContentType, 
                 max_results: int, headless: bool):
        super().__init__()
        self.crawler = crawler
        self.keyword = keyword
        self.content_type = content_type
        self.max_results = max_results
        self.headless = headless
    
    def run(self):
        try:
            # Set up callbacks
            self.crawler.set_progress_callback(
                lambda p: self.progress_updated.emit(p)
            )
            self.crawler.set_result_callback(
                lambda r: self.result_added.emit(r)
            )
            
            # Run async crawler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.crawler.search(
                        self.keyword, 
                        self.content_type, 
                        self.max_results,
                        self.headless
                    )
                )
            finally:
                loop.close()
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.results: List[CrawlResult] = []
        self.crawler = None
        self.worker = None
        
        logger.info("主窗口初始化 / Main window initializing")
        
        self.init_ui()
        self.apply_styles()
        
        logger.info("主窗口初始化完成 / Main window initialized")
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("关键词搜索抓取工具")
        self.setMinimumSize(1000, 750)
        self.resize(1100, 850)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # === Header ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 关键词搜索抓取工具")
        title_label.setObjectName("titleLabel")
        
        self.help_btn = QPushButton("❓ 帮助")
        self.help_btn.setFixedWidth(80)
        self.help_btn.clicked.connect(self.show_help)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.help_btn)
        main_layout.addLayout(header_layout)
        
        # === Search Settings ===
        search_group = QGroupBox("🔎 搜索设置")
        search_layout = QGridLayout(search_group)
        search_layout.setSpacing(15)
        
        # Row 1: Platform and Type selection
        search_layout.addWidget(QLabel("平台:"), 0, 0)
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["抖音", "快手", "淘宝", "京东"])
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        search_layout.addWidget(self.platform_combo, 0, 1)
        
        search_layout.addWidget(QLabel("类型:"), 0, 2)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["直播", "短视频"])
        search_layout.addWidget(self.type_combo, 0, 3)
        
        search_layout.addWidget(QLabel("最大数量:"), 0, 4)
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 100000)  # Allow up to 100,000
        self.max_results_spin.setValue(100)
        self.max_results_spin.setSingleStep(100)
        self.max_results_spin.setToolTip("建议: 100-1000条。抓取数千条可能需要较长时间。")
        search_layout.addWidget(self.max_results_spin, 0, 5)
        
        # Row 2: Keyword input
        search_layout.addWidget(QLabel("关键词:"), 1, 0)
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入要搜索的关键词，如: 美食、游戏、教育...")
        self.keyword_input.returnPressed.connect(self.start_crawl)
        search_layout.addWidget(self.keyword_input, 1, 1, 1, 4)
        
        # Headless checkbox
        self.headless_check = QCheckBox("后台运行")
        self.headless_check.setToolTip("勾选后浏览器在后台运行，不显示窗口")
        search_layout.addWidget(self.headless_check, 1, 5)
        
        # Row 3: Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始抓取")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self.start_crawl)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setObjectName("dangerButton")
        self.stop_btn.clicked.connect(self.stop_crawl)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        
        search_layout.addLayout(btn_layout, 2, 0, 1, 6)
        
        main_layout.addWidget(search_group)
        
        # === Progress ===
        progress_group = QGroupBox("📊 进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setStyleSheet("color: #888;")
        progress_layout.addWidget(self.progress_label)
        
        main_layout.addWidget(progress_group)
        
        # === Results Table ===
        results_group = QGroupBox("📋 抓取结果")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "序号", "APP分享文本", "链接", "账号ID", "账号名称", "标题", "抓取时间"
        ])
        
        # Table settings
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        
        # Column widths
        self.results_table.setColumnWidth(0, 50)
        self.results_table.setColumnWidth(1, 400)  # APP分享文本 - wider
        self.results_table.setColumnWidth(2, 250)
        self.results_table.setColumnWidth(3, 100)
        self.results_table.setColumnWidth(4, 100)
        self.results_table.setColumnWidth(5, 150)
        
        results_layout.addWidget(self.results_table)
        
        # Results buttons
        results_btn_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 复制全部")
        self.copy_btn.clicked.connect(self.copy_all_results)
        
        self.export_excel_btn = QPushButton("📊 导出Excel")
        self.export_excel_btn.setObjectName("successButton")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        
        self.export_csv_btn = QPushButton("📄 导出CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setObjectName("dangerButton")
        self.clear_btn.clicked.connect(self.clear_results)
        
        results_btn_layout.addWidget(self.copy_btn)
        results_btn_layout.addStretch()
        results_btn_layout.addWidget(self.export_csv_btn)
        results_btn_layout.addWidget(self.export_excel_btn)
        results_btn_layout.addWidget(self.clear_btn)
        
        results_layout.addLayout(results_btn_layout)
        main_layout.addWidget(results_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪 - 选择平台和类型，输入关键词后点击开始抓取")
    
    def apply_styles(self):
        """Apply the stylesheet"""
        self.setStyleSheet(DARK_THEME)
    
    def on_platform_changed(self, platform: str):
        """Handle platform selection change"""
        logger.log_user_action(f"选择平台: {platform}")
        
        # Update type options based on platform
        self.type_combo.clear()
        
        if platform in ["抖音", "快手"]:
            self.type_combo.addItems(["直播", "短视频"])
        elif platform in ["淘宝", "京东"]:
            self.type_combo.addItems(["店铺", "商品"])
    
    def start_crawl(self):
        """Start crawling"""
        keyword = self.keyword_input.text().strip()
        
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        
        platform = self.platform_combo.currentText()
        content_type_text = self.type_combo.currentText()
        max_results = self.max_results_spin.value()
        headless = self.headless_check.isChecked()
        
        logger.log_user_action(f"开始抓取: {platform} {content_type_text} '{keyword}'")
        
        # Map to ContentType
        type_map = {
            "直播": ContentType.LIVE,
            "短视频": ContentType.VIDEO,
            "店铺": ContentType.STORE,
            "商品": ContentType.PRODUCT,
        }
        content_type = type_map.get(content_type_text)
        
        # Create appropriate crawler
        if platform == "抖音":
            self.crawler = DouyinCrawler()
        else:
            QMessageBox.information(
                self, "提示", 
                f"{platform}抓取功能开发中...\n\n"
                "请先测试抖音功能，确认没问题后再开发其他平台。"
            )
            return
        
        # Disable UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.keyword_input.setEnabled(False)
        self.platform_combo.setEnabled(False)
        self.type_combo.setEnabled(False)
        
        # Start worker thread
        self.worker = CrawlerWorker(
            self.crawler, keyword, content_type, max_results, headless
        )
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.result_added.connect(self.on_result_added)
        self.worker.finished.connect(self.on_crawl_finished)
        self.worker.error.connect(self.on_crawl_error)
        self.worker.start()
    
    def stop_crawl(self):
        """Stop crawling"""
        logger.log_user_action("停止抓取")
        
        if self.crawler:
            self.crawler.cancel()
        
        self.progress_label.setText("正在停止...")
    
    def on_progress_updated(self, progress: CrawlProgress):
        """Handle progress update"""
        self.progress_bar.setValue(progress.percentage)
        self.progress_label.setText(progress.message)
        self.status_bar.showMessage(
            f"状态: {progress.status.value} | {progress.message}"
        )
        
        # Change label color based on status
        if progress.status == CrawlStatus.WAITING:
            # Orange/warning for CAPTCHA
            self.progress_label.setStyleSheet("color: #ff9500; font-weight: bold; font-size: 14px;")
        elif progress.status == CrawlStatus.ERROR:
            # Red for error
            self.progress_label.setStyleSheet("color: #ff3b30; font-weight: bold;")
        elif progress.status == CrawlStatus.COMPLETED:
            # Green for success
            self.progress_label.setStyleSheet("color: #34c759;")
        else:
            # Normal gray
            self.progress_label.setStyleSheet("color: #888;")
    
    def on_result_added(self, result: CrawlResult):
        """Handle new result"""
        self.results.append(result)
        self._add_result_to_table(result)
    
    def _add_result_to_table(self, result: CrawlResult):
        """Add a result to the table"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.results_table.setItem(row, 1, QTableWidgetItem(result.share_text))  # APP分享文本
        self.results_table.setItem(row, 2, QTableWidgetItem(result.url))
        self.results_table.setItem(row, 3, QTableWidgetItem(result.account_id))
        self.results_table.setItem(row, 4, QTableWidgetItem(result.account_name))
        self.results_table.setItem(row, 5, QTableWidgetItem(result.title))
        self.results_table.setItem(row, 6, QTableWidgetItem(result.crawled_at))
    
    def on_crawl_finished(self):
        """Handle crawl completion"""
        logger.info(f"抓取完成: {len(self.results)} 条结果")
        
        self._reset_ui()
        
        QMessageBox.information(
            self, "完成",
            f"抓取完成!\n\n共获取 {len(self.results)} 条结果"
        )
    
    def on_crawl_error(self, error: str):
        """Handle crawl error"""
        logger.error(f"抓取错误: {error}")
        
        self._reset_ui()
        
        QMessageBox.critical(
            self, "错误",
            f"抓取过程中出现错误:\n\n{error}\n\n"
            "请确保:\n"
            "1. 已安装 Playwright: pip install playwright\n"
            "2. 已安装浏览器: playwright install chromium\n"
            "3. 网络连接正常"
        )
    
    def _reset_ui(self):
        """Reset UI after crawl"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.keyword_input.setEnabled(True)
        self.platform_combo.setEnabled(True)
        self.type_combo.setEnabled(True)
        self.worker = None
    
    def copy_all_results(self):
        """Copy all results to clipboard"""
        logger.log_user_action("复制全部结果")
        
        if not self.results:
            QMessageBox.information(self, "提示", "没有可复制的结果")
            return
        
        lines = []
        for r in self.results:
            lines.append(f"{r.url}\t{r.account_id}\t{r.account_name}\t{r.title}")
        
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
        
        self.status_bar.showMessage(f"已复制 {len(self.results)} 条记录", 3000)
    
    def export_to_excel(self):
        """Export results to Excel"""
        logger.log_user_action("导出Excel")
        
        if not self.results:
            QMessageBox.information(self, "提示", "没有可导出的结果")
            return
        
        default_name = Exporter.generate_filename("crawl_results", "xlsx")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出Excel", default_name, "Excel Files (*.xlsx)"
        )
        
        if filepath:
            # Convert CrawlResult to format Exporter expects
            if Exporter.to_excel_from_dicts(
                [r.to_dict() for r in self.results], 
                filepath
            ):
                logger.info(f"导出成功: {filepath}")
                QMessageBox.information(self, "成功", f"已导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "错误", "导出失败")
    
    def export_to_csv(self):
        """Export results to CSV"""
        logger.log_user_action("导出CSV")
        
        if not self.results:
            QMessageBox.information(self, "提示", "没有可导出的结果")
            return
        
        default_name = Exporter.generate_filename("crawl_results", "csv")
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", default_name, "CSV Files (*.csv)"
        )
        
        if filepath:
            if Exporter.to_csv_from_dicts(
                [r.to_dict() for r in self.results],
                filepath
            ):
                logger.info(f"导出成功: {filepath}")
                QMessageBox.information(self, "成功", f"已导出到:\n{filepath}")
            else:
                QMessageBox.critical(self, "错误", "导出失败")
    
    def clear_results(self):
        """Clear all results"""
        logger.log_user_action("清空结果")
        
        self.results.clear()
        self.results_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_label.setText("准备就绪")
        self.status_bar.showMessage("已清空结果", 2000)
    
    def show_help(self):
        """Show help dialog"""
        logger.log_user_action("查看帮助")
        dialog = HelpDialog(self)
        dialog.exec()
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.log_user_action("关闭应用")
        
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "抓取正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            if self.crawler:
                self.crawler.cancel()
        
        logger.info("应用退出")
        event.accept()
