"""
Help dialog with user manual and logging instructions.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QTextBrowser, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class HelpDialog(QDialog):
    """Help dialog with user manual"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用手册")
        self.setMinimumSize(700, 550)
        self.resize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_usage_tab(), "📖 使用说明")
        tabs.addTab(self._create_platforms_tab(), "🌐 平台指南")
        tabs.addTab(self._create_log_tab(), "📋 日志说明")
        tabs.addTab(self._create_faq_tab(), "❓ 常见问题")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QTabWidget::pane {
                border: 2px solid #0f3460;
                border-radius: 8px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #0f3460;
                color: #888;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #00d9ff;
                color: #1a1a2e;
                font-weight: bold;
            }
            QTextBrowser {
                background-color: #16213e;
                color: #e0e0e0;
                border: none;
                padding: 15px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0f3460;
                border: 2px solid #00d9ff;
                border-radius: 8px;
                padding: 10px 20px;
                color: #00d9ff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d9ff;
                color: #1a1a2e;
            }
        """)
    
    def _create_usage_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml("""
        <h2 style="color: #00d9ff;">📖 基本使用方法</h2>
        
        <h3 style="color: #2ed573;">第一步：获取分享文本</h3>
        <p>在抖音/快手App中：</p>
        <ol>
            <li>找到要提取的直播间或短视频</li>
            <li>点击 <b>分享</b> 按钮</li>
            <li>选择 <b>复制链接</b></li>
        </ol>
        
        <h3 style="color: #2ed573;">第二步：获取账号ID（重要！）</h3>
        <p style="color: #ff4757;"><b>⚠️ 注意：账号ID不在分享文本中！</b></p>
        <ol>
            <li>进入账号的 <b>个人主页</b></li>
            <li>点击右上角 <b>⋯</b> (三个点)</li>
            <li>会显示 <b>抖音号: xxxxxx</b></li>
            <li>记下这个抖音号</li>
        </ol>
        
        <h3 style="color: #2ed573;">第三步：粘贴到软件</h3>
        <p>在输入框中粘贴，格式如下：</p>
        <pre style="background-color: #0f3460; padding: 10px; border-radius: 5px;">
