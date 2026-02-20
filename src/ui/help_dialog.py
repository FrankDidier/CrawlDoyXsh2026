"""
Help dialog with user manual for the crawler tool.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QTextBrowser, QPushButton
)
from PySide6.QtCore import Qt


class HelpDialog(QDialog):
    """Help dialog with user manual"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用帮助")
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
        tabs.addTab(self._create_emulator_tab(), "📱 模拟器设置")
        tabs.addTab(self._create_install_tab(), "⚙️ 安装配置")
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
        <h2 style="color: #00d9ff;">📖 使用说明</h2>
        
        <h3 style="color: #2ed573;">功能介绍</h3>
        <p>本工具可以自动搜索并抓取各平台的数据:</p>
        <ul>
            <li><b>抖音</b>: 直播间、短视频 (支持网页版和APP版)</li>
            <li><b>快手</b>: 直播间、短视频</li>
            <li><b>淘宝</b>: 店铺、商品</li>
            <li><b>京东</b>: 店铺、商品</li>
        </ul>
        
        <h3 style="color: #ffa502;">🔄 两种模式</h3>
        <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #0f3460;">
                <th>模式</th>
                <th>链接格式</th>
                <th>速度</th>
                <th>适用平台</th>
            </tr>
            <tr>
                <td><b>网页版</b></td>
                <td>live.douyin.com<br/>www.kuaishou.com</td>
                <td>快</td>
                <td>全部平台</td>
            </tr>
            <tr>
                <td><b>APP版 (模拟器)</b></td>
                <td>v.douyin.com<br/>(真正的APP分享链接)</td>
                <td>慢</td>
                <td>抖音、快手</td>
            </tr>
        </table>
        
        <h3 style="color: #2ed573;">使用步骤</h3>
        <ol>
            <li><b>选择模式</b>: 网页版(快) 或 APP版(真实分享链接)</li>
            <li><b>选择平台</b>: 从下拉菜单选择要搜索的平台</li>
            <li><b>选择类型</b>: 选择要搜索的内容类型</li>
            <li><b>设置数量</b>: 设置最大抓取数量</li>
            <li><b>输入关键词</b>: 在输入框输入搜索关键词</li>
            <li><b>开始抓取</b>: 点击"开始抓取"按钮</li>
            <li><b>等待完成</b>: 自动完成，请勿操作</li>
            <li><b>导出结果</b>: 抓取完成后，可导出为 Excel 或 CSV</li>
        </ol>
        
        <h3 style="color: #2ed573;">抓取的数据</h3>
        <p>对于抖音直播间，会抓取:</p>
        <ul>
            <li>直播间链接</li>
            <li>主播账号ID</li>
            <li>主播名称</li>
            <li>直播标题</li>
        </ul>
        
        <h3 style="color: #ff4757;">⚠️ 注意事项</h3>
        <ul>
            <li>首次使用可能需要完成<b>滑块验证</b>和<b>登录验证</b></li>
            <li>如出现验证，请在浏览器中手动完成</li>
            <li>抓取过程中请勿操作自动打开的浏览器窗口</li>
            <li>如果勾选"后台运行"，浏览器将不显示窗口（不推荐首次使用）</li>
            <li>网络不稳定可能导致抓取失败，请重试</li>
        </ul>
        
        <h3 style="color: #ffa502;">🔐 关于验证和登录</h3>
        <p>抖音等平台为防止机器访问，会进行以下验证:</p>
        <ol>
            <li><b>滑块验证</b>: 拖动滑块完成拼图</li>
            <li><b>手机号验证</b>: 输入手机号和验证码</li>
        </ol>
        <p>验证完成后，程序会自动继续抓取。</p>
        <p><b>提示:</b> 建议首次使用时不勾选"后台运行"，以便完成验证。</p>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_emulator_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml("""
        <h2 style="color: #00d9ff;">📱 模拟器设置 (获取真实APP分享链接)</h2>
        
        <h3 style="color: #2ed573;">什么是APP版模式?</h3>
        <p>APP版模式通过Android模拟器运行真正的抖音/快手APP，获取 <b>v.douyin.com</b> 格式的真实分享链接。</p>
        
        <h3 style="color: #ffa502;">推荐模拟器 (按速度排序)</h3>
        <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #0f3460;">
                <th>模拟器</th>
                <th>评分</th>
                <th>下载地址</th>
                <th>备注</th>
            </tr>
            <tr>
                <td><b>MuMu模拟器</b></td>
                <td>⭐ 3.8</td>
                <td>mumu.163.com</td>
                <td style="color: #2ed573;">✅ 最快！推荐</td>
            </tr>
            <tr>
                <td>雷电模拟器9</td>
                <td>⭐ 2.7</td>
                <td>ldplayer.net</td>
                <td>普通</td>
            </tr>
            <tr>
                <td>夜神模拟器</td>
                <td>⭐ 3.3</td>
                <td>yeshen.com</td>
                <td>可选</td>
            </tr>
        </table>
        
        <h3 style="color: #2ed573;">安装步骤</h3>
        <ol>
            <li><b>安装模拟器</b>: 下载并安装MuMu或雷电模拟器</li>
            <li><b>启动模拟器</b>: 等待模拟器完全启动</li>
            <li><b>安装抖音APP</b>: 在模拟器应用商店搜索"抖音"安装</li>
            <li><b>登录抖音</b>: 打开抖音APP并登录账号</li>
            <li><b>检查环境</b>: 在本工具中点击"检查环境"确认连接正常</li>
        </ol>
        
        <h3 style="color: #2ed573;">性能预估</h3>
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
            <tr style="background-color: #0f3460;">
                <th>数量</th>
                <th>预计时间</th>
            </tr>
            <tr><td>10条</td><td>~1分钟</td></tr>
            <tr><td>100条</td><td>~5-10分钟</td></tr>
            <tr><td>1000条</td><td>~1小时</td></tr>
        </table>
        
        <h3 style="color: #ff4757;">⚠️ 注意事项</h3>
        <ul>
            <li>模拟器需要至少 <b>4GB内存</b></li>
            <li>抓取时请勿操作模拟器</li>
            <li>如果雷电9太卡，建议换用 <b>MuMu模拟器</b></li>
        </ul>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_install_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2 style="color: #00d9ff;">⚙️ 安装配置</h2>
        
        <h3 style="color: #2ed573;">首次使用需要安装浏览器</h3>
        <p>本工具使用 Playwright 自动化浏览器，首次使用需要安装:</p>
        
        <pre style="background-color: #0f3460; padding: 10px; border-radius: 5px;">
# 1. 安装 Playwright
pip install playwright

# 2. 安装 Chromium 浏览器
playwright install chromium
        </pre>
        
        <h3 style="color: #2ed573;">系统要求</h3>
        <ul>
            <li><b>操作系统</b>: Windows 10/11, macOS 10.15+</li>
            <li><b>Python</b>: 3.9 或更高版本</li>
            <li><b>网络</b>: 稳定的网络连接</li>
            <li><b>内存</b>: 建议 4GB 以上</li>
        </ul>
        
        <h3 style="color: #2ed573;">常见安装问题</h3>
        <p><b>如果安装失败:</b></p>
        <ol>
            <li>确保 Python 版本正确: <code>python --version</code></li>
            <li>尝试使用管理员权限运行命令</li>
            <li>检查网络连接，浏览器下载可能需要较长时间</li>
        </ol>
        """)
        
        layout.addWidget(browser)
        return widget
    
    def _create_faq_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        browser = QTextBrowser()
        browser.setHtml("""
        <h2 style="color: #00d9ff;">❓ 常见问题</h2>
        
        <h3 style="color: #ff4757;">Q: 点击开始后报错 "Playwright未安装"</h3>
        <p><b>A:</b> 请按照"安装配置"页面的说明安装 Playwright 和 Chromium。</p>
        
        <h3 style="color: #ff4757;">Q: 浏览器打开后一直加载</h3>
        <p><b>A:</b> 可能是网络问题，请检查网络连接后重试。</p>
        
        <h3 style="color: #ff4757;">Q: 出现验证码怎么办?</h3>
        <p><b>A:</b> 请在浏览器中手动完成验证（滑块拼图或手机号验证）。
        完成后程序会自动继续。建议首次使用时不勾选"后台运行"。</p>
        
        <h3 style="color: #ff4757;">Q: 需要登录怎么办?</h3>
        <p><b>A:</b> 抖音直播搜索可能需要登录。请在弹出的浏览器中完成登录，
        登录成功后程序会自动继续抓取。</p>
        
        <h3 style="color: #ff4757;">Q: 抓取数量比设置的少</h3>
        <p><b>A:</b> 搜索结果数量取决于平台返回的结果，如果搜索结果本身较少，
        抓取数量会相应减少。</p>
        
        <h3 style="color: #ff4757;">Q: 可以同时抓取多个平台吗?</h3>
        <p><b>A:</b> 目前一次只能抓取一个平台。完成后可以再抓取其他平台。</p>
        
        <h3 style="color: #ff4757;">Q: 抓取速度很慢</h3>
        <p><b>A:</b> 为避免被平台检测，抓取速度故意放慢。这是正常现象。</p>
        
        <h3 style="color: #ff4757;">Q: 其他平台什么时候支持?</h3>
        <p><b>A:</b> 目前优先完成抖音功能，确认没问题后再开发其他平台。</p>
        """)
        
        layout.addWidget(browser)
        return widget
