# ShareLink Extractor | 分享链接提取工具

A Windows desktop application that extracts URLs and account/store information from shared text copied from Chinese social media and e-commerce platforms.

一款Windows桌面应用程序，可从中国社交媒体和电商平台的分享文本中提取链接和账号/店铺信息。

![Platform Support](https://img.shields.io/badge/Platform-Windows-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🎯 Features | 功能特点

### Supported Platforms | 支持的平台

| Platform 平台 | Content Type 内容类型 | Extracted Info 提取信息 |
|--------------|---------------------|------------------------|
| **抖音 (Douyin)** | 直播 / 短视频 | URL, 账号ID, 账号名称 |
| **快手 (Kuaishou)** | 直播 / 短视频 | URL, 账号ID, 账号名称 |
| **淘宝 (Taobao)** | 商品 / 店铺 | URL, 店铺名称, 商品名称 |
| **京东 (JD.com)** | 商品 / 店铺 | URL, 店铺名称, 商品名称 |

### Key Features | 主要功能

- ✅ **Auto Platform Detection** - Automatically detects platform from pasted text
- ✅ **URL Extraction** - Extracts clean URLs from messy share text
- ✅ **Account Info Extraction** - Extracts account IDs and names
- ✅ **Batch Processing** - Process multiple share texts at once
- ✅ **Export to Excel/CSV** - Export results for further analysis
- ✅ **Modern UI** - Clean, dark-themed user interface
- ✅ **Bilingual Interface** - Chinese and English labels

---

## 📸 Screenshots | 截图

The application features a modern dark theme with:
- Input area for pasting shared text
- Results table showing extracted information
- Export buttons for CSV and Excel formats

---

## 🚀 Quick Start | 快速开始

### Option 1: Run from Source | 从源码运行

```bash
# 1. Clone or download the project
# 克隆或下载项目

# 2. Install Python 3.9+ if not installed
# 安装Python 3.9+（如未安装）

# 3. Install dependencies | 安装依赖
pip install -r requirements.txt

# 4. Run the application | 运行应用
python run.py
```

### Option 2: Build Windows Executable | 构建Windows可执行文件

```bash
# Install dependencies | 安装依赖
pip install -r requirements.txt

# Build executable | 构建可执行文件
python build.py --release

# Or use the batch file on Windows | 或在Windows上使用批处理文件
build_windows.bat release
```

The executable will be created at `dist/ShareLinkExtractor.exe`

---

## 📖 Usage Guide | 使用指南

### Step 1: Copy Share Text | 复制分享文本

Copy the share text from your mobile app. Example:

**抖音 Douyin:**
```
2- #在抖音，记录美好生活#【绝地苟老六】正在直播，来和我一起支持Ta吧。复制下方链接，打开【抖音】，直接观看直播！ https://v.douyin.com/RfiaMUy15vo/ 0@5.com :9pm
```

**淘宝 Taobao:**
```
【淘宝】7天无理由退货 https://e.tb.cn/h.7vUJnkd5IQyLbmr?tk=uEXDUlwjL4E HU926 「新款饺子器木制圆形厨房家用擀饺子皮神器模具包水面皮不粘饺子皮」
点击链接直接打开 或者 淘宝搜索直接打开
```

### Step 2: Paste and Extract | 粘贴并提取

1. Open ShareLink Extractor
2. Click "📋 粘贴 Paste" or paste directly into the input area
3. Click "🔍 提取 Extract" button
4. View the extracted information in the results table

### Step 3: Export Results | 导出结果

- Click "📊 导出Excel Export" to save as Excel file
- Click "📄 导出CSV" to save as CSV file
- Click "📎 复制链接 Copy URL" to copy selected URL
- Click "📋 复制全部 Copy All" to copy all results

---

## 🏗️ Project Structure | 项目结构

```
CrawProj/
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── parsers/             # Platform-specific parsers
│   │   ├── __init__.py
│   │   ├── base.py          # Base parser class
│   │   ├── douyin.py        # Douyin parser
│   │   ├── kuaishou.py      # Kuaishou parser
│   │   ├── taobao.py        # Taobao parser
│   │   └── jd.py            # JD.com parser
│   ├── ui/                  # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py   # Main window
│   │   └── styles.py        # Theme styles
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── parser_manager.py
│       └── exporter.py
├── run.py                   # Quick run script
├── build.py                 # Build script
├── build_windows.bat        # Windows build batch file
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🔧 Requirements | 系统要求

- **OS**: Windows 10/11 (for .exe), macOS/Linux (for Python)
- **Python**: 3.9 or higher (if running from source)
- **Dependencies**: See `requirements.txt`

---

## 📝 Notes | 注意事项

1. **Mobile App Links**: For Douyin and Kuaishou, use links shared from the mobile app, not web browser links.
   
   对于抖音和快手，请使用移动App分享的链接，而不是网页版链接。

2. **Web Links OK for E-commerce**: Taobao and JD links from web browsers work fine.
   
   淘宝和京东的网页版链接可以正常使用。

3. **Clean URLs**: The tool extracts only the URL portion, removing extra promotional text.
   
   工具只提取URL部分，移除额外的推广文字。

---

## 🛠️ Development | 开发

### Adding New Platform Support | 添加新平台支持

1. Create a new parser in `src/parsers/`
2. Inherit from `BaseParser`
3. Implement `can_parse()` and `parse()` methods
4. Add the parser to `ParserManager` in `src/utils/parser_manager.py`

Example:
```python
from .base import BaseParser, ParseResult, Platform, ContentType

class NewPlatformParser(BaseParser):
    platform = Platform.NEW
    
    def can_parse(self, text: str) -> bool:
        return 'newplatform.com' in text.lower()
    
    def parse(self, text: str) -> ParseResult:
        # Implement parsing logic
        pass
```

---

## 📄 License | 许可证

MIT License - Feel free to use and modify.

---

## 🤝 Contributing | 贡献

Contributions are welcome! Please feel free to submit issues or pull requests.

欢迎贡献！请随时提交问题或拉取请求。
