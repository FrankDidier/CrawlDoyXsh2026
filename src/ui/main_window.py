"""
Main window for ShareLink Extractor application.
"""

import sys
import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QStatusBar, QMessageBox, QFileDialog, QSplitter, QGroupBox,
    QHeaderView, QAbstractItemView, QApplication, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont, QClipboard, QAction

from .styles import DARK_THEME
from .help_dialog import HelpDialog
from ..utils.parser_manager import ParserManager
from ..utils.exporter import Exporter
from ..utils.logger import logger
from ..parsers.base import ParseResult


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.parser_manager = ParserManager()
        self.results: List[ParseResult] = []
        
        logger.info("主窗口初始化 / Main window initializing")
        
        self.init_ui()
        self.init_menu()
        self.apply_styles()
        
        logger.info("主窗口初始化完成 / Main window initialized")
        
    def init_menu(self):
        """Initialize menu bar"""
        menubar = self.menuBar()
        
        # === 日志菜单 ===
        log_menu = menubar.addMenu("📋 日志")
        
        # 设置日志位置
        set_log_action = QAction("📂 设置日志文件位置", self)
        set_log_action.triggered.connect(self.set_log_file_location)
        log_menu.addAction(set_log_action)
        
        # 打开日志文件
        open_log_action = QAction("📄 打开当前日志", self)
        open_log_action.triggered.connect(self.open_log_file)
        log_menu.addAction(open_log_action)
        
        # 查看日志位置
        view_log_path_action = QAction("📍 查看日志路径", self)
        view_log_path_action.triggered.connect(self.show_log_path)
        log_menu.addAction(view_log_path_action)
        
        # === 帮助菜单 ===
        help_menu = menubar.addMenu("❓ 帮助")
        
        # 使用手册
        manual_action = QAction("📖 使用手册", self)
        manual_action.triggered.connect(self.show_help)
        help_menu.addAction(manual_action)
        
        # 关于
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("分享链接提取工具")
        self.setMinimumSize(900, 700)
        self.resize(1000, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 20, 25, 20)
        
        # Header with help button
        header_layout = QVBoxLayout()
        
        # Title row with help button
        title_row = QHBoxLayout()
        title_row.addStretch()
        
        title_label = QLabel("🔗 分享链接提取工具")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_row.addWidget(title_label)
        
        title_row.addStretch()
        
        # Help button
        self.help_btn = QPushButton("❓ 帮助")
        self.help_btn.setFixedWidth(80)
        self.help_btn.clicked.connect(self.show_help)
        title_row.addWidget(self.help_btn)
        
        header_layout.addLayout(title_row)
        
        subtitle_label = QLabel("从分享文本中提取链接和账号信息")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)
        
        # Splitter for input and output sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === Input Section ===
        input_group = QGroupBox("📥 输入")
        input_layout = QVBoxLayout(input_group)
        
        input_hint = QLabel("粘贴从抖音、快手、淘宝、京东等平台分享的文本")
        input_hint.setStyleSheet("color: #888; font-size: 12px; padding: 5px 0;")
        input_layout.addWidget(input_hint)
        
        self.input_text = QTextEdit()
        self.input_text.setObjectName("inputArea")
        self.input_text.setPlaceholderText(
            "在此粘贴分享文本...\n\n"
            "格式示例:\n"
            "分享文本内容... https://v.douyin.com/xxxxx/\n"
            "抖音号: wyp6666688688\n\n"
            "提示: 抖音号/快手号需要点击个人主页右上角⋯查看\n\n"
            "支持的平台:\n"
            "• 抖音 - 直播/短视频 (点⋯获取抖音号)\n"
            "• 快手 - 直播/短视频 (点⋯获取快手号)\n"
            "• 淘宝 - 商品/店铺\n"
            "• 京东 - 商品/店铺"
        )
        input_layout.addWidget(self.input_text)
        
        # Input buttons
        input_btn_layout = QHBoxLayout()
        input_btn_layout.setSpacing(10)
        
        self.paste_btn = QPushButton("📋 粘贴")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        
        self.parse_btn = QPushButton("🔍 提取")
        self.parse_btn.setObjectName("primaryButton")
        self.parse_btn.clicked.connect(self.parse_input)
        
        self.clear_input_btn = QPushButton("🗑️ 清空")
        self.clear_input_btn.setObjectName("dangerButton")
        self.clear_input_btn.clicked.connect(self.clear_input)
        
        input_btn_layout.addWidget(self.paste_btn)
        input_btn_layout.addStretch()
        input_btn_layout.addWidget(self.parse_btn)
        input_btn_layout.addWidget(self.clear_input_btn)
        
        input_layout.addLayout(input_btn_layout)
        splitter.addWidget(input_group)
        
        # === Results Section ===
        results_group = QGroupBox("📊 结果")
        results_layout = QVBoxLayout(results_group)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "平台", 
            "类型", 
            "链接", 
            "账号ID",
            "账号名称",
            "店铺名称",
            "商品名称"
        ])
        
        # Table settings
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        
        # Set default column widths
        self.results_table.setColumnWidth(0, 80)
        self.results_table.setColumnWidth(1, 80)
        self.results_table.setColumnWidth(2, 250)
        self.results_table.setColumnWidth(3, 100)
        self.results_table.setColumnWidth(4, 120)
        self.results_table.setColumnWidth(5, 120)
        self.results_table.setColumnWidth(6, 150)
        
        results_layout.addWidget(self.results_table)
        
        # Results buttons
        results_btn_layout = QHBoxLayout()
        results_btn_layout.setSpacing(10)
        
        self.copy_url_btn = QPushButton("📎 复制链接")
        self.copy_url_btn.clicked.connect(self.copy_selected_url)
        
        self.copy_all_btn = QPushButton("📋 复制全部")
        self.copy_all_btn.clicked.connect(self.copy_all_results)
        
        self.export_excel_btn = QPushButton("📊 导出Excel")
        self.export_excel_btn.setObjectName("successButton")
        self.export_excel_btn.clicked.connect(self.export_to_excel)
        
        self.export_csv_btn = QPushButton("📄 导出CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        
        self.clear_results_btn = QPushButton("🗑️ 清空结果")
        self.clear_results_btn.setObjectName("dangerButton")
        self.clear_results_btn.clicked.connect(self.clear_results)
        
        results_btn_layout.addWidget(self.copy_url_btn)
        results_btn_layout.addWidget(self.copy_all_btn)
        results_btn_layout.addStretch()
        results_btn_layout.addWidget(self.export_csv_btn)
        results_btn_layout.addWidget(self.export_excel_btn)
        results_btn_layout.addWidget(self.clear_results_btn)
        
        results_layout.addLayout(results_btn_layout)
        splitter.addWidget(results_group)
        
        # Set splitter sizes
        splitter.setSizes([300, 400])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")
        
    def apply_styles(self):
        """Apply the stylesheet"""
        self.setStyleSheet(DARK_THEME)
    
    # === Logging Functions ===
    
    def set_log_file_location(self):
        """Let user choose log file location"""
        logger.log_user_action("设置日志文件位置")
        
        default_path = logger.get_default_log_path()
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "选择日志保存位置",
            default_path,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filepath:
            if logger.set_log_file(filepath):
                QMessageBox.information(
                    self,
                    "成功",
                    f"日志已开始记录到:\n{filepath}\n\n"
                    "所有操作将被记录，方便调试问题。"
                )
                self.status_bar.showMessage(f"日志记录中: {filepath}", 5000)
            else:
                QMessageBox.warning(
                    self,
                    "错误",
                    "无法创建日志文件，请检查路径权限"
                )
    
    def open_log_file(self):
        """Open the current log file"""
        logger.log_user_action("打开日志文件")
        
        log_path = logger.get_log_file_path()
        if log_path and os.path.exists(log_path):
            import platform
            import subprocess
            
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(log_path)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", log_path])
                else:  # Linux
                    subprocess.run(["xdg-open", log_path])
                logger.info(f"打开日志文件: {log_path}")
            except Exception as e:
                logger.log_exception(e, "打开日志文件")
                QMessageBox.warning(self, "错误", f"无法打开日志文件: {e}")
        else:
            QMessageBox.information(
                self,
                "提示",
                "尚未设置日志文件。\n\n"
                "请先通过 日志 → 设置日志文件位置 来启用日志记录。"
            )
    
    def show_log_path(self):
        """Show current log file path"""
        log_path = logger.get_log_file_path()
        if log_path:
            QMessageBox.information(
                self,
                "日志路径",
                f"当前日志文件:\n{log_path}"
            )
        else:
            QMessageBox.information(
                self,
                "日志路径",
                "尚未设置日志文件。\n\n"
                "请先通过 日志 → 设置日志文件位置 来启用日志记录。"
            )
    
    # === Help Functions ===
    
    def show_help(self):
        """Show help dialog"""
        logger.log_user_action("查看帮助")
        dialog = HelpDialog(self)
        dialog.exec()
    
    def show_about(self):
        """Show about dialog"""
        logger.log_user_action("查看关于")
        QMessageBox.about(
            self,
            "关于",
            "<h3>分享链接提取工具</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>从分享文本中提取链接和账号信息</p>"
            "<p>支持平台: 抖音、快手、淘宝、京东</p>"
            "<hr>"
            "<p>如有问题，请启用日志功能后重新操作，</p>"
            "<p>然后将日志文件发送给开发者。</p>"
        )
        
    # === Main Functions ===
    
    def paste_from_clipboard(self):
        """Paste text from clipboard"""
        logger.log_user_action("粘贴剪贴板")
        
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.input_text.setPlainText(text)
            logger.info(f"粘贴内容长度: {len(text)} 字符")
            self.status_bar.showMessage("已粘贴剪贴板内容", 3000)
        else:
            logger.warning("剪贴板为空")
            self.status_bar.showMessage("剪贴板为空", 3000)
    
    def parse_input(self):
        """Parse the input text and display results"""
        logger.log_user_action("提取链接")
        
        text = self.input_text.toPlainText().strip()
        
        if not text:
            logger.warning("输入为空")
            QMessageBox.warning(
                self, 
                "提示",
                "请先输入或粘贴分享文本"
            )
            return
        
        logger.log_parse_attempt(text)
        
        # Try to parse each line as separate entry
        lines = text.split('\n')
        new_results = []
        
        # First try parsing the entire text as one entry
        try:
            result = self.parser_manager.parse(text)
            if result:
                new_results.append(result)
                logger.log_parse_result(
                    result.platform.value, True,
                    result.url, result.account_name, result.account_id
                )
            else:
                # Try parsing each non-empty line
                for line in lines:
                    line = line.strip()
                    if line:
                        result = self.parser_manager.parse(line)
                        if result:
                            new_results.append(result)
                            logger.log_parse_result(
                                result.platform.value, True,
                                result.url, result.account_name, result.account_id
                            )
        except Exception as e:
            logger.log_exception(e, "parse_input")
        
        if not new_results:
            logger.warning("未找到有效链接")
            QMessageBox.information(
                self,
                "未找到",
                "未能从输入文本中提取有效信息\n\n"
                "请确保文本包含有效的分享链接"
            )
            return
        
        # Add to results
        self.results.extend(new_results)
        self.update_results_table()
        
        logger.info(f"提取成功: {len(new_results)} 条记录")
        self.status_bar.showMessage(
            f"成功提取 {len(new_results)} 条记录", 
            5000
        )
    
    def update_results_table(self):
        """Update the results table with current results"""
        self.results_table.setRowCount(len(self.results))
        
        for row, result in enumerate(self.results):
            data = result.to_dict()
            
            self.results_table.setItem(row, 0, QTableWidgetItem(data["平台"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(data["类型"]))
            self.results_table.setItem(row, 2, QTableWidgetItem(data["链接"]))
            self.results_table.setItem(row, 3, QTableWidgetItem(data["账号ID"]))
            self.results_table.setItem(row, 4, QTableWidgetItem(data["账号名称"]))
            self.results_table.setItem(row, 5, QTableWidgetItem(data["店铺名称"]))
            self.results_table.setItem(row, 6, QTableWidgetItem(data["商品名称"]))
    
    def copy_selected_url(self):
        """Copy the URL of selected row to clipboard"""
        logger.log_user_action("复制链接")
        
        current_row = self.results_table.currentRow()
        
        if current_row < 0:
            QMessageBox.information(
                self,
                "提示",
                "请先选择一行记录"
            )
            return
        
        url_item = self.results_table.item(current_row, 2)
        if url_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(url_item.text())
            logger.info(f"复制链接: {url_item.text()}")
            self.status_bar.showMessage("已复制链接", 3000)
    
    def copy_all_results(self):
        """Copy all results to clipboard"""
        logger.log_user_action("复制全部结果")
        
        if not self.results:
            QMessageBox.information(
                self,
                "提示",
                "没有可复制的结果"
            )
            return
        
        text_lines = []
        for result in self.results:
            info = result.get_display_info()
            line_parts = [f"{key}: {value}" for key, value in info if value]
            text_lines.append(" | ".join(line_parts))
        
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(text_lines))
        logger.info(f"复制 {len(self.results)} 条记录")
        self.status_bar.showMessage(
            f"已复制 {len(self.results)} 条记录", 
            3000
        )
    
    def export_to_excel(self):
        """Export results to Excel file"""
        logger.log_user_action("导出Excel")
        
        if not self.results:
            QMessageBox.information(
                self,
                "提示",
                "没有可导出的结果"
            )
            return
        
        default_name = Exporter.generate_filename("sharelink_export", "xlsx")
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出Excel",
            default_name,
            "Excel Files (*.xlsx)"
        )
        
        if filepath:
            try:
                if Exporter.to_excel(self.results, filepath):
                    logger.log_export("Excel", filepath, True, len(self.results))
                    QMessageBox.information(
                        self,
                        "成功",
                        f"已导出到:\n{filepath}"
                    )
                else:
                    logger.log_export("Excel", filepath, False, error="导出失败")
                    QMessageBox.critical(
                        self,
                        "错误",
                        "导出失败，请检查文件路径"
                    )
            except Exception as e:
                logger.log_exception(e, "export_to_excel")
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def export_to_csv(self):
        """Export results to CSV file"""
        logger.log_user_action("导出CSV")
        
        if not self.results:
            QMessageBox.information(
                self,
                "提示",
                "没有可导出的结果"
            )
            return
        
        default_name = Exporter.generate_filename("sharelink_export", "csv")
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出CSV",
            default_name,
            "CSV Files (*.csv)"
        )
        
        if filepath:
            try:
                if Exporter.to_csv(self.results, filepath):
                    logger.log_export("CSV", filepath, True, len(self.results))
                    QMessageBox.information(
                        self,
                        "成功",
                        f"已导出到:\n{filepath}"
                    )
                else:
                    logger.log_export("CSV", filepath, False, error="导出失败")
                    QMessageBox.critical(
                        self,
                        "错误",
                        "导出失败，请检查文件路径"
                    )
            except Exception as e:
                logger.log_exception(e, "export_to_csv")
                QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def clear_input(self):
        """Clear input area"""
        logger.log_user_action("清空输入")
        self.input_text.clear()
        self.status_bar.showMessage("已清空输入", 2000)
    
    def clear_results(self):
        """Clear all results"""
        logger.log_user_action("清空结果")
        self.results.clear()
        self.results_table.setRowCount(0)
        self.status_bar.showMessage("已清空结果", 2000)
    
    def closeEvent(self, event):
        """Handle window close event"""
        logger.log_user_action("关闭应用")
        
        if self.results:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "还有未导出的结果，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                logger.info("用户取消退出")
                event.ignore()
                return
        
        logger.info("应用退出")
        event.accept()
