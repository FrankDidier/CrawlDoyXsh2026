#!/usr/bin/env python3
"""
Quick run script for development.
Run this file to start the ShareLink Extractor application.
"""

import sys
import os

# Ensure the project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.main import main

if __name__ == "__main__":
    main()
