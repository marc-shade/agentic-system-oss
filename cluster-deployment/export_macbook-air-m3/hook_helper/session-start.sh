#!/bin/bash
# Session Start Hook Wrapper
# Calls unified hook system session_start

python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
from hooks.claude_code_hooks import session_start
result = session_start()
"
