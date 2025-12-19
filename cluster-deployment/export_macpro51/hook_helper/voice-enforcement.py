#!/usr/bin/env python3
'''Voice Enforcement Hook - Ensures voice is used at key points'''

import json
import subprocess
import sys

# Load voice config
with open('/home/marc/.claude/voice-orchestration-config.json', 'r') as f:
    config = json.load(f)

def enforce_voice(context):
    '''Check if voice should be used based on context'''
    
    # Check for mandatory voice points
    mandatory_points = config['voice_usage_rules']['orchestrator_must_speak']
    
    for point in mandatory_points:
        if point in context.lower():
            # Trigger voice output
            return True
    
    return False

# Hook implementation would go here
# This is a template for the actual hook system
