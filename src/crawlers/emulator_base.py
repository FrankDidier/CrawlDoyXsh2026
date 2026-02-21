"""
Android Emulator Automation Base Class
Uses ADB (Android Debug Bridge) to control emulator and extract APP share links.

Requirements:
- Android emulator (LDPlayer, NoxPlayer, or BlueStacks)
- ADB installed and in PATH
- Douyin/Kuaishou APP installed in emulator
"""

import subprocess
import time
import re
import os
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class EmulatorType(Enum):
    """Supported Android emulators"""
    LDPLAYER = "ldplayer"      # 雷电模拟器
    MUMU = "mumu"              # MuMu模拟器 (推荐，最快)
    NOXPLAYER = "noxplayer"    # 夜神模拟器
    BLUESTACKS = "bluestacks"  # 蓝叠模拟器
    GENERIC = "generic"        # 通用ADB


@dataclass
class EmulatorConfig:
    """Emulator configuration"""
    emulator_type: EmulatorType = EmulatorType.LDPLAYER
    adb_path: str = "adb"  # Use system ADB by default
    device_id: Optional[str] = None  # e.g., "emulator-5554" or "127.0.0.1:5555"
    
    # LDPlayer specific (雷电模拟器)
    ldplayer_path: str = r"C:\LDPlayer\LDPlayer9"
    ldplayer_adb_port: int = 5555
    
    # MuMu specific (MuMu模拟器 - 推荐，最快)
    mumu_path: str = r"C:\Program Files\Netease\MuMu Player 12"
    mumu_adb_port: int = 16384  # MuMu default ADB port
    mumu_adb_ports: tuple = (16384, 7555, 16416, 7556)  # Try multiple ports
    
    # NoxPlayer specific (夜神模拟器)
    noxplayer_path: str = r"C:\Program Files\Nox\bin"
    noxplayer_adb_port: int = 62001


