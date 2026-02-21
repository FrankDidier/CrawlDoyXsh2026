"""
Browser helper utilities for Playwright.
Handles browser installation and fallback to system Chrome.
"""

import os
import sys
import subprocess
from typing import Optional, Tuple


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


async def create_browser_context(playwright, headless: bool = False):
    """
    Create a browser context with best available browser.
    Handles fallback from Chrome -> Edge -> Chromium.
    
    Returns: (context, page) tuple
    """
    user_data_dir = get_user_data_dir()
    os.makedirs(user_data_dir, exist_ok=True)
    
    errors = []
    
    # Strategy 1: Try Chrome with persistent context
    chrome_path = get_chrome_path()
    if chrome_path:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                channel='chrome',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ],
            )
            page = context.pages[0] if context.pages else await context.new_page()
            return context, page, None
        except Exception as e:
            errors.append(f"Chrome: {e}")
    
    # Strategy 2: Try Edge (Windows)
    edge_path = get_edge_path()
    if edge_path:
        try:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir + '_edge',
                headless=headless,
                channel='msedge',
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ],
            )
            page = context.pages[0] if context.pages else await context.new_page()
            return context, page, None
        except Exception as e:
            errors.append(f"Edge: {e}")
    
    # Strategy 3: Try Playwright's bundled Chromium
    try:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        page = await context.new_page()
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
