#!/bin/bash
# Session End Hook Wrapper
# Calls unified hook system session_end

python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
from hooks.claude_code_hooks import session_end
result = session_end()
"
