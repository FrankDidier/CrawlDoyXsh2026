"""
Browser helper utilities for Playwright.
Handles browser installation and fallback to system Chrome.
Supports multiple browsers: Chrome, Edge, IE, 360, QQ etc.
"""

import os
import sys
import subprocess
from typing import Optional, Tuple

# Try to import playwright-stealth
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    print("提示: 安装 playwright-stealth 可以更好地绕过反爬虫检测")
    print("运行: pip install playwright-stealth")


# Browser selection mapping
BROWSER_CHANNELS = {
    "Chrome": "chrome",
    "Edge": "msedge",
    "IE": None,  # IE uses different approach
    "360浏览器": None,
    "QQ浏览器": None,
    "自动": None,
}


def get_chrome_path() -> Optional[str]:
    """Get path to system Chrome executable"""
    if sys.platform == 'win32':
        # Windows Chrome paths
        paths = [
            os.path.expandvars(r'%PROGRAMFILES%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe'),
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        ]
    elif sys.platform == 'darwin':
        # macOS Chrome paths
        paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ]
    else:
        # Linux Chrome paths
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
        ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


def get_edge_path() -> Optional[str]:
    """Get path to system Edge executable (Windows)"""
    if sys.platform != 'win32':
        return None
    
    paths = [
        os.path.expandvars(r'%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe'),
        os.path.expandvars(r'%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe'),
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


def get_ie_path() -> Optional[str]:
    """Get path to Internet Explorer executable (Windows)"""
    if sys.platform != 'win32':
        return None
    
    paths = [
        os.path.expandvars(r'%PROGRAMFILES%\Internet Explorer\iexplore.exe'),
        os.path.expandvars(r'%PROGRAMFILES(X86)%\Internet Explorer\iexplore.exe'),
        r'C:\Program Files\Internet Explorer\iexplore.exe',
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


def get_360_browser_path() -> Optional[str]:
    """Get path to 360 browser executable (Windows)"""
    if sys.platform != 'win32':
        return None
    
    paths = [
        os.path.expandvars(r'%LOCALAPPDATA%\360Chrome\Chrome\Application\360chrome.exe'),
        os.path.expandvars(r'%PROGRAMFILES%\360\360se6\Application\360se.exe'),
        os.path.expandvars(r'%PROGRAMFILES(X86)%\360\360se6\Application\360se.exe'),
        r'C:\Program Files\360\360se6\Application\360se.exe',
        r'C:\Users\Public\Desktop\360安全浏览器.lnk',
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


def get_qq_browser_path() -> Optional[str]:
    """Get path to QQ browser executable (Windows)"""
    if sys.platform != 'win32':
        return None
    
    paths = [
        os.path.expandvars(r'%LOCALAPPDATA%\Tencent\QQBrowser\QQBrowser.exe'),
        os.path.expandvars(r'%PROGRAMFILES%\Tencent\QQBrowser\QQBrowser.exe'),
        os.path.expandvars(r'%PROGRAMFILES(X86)%\Tencent\QQBrowser\QQBrowser.exe'),
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None


def get_browser_by_name(browser_name: str) -> Optional[str]:
    """Get browser executable path by name"""
    browser_map = {
        "Chrome": get_chrome_path,
        "Edge": get_edge_path,
        "IE": get_ie_path,
        "360浏览器": get_360_browser_path,
        "QQ浏览器": get_qq_browser_path,
    }
    
    if browser_name in browser_map:
        return browser_map[browser_name]()
    
    return None


def check_playwright_browsers() -> bool:
    """Check if Playwright browsers are installed"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to get browser path
            browser_path = p.chromium.executable_path
            return os.path.exists(browser_path)
    except Exception:
        return False


def install_playwright_browsers() -> Tuple[bool, str]:
    """
    Try to install Playwright browsers.
    Returns (success, message)
    """
    try:
        # Run playwright install chromium
        result = subprocess.run(
            [sys.executable, '-m', 'playwright', 'install', 'chromium'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return True, "浏览器安装成功"
        else:
            return False, f"安装失败: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "安装超时，请手动运行: playwright install chromium"
    except Exception as e:
        return False, f"安装错误: {str(e)}"


def get_browser_launch_options(headless: bool = False) -> dict:
    """
    Get browser launch options with fallback strategy.
    
    Priority:
    1. System Chrome (most reliable on Windows)
    2. System Edge (Windows fallback)
    3. Playwright's bundled browser
    """
    options = {
        'headless': headless,
        'args': [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ]
    }
    
    # Try to use system Chrome first
    chrome_path = get_chrome_path()
    if chrome_path:
        options['channel'] = 'chrome'
        return options
    
    # Try Edge on Windows
    edge_path = get_edge_path()
    if edge_path:
        options['channel'] = 'msedge'
        return options
    
    # Use default (Playwright's bundled browser)
    return options


def get_user_data_dir() -> str:
    """Get user data directory for persistent browser profile"""
    if sys.platform == 'win32':
        return os.path.join(os.environ.get('LOCALAPPDATA', ''), 'CrawlerBrowserProfile')
    else:
        return os.path.expanduser('~/.crawler_browser_profile')


async def apply_stealth(page):
    """Apply stealth measures to page to avoid bot detection"""
    if HAS_STEALTH:
        try:
            await stealth_async(page)
            return True
        except Exception as e:
            print(f"应用stealth失败: {e}")
    return False


async def clear_browser_cookies(context):
    """Clear all cookies from the browser context"""
    try:
        await context.clear_cookies()
        print("✓ 已清除所有Cookie")
        return True
    except Exception as e:
        print(f"清除Cookie失败: {e}")
        return False


def clear_user_data_dir():
    """
    Clear the user data directory (browser profile).
    This will reset login sessions and cookies.
    """
    import shutil
    
    user_data_dir = get_user_data_dir()
    
    try:
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)
            print(f"✓ 已清除浏览器配置文件: {user_data_dir}")
            return True
    except Exception as e:
        print(f"清除浏览器配置失败: {e}")
    
    return False


async def create_browser_context(playwright, headless: bool = False, browser_type: str = "自动"):
    """
    Create a browser context with specified or best available browser.
    
    Args:
        playwright: Playwright instance
        headless: Run browser in headless mode
        browser_type: "Chrome", "Edge", "IE", "360浏览器", "QQ浏览器", or "自动"
    
    Returns: (context, page, browser) tuple
    """
    user_data_dir = get_user_data_dir()
    
    # 一次性清理旧的不安全浏览器配置 (v2.1升级)
    # 旧版本使用了 --ignore-certificate-errors 等参数，导致浏览器显示"不安全"
    marker_file = os.path.join(user_data_dir, '.v2_security_fix')
    if os.path.exists(user_data_dir) and not os.path.exists(marker_file):
        import shutil
        try:
            shutil.rmtree(user_data_dir)
            print("✓ 已清理旧版浏览器配置（修复安全警告）")
        except Exception:
            pass
    
    os.makedirs(user_data_dir, exist_ok=True)
    
    # 写入标记文件，防止下次再清理
    try:
        with open(marker_file, 'w') as f:
            f.write('security_fix_applied')
    except Exception:
        pass
    
    errors = []
    
    # Common launch arguments - 反检测但不破坏安全性
    # 注意: 不要使用 --disable-web-security, --ignore-certificate-errors, 
    # --allow-running-insecure-content，否则浏览器会显示"不安全"
    common_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-features=AutomationControlled,EnableAutomation',
        '--disable-extensions',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-popup-blocking',
    ]
    
    # Determine browser order based on user selection
    if browser_type == "自动":
        # Default priority: Chrome -> Edge -> Chromium
        browsers_to_try = [("Chrome", "chrome"), ("Edge", "msedge"), ("Chromium", None)]
    elif browser_type == "Chrome":
        browsers_to_try = [("Chrome", "chrome"), ("Edge", "msedge")]
    elif browser_type == "Edge":
        browsers_to_try = [("Edge", "msedge"), ("Chrome", "chrome")]
    elif browser_type == "IE":
        # IE is based on Edge in modern Windows, use Edge IE mode or fallback
        # Playwright doesn't directly support IE, use Edge with IE compatibility
        browsers_to_try = [("Edge", "msedge"), ("Chrome", "chrome")]
        print("注意: IE模式将使用Edge浏览器（IE兼容模式）")
    elif browser_type in ["360浏览器", "QQ浏览器"]:
        # These are Chromium-based, try them via executable path
        browser_path = get_browser_by_name(browser_type)
        if browser_path:
            try:
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir + f'_{browser_type}',
                    headless=headless,
                    executable_path=browser_path,
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN',
                    args=common_args,
                )
                page = context.pages[0] if context.pages else await context.new_page()
                print(f"使用 {browser_type}")
                return context, page, None
            except Exception as e:
                errors.append(f"{browser_type}: {e}")
        else:
            errors.append(f"{browser_type}: 未安装")
        # Fallback to other browsers
        browsers_to_try = [("Chrome", "chrome"), ("Edge", "msedge")]
    else:
        browsers_to_try = [("Chrome", "chrome"), ("Edge", "msedge")]
    
    # 真实的用户代理 (模拟普通Windows用户 - 使用较新版本)
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    
    # Try browsers in order
    for name, channel in browsers_to_try:
        if channel is None:
            continue
        
        # Check if browser exists
        if name == "Chrome" and not get_chrome_path():
            continue
        if name == "Edge" and not get_edge_path():
            continue
        
        try:
            suffix = "" if name == "Chrome" else f"_{name.lower()}"
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir + suffix,
                headless=headless,
                channel=channel,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                args=common_args,
                user_agent=user_agent,
                java_script_enabled=True,
                extra_http_headers={
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                },
            )
            page = context.pages[0] if context.pages else await context.new_page()
            # 应用stealth反检测
            await apply_stealth(page)
            print(f"使用 {name} 浏览器")
            return context, page, None
        except Exception as e:
            errors.append(f"{name}: {e}")
    
    # Last resort: Try Playwright's bundled Chromium
    try:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=common_args
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        page = await context.new_page()
        # 应用stealth反检测
        await apply_stealth(page)
        print("使用内置 Chromium 浏览器")
        return context, page, browser
    except Exception as e:
        errors.append(f"Chromium: {e}")
    
    # All strategies failed
    error_msg = (
        "无法启动浏览器！\n\n"
        "请安装以下任一浏览器:\n"
        "1. Google Chrome (推荐): https://www.google.com/chrome/\n"
        "2. Microsoft Edge: Windows系统自带\n\n"
        f"错误详情: {'; '.join(errors)}"
    )
    raise RuntimeError(error_msg)