class ADBController:
    """
    Control Android emulator via ADB commands.
    """
    
    def __init__(self, config: EmulatorConfig = None):
        self.config = config or EmulatorConfig()
        self._connected = False
        self._device_id = None
    
    def _run_adb(self, *args, timeout: int = 30) -> Tuple[bool, str]:
        """Run ADB command and return (success, output)"""
        cmd = [self.config.adb_path]
        if self._device_id:
            cmd.extend(['-s', self._device_id])
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                encoding='utf-8',
                errors='ignore'
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def connect(self) -> bool:
        """Connect to emulator - tries multiple ports for MuMu"""
        ports_to_try = []
        
        # Determine which ports to try based on emulator type
        if self.config.emulator_type == EmulatorType.LDPLAYER:
            ports_to_try = [self.config.ldplayer_adb_port, 5555, 5556, 5554]
        elif self.config.emulator_type == EmulatorType.MUMU:
            # MuMu Player 12 can use different ports
            ports_to_try = list(self.config.mumu_adb_ports) if hasattr(self.config, 'mumu_adb_ports') else [16384, 7555, 16416, 7556]
        elif self.config.emulator_type == EmulatorType.NOXPLAYER:
            ports_to_try = [self.config.noxplayer_adb_port, 62001, 62025]
        else:
            ports_to_try = [5555]  # Generic
        
        # Try each port
        for port in ports_to_try:
            self._device_id = f"127.0.0.1:{port}"
            
            # Try to connect via ADB
            success, output = self._run_adb('connect', self._device_id)
            
            # Check if connected
            success, output = self._run_adb('devices')
            if success:
                for line in output.split('\n'):
                    if self._device_id in line and '\tdevice' in line:
                        print(f"Connected to emulator on port {port}")
                        self._connected = True
                        return True
        
        # If specific port didn't work, try to find any connected device
        success, output = self._run_adb('devices')
        if success:
            lines = output.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if '\tdevice' in line:
                    self._device_id = line.split('\t')[0]
                    print(f"Found device: {self._device_id}")
                    self._connected = True
                    return True
        
        print(f"Failed to connect. ADB devices output: {output}")
        return False
    
    def disconnect(self):
        """Disconnect from emulator"""
        if self._device_id and ':' in self._device_id:
            self._run_adb('disconnect', self._device_id)
        self._connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to emulator"""
        if not self._connected:
            return False
        success, output = self._run_adb('get-state')
        return success and 'device' in output
    
    def tap(self, x: int, y: int):
        """Tap on screen at coordinates"""
        self._run_adb('shell', 'input', 'tap', str(x), str(y))
        time.sleep(0.3)
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Swipe from (x1,y1) to (x2,y2)"""
        self._run_adb('shell', 'input', 'swipe', 
                      str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        time.sleep(0.5)
    
    def swipe_up(self, distance: int = 500):
        """Swipe up to scroll down"""
        # Screen center swipe up
        self.swipe(540, 1200, 540, 1200 - distance, 200)
    
    def swipe_down(self, distance: int = 500):
        """Swipe down to scroll up"""
        self.swipe(540, 600, 540, 600 + distance, 200)
    
    def press_back(self):
        """Press back button"""
        self._run_adb('shell', 'input', 'keyevent', '4')
        time.sleep(0.3)
    
    def press_home(self):
        """Press home button"""
        self._run_adb('shell', 'input', 'keyevent', '3')
        time.sleep(0.5)
    
    def input_text(self, text: str):
        """Input text (for search etc.)"""
        # Escape special characters
        escaped = text.replace(' ', '%s').replace('&', '\\&')
        self._run_adb('shell', 'input', 'text', escaped)
        time.sleep(0.3)
    
    def get_clipboard(self) -> str:
        """Get clipboard content (requires Android 10+)"""
        # This may not work on all emulators
        success, output = self._run_adb('shell', 'cmd', 'clipboard', 'get')
        if success:
            return output
        return ""
    
    def screenshot(self, local_path: str) -> bool:
        """Take screenshot and save to local path"""
        remote_path = '/sdcard/screenshot.png'
        
        # Capture screenshot
        success, _ = self._run_adb('shell', 'screencap', '-p', remote_path)
        if not success:
            return False
        
        # Pull to local
        success, _ = self._run_adb('pull', remote_path, local_path)
        
        # Clean up
        self._run_adb('shell', 'rm', remote_path)
        
        return success
    
    def get_current_activity(self) -> str:
        """Get current foreground activity"""
        success, output = self._run_adb('shell', 'dumpsys', 'window', 'windows')
        if success:
            match = re.search(r'mCurrentFocus=.*?([a-zA-Z0-9_.]+/[a-zA-Z0-9_.]+)', output)
            if match:
                return match.group(1)
        return ""
    
    def start_app(self, package: str, activity: str = None):
        """Start an app by package name"""
        if activity:
            self._run_adb('shell', 'am', 'start', '-n', f'{package}/{activity}')
        else:
            # Use monkey to start app
            self._run_adb('shell', 'monkey', '-p', package, '-c', 
                         'android.intent.category.LAUNCHER', '1')
        time.sleep(2)
    
    def stop_app(self, package: str):
        """Force stop an app"""
        self._run_adb('shell', 'am', 'force-stop', package)
        time.sleep(0.5)
    
    def is_app_installed(self, package: str) -> bool:
        """Check if app is installed"""
        success, output = self._run_adb('shell', 'pm', 'list', 'packages', package)
        return success and package in output
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen resolution"""
        success, output = self._run_adb('shell', 'wm', 'size')
        if success:
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1080, 1920  # Default


# App package names
DOUYIN_PACKAGE = "com.ss.android.ugc.aweme"
KUAISHOU_PACKAGE = "com.smile.gifmaker"


def check_adb_installed() -> bool:
    """Check if ADB is installed and accessible"""
    # First try system ADB
    try:
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try to find emulator-specific ADB
    adb_path = find_any_adb()
    if adb_path:
        return True
    
    return False


def find_any_adb() -> Optional[str]:
    """Find any available ADB executable by searching all drives"""
    # Search all available drives on Windows
    drives = []
    if os.name == 'nt':  # Windows
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(letter)
    else:
        drives = ['']  # Unix-like systems don't have drive letters
    
    # Common relative paths for emulators
    relative_paths = [
        # MuMu Player 12 (multiple possible locations)
        r"MuMuPlayer\shell\adb.exe",  # Client's path: D:\MuMuPlayer
        r"MuMuPlayer\vms\MuMuPlayer-12.0-base\adb.exe",
        r"MuMuPlayer-12.0\shell\adb.exe",
        r"Program Files\Netease\MuMu Player 12\shell\adb.exe",
        r"Netease\MuMu Player 12\shell\adb.exe",
        r"MuMu Player 12\shell\adb.exe",
        r"Program Files (x86)\Netease\MuMu Player 12\shell\adb.exe",
        # MuMu older versions
        r"MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
        r"Program Files\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
        r"Netease\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
        # LDPlayer (雷电)
        r"LDPlayer\LDPlayer9\adb.exe",
        r"LDPlayer9\adb.exe",
        r"leidian\LDPlayer9\adb.exe",
        r"LDPlayer\LDPlayer4.0\adb.exe",
        r"Program Files\LDPlayer\LDPlayer9\adb.exe",
        # NoxPlayer (夜神)
        r"Program Files\Nox\bin\adb.exe",
        r"Program Files (x86)\Nox\bin\nox_adb.exe",
        r"Nox\bin\adb.exe",
        # BlueStacks
        r"Program Files\BlueStacks_nxt\HD-Adb.exe",
    ]
    
    # Search each drive for each path
    for drive in drives:
        for rel_path in relative_paths:
            if drive:
                full_path = f"{drive}:\\{rel_path}"
            else:
                full_path = f"/{rel_path}"
            
            if os.path.exists(full_path):
                return full_path
    
    # Also try Android SDK paths
    sdk_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
    ]
    for path in sdk_paths:
        if os.path.exists(path):
            return path
    
    return None


def get_emulator_adb_path(emulator_type: EmulatorType) -> Optional[str]:
    """Get ADB path for specific emulator - searches all drives"""
    
    # Get all available drives on Windows
    drives = ['C', 'D', 'E', 'F']  # Common drives
    if os.name == 'nt':
        import string
        drives = [letter for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]
    
    # Relative paths for each emulator type (without drive letter)
    relative_paths = {
        EmulatorType.LDPLAYER: [
            r"LDPlayer\LDPlayer9\adb.exe",
            r"LDPlayer\LDPlayer4.0\adb.exe",
            r"leidian\LDPlayer9\adb.exe",
            r"leidian\LDPlayer4.0\adb.exe",
            r"Program Files\LDPlayer\LDPlayer9\adb.exe",
            r"Program Files (x86)\LDPlayer\LDPlayer9\adb.exe",
        ],
        EmulatorType.MUMU: [
            # MuMu Player 12 paths
            r"MuMuPlayer\shell\adb.exe",  # D:\MuMuPlayer\shell\adb.exe
            r"MuMuPlayer\vms\MuMuPlayer-12.0-base\adb.exe",
            r"MuMu Player 12\shell\adb.exe",
            r"Netease\MuMu Player 12\shell\adb.exe",
            r"Program Files\Netease\MuMu Player 12\shell\adb.exe",
            r"Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
            r"Program Files (x86)\Netease\MuMu Player 12\shell\adb.exe",
            # Older MuMu paths
            r"MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
            r"Program Files\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
            r"Program Files (x86)\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
            r"Netease\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
        ],
        EmulatorType.NOXPLAYER: [
            r"Nox\bin\adb.exe",
            r"Nox\bin\nox_adb.exe",
            r"Program Files\Nox\bin\adb.exe",
            r"Program Files (x86)\Nox\bin\nox_adb.exe",
        ],
        EmulatorType.BLUESTACKS: [
            r"Program Files\BlueStacks_nxt\HD-Adb.exe",
            r"Program Files (x86)\BlueStacks_nxt\HD-Adb.exe",
            r"BlueStacks_nxt\HD-Adb.exe",
        ],
    }
    
    # Search all drives for each path
    for drive in drives:
        for rel_path in relative_paths.get(emulator_type, []):
            full_path = f"{drive}:\\{rel_path}"
            if os.path.exists(full_path):
                print(f"Found ADB at: {full_path}")
                return full_path
    
    # Fallback: use find_any_adb
    return find_any_adb()


def detect_running_emulator() -> Optional[EmulatorType]:
    """
    Auto-detect which emulator is currently running.
    Returns the EmulatorType if found, None otherwise.
    """
    # Check common ADB ports (different emulator versions use different ports)
    port_map = {
        # LDPlayer (雷电)
        5555: EmulatorType.LDPLAYER,
        5556: EmulatorType.LDPLAYER,
        5554: EmulatorType.LDPLAYER,
        # MuMu Player 12 (common ports)
        16384: EmulatorType.MUMU,
        16416: EmulatorType.MUMU,
        7555: EmulatorType.MUMU,  # MuMu 12 alternate
        7556: EmulatorType.MUMU,
        # NoxPlayer (夜神)
        62001: EmulatorType.NOXPLAYER,
        62025: EmulatorType.NOXPLAYER,
        62026: EmulatorType.NOXPLAYER,
        # BlueStacks
        5565: EmulatorType.BLUESTACKS,
        5575: EmulatorType.BLUESTACKS,
    }
    
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        output = result.stdout
        
        for line in output.split('\n'):
            if '\tdevice' in line:
                device = line.split('\t')[0]
                if ':' in device:
                    port = int(device.split(':')[1])
                    if port in port_map:
                        return port_map[port]
        
        # If device found but port not recognized, return generic
        if 'device' in output:
            return EmulatorType.GENERIC
            
    except Exception:
        pass
    
    return None
