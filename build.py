#!/usr/bin/env python3
"""
Build script for creating Windows executable using PyInstaller.

Usage:
    python build.py           # Build with console window (for debugging)
    python build.py --release # Build without console window (for production)

Requirements:
    pip install pyinstaller
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path


def clean_build_dirs():
    """Remove previous build artifacts"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}/...")
            shutil.rmtree(dir_name)
    
    # Clean .spec files
    for spec_file in Path('.').glob('*.spec'):
        print(f"Removing {spec_file}...")
        spec_file.unlink()
    
    # Clean __pycache__ in subdirectories
    for pycache in Path('.').rglob('__pycache__'):
        print(f"Cleaning {pycache}...")
        shutil.rmtree(pycache)


def build_executable(release_mode=False):
    """Build the Windows executable"""
    
    print("=" * 50)
    print("ShareLink Extractor - Build Script")
    print("=" * 50)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller is not installed!")
        print("Please install it: pip install pyinstaller")
        sys.exit(1)
    
    # Clean previous builds
    print("\n[1/3] Cleaning previous builds...")
    clean_build_dirs()
    
    # Build command
    print("\n[2/3] Building executable...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=ShareLinkExtractor',
        '--onefile',  # Single executable file
        '--add-data=src;src',  # Include source files
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtGui',
        '--hidden-import=openpyxl',
        '--collect-all=PySide6',
        '--noconfirm',  # Replace output without confirmation
    ]
    
    # Add icon if exists
    icon_path = Path('assets/icon.ico')
    if icon_path.exists():
        cmd.append(f'--icon={icon_path}')
    
    # Release mode: no console window
    if release_mode:
        cmd.append('--windowed')
        print("Building in RELEASE mode (no console window)")
    else:
        cmd.append('--console')
        print("Building in DEBUG mode (with console window)")
    
    # Entry point
    cmd.append('run.py')
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("\nERROR: Build failed!")
        sys.exit(1)
    
    # Post-build
    print("\n[3/3] Post-build tasks...")
    
    exe_path = Path('dist/ShareLinkExtractor.exe')
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n{'=' * 50}")
        print("BUILD SUCCESSFUL!")
        print(f"{'=' * 50}")
        print(f"Executable: {exe_path.absolute()}")
        print(f"Size: {size_mb:.2f} MB")
        print(f"\nMode: {'Release' if release_mode else 'Debug'}")
        print("\nYou can now distribute the .exe file to Windows users.")
    else:
        print("\nWARNING: Executable not found at expected path")


def main():
    parser = argparse.ArgumentParser(description='Build ShareLink Extractor executable')
    parser.add_argument('--release', action='store_true', 
                       help='Build in release mode (no console window)')
    parser.add_argument('--clean', action='store_true',
                       help='Only clean build directories')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_build_dirs()
        print("Clean complete!")
    else:
        build_executable(release_mode=args.release)


if __name__ == '__main__':
    main()
