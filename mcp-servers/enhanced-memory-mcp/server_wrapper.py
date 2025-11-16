#!/usr/bin/env python3
"""
Wrapper for enhanced-memory-mcp server to ensure proper stdio handling
"""
import sys
import os

# Ensure unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
sys.stdout = sys.stdout.reconfigure(line_buffering=True)
sys.stderr = sys.stderr.reconfigure(line_buffering=True)

# Import and run the server
from server import main

if __name__ == "__main__":
    main()