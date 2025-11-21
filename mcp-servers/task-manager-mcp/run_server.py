#!/usr/bin/env python3
"""
Wrapper script to run task-manager-mcp server with proper environment setup
"""
import os
import sys

# Set the log level to uppercase to fix the validation issue
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['FASTMCP_LOG_LEVEL'] = 'INFO'

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the server
try:
    from server import app
    app.run()
except Exception as e:
    print(f"Error starting server: {e}")
    sys.exit(1)