分享的文本内容... https://v.douyin.com/xxxxx/
抖音号: wyp6666688688
        </pre>
        
        <h3 style="color: #2ed573;">第四步：点击提取</h3>
        <p>点击 <b>🔍 提取</b> 按钮，结果会显示在下方表格中。</p>
        
        <h3 style="color: #2ed573;">第五步：导出结果</h3>
        <p>可以导出为 Excel 或 CSV 文件保存。</p>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_platforms_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2 style="color: #00d9ff;">🌐 各平台操作指南</h2>
        
        <h3 style="color: #ff6b6b;">📱 抖音</h3>
        <table style="width: 100%;">
            <tr><td><b>分享链接：</b></td><td>分享 → 复制链接</td></tr>
            <tr><td><b>抖音号：</b></td><td>个人主页 → 点击⋯ → 查看抖音号</td></tr>
            <tr><td><b>账号名称：</b></td><td>自动从分享文本【】中提取</td></tr>
        </table>
        
        <h3 style="color: #ffa502;">📱 快手</h3>
        <table style="width: 100%;">
            <tr><td><b>分享链接：</b></td><td>分享 → 复制链接</td></tr>
            <tr><td><b>快手号：</b></td><td>个人主页 → 点击⋯ → 查看快手号</td></tr>
            <tr><td><b>账号名称：</b></td><td>自动从分享文本【】中提取</td></tr>
        </table>
        
        <h3 style="color: #ff7f50;">🛒 淘宝</h3>
        <table style="width: 100%;">
            <tr><td><b>店铺链接：</b></td><td>网页版 → 进入店铺首页 → 复制地址栏URL</td></tr>
            <tr><td><b>店铺名称：</b></td><td>自动从分享文本中提取</td></tr>
        </table>
        
        <h3 style="color: #e74c3c;">🛒 京东</h3>
        <table style="width: 100%;">
            <tr><td><b>店铺链接：</b></td><td>网页版 → 进入店铺首页 → 复制地址栏URL</td></tr>
            <tr><td><b>店铺名称：</b></td><td>自动从分享文本中提取</td></tr>
        </table>
        
        <h3 style="color: #2ed573;">✅ 提示</h3>
        <ul>
            <li>抖音/快手：使用 <b>手机App</b> 分享的链接</li>
            <li>淘宝/京东：可以使用 <b>网页版</b> 的链接</li>
        </ul>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_log_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2 style="color: #00d9ff;">📋 日志功能说明</h2>
        
        <h3 style="color: #2ed573;">什么是日志？</h3>
        <p>日志是软件运行时记录的详细信息，包括：</p>
        <ul>
            <li>您的每一个操作</li>
            <li>输入的文本内容</li>
            <li>提取的结果</li>
            <li>遇到的错误信息</li>
            <li>系统环境信息</li>
        </ul>
        
        <h3 style="color: #2ed573;">如何启用日志？</h3>
        <ol>
            <li>点击菜单栏的 <b>📋 日志</b></li>
            <li>选择 <b>设置日志文件位置</b></li>
            <li>选择保存位置（建议桌面）</li>
            <li>软件会开始记录所有操作</li>
        </ol>
        
        <h3 style="color: #2ed573;">如何发送日志给开发者？</h3>
        <ol>
            <li>在桌面找到日志文件（ShareLinkExtractor_log_日期.txt）</li>
            <li>将文件发送给开发者</li>
            <li>描述遇到的问题</li>
        </ol>
        
        <h3 style="color: #ff4757;">⚠️ 隐私提示</h3>
        <p>日志文件会记录您输入的文本内容，发送前请确认没有敏感信息。</p>
        
        <h3 style="color: #2ed573;">日志文件位置</h3>
        <ul>
            <li><b>Windows:</b> C:\\Users\\用户名\\Desktop\\ShareLinkExtractor_log_xxx.txt</li>
            <li><b>Mac:</b> /Users/用户名/Desktop/ShareLinkExtractor_log_xxx.txt</li>
        </ul>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_faq_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2 style="color: #00d9ff;">❓ 常见问题</h2>
        
        <h3 style="color: #ff4757;">Q: 为什么账号ID显示为空？</h3>
        <p><b>A:</b> 抖音号/快手号不在分享文本中。您需要：</p>
        <ol>
            <li>进入账号主页</li>
            <li>点击右上角 ⋯</li>
            <li>复制显示的抖音号/快手号</li>
            <li>在输入框中添加一行：<code>抖音号: xxxxx</code></li>
        </ol>
        
        <h3 style="color: #ff4757;">Q: 为什么链接提取不完整？</h3>
        <p><b>A:</b> 请确保复制了完整的分享文本，包括完整的URL链接。</p>
        
        <h3 style="color: #ff4757;">Q: 支持哪些平台？</h3>
        <p><b>A:</b> 目前支持：</p>
        <ul>
            <li>抖音 - 直播、短视频</li>
            <li>快手 - 直播、短视频</li>
            <li>淘宝 - 商品、店铺</li>
            <li>京东 - 商品、店铺</li>
        </ul>
        
        <h3 style="color: #ff4757;">Q: 如何批量提取？</h3>
        <p><b>A:</b> 可以一次粘贴多条分享文本，每条占一行或一段，软件会自动识别并提取。</p>
        
        <h3 style="color: #ff4757;">Q: 遇到问题怎么办？</h3>
        <p><b>A:</b></p>
        <ol>
            <li>启用日志功能（菜单 → 日志 → 设置日志文件位置）</li>
            <li>重新操作一遍出问题的步骤</li>
            <li>将日志文件发送给开发者</li>
        </ol>
        """)
        
        layout.addWidget(browser)
        return widget
