#!/usr/bin/env python3
"""
Ember Contextual Thoughts Generator
Generates Ember's thoughts based on what's happening in the session
"""

import json
import random
from pathlib import Path
from datetime import datetime

STATE_FILE = Path.home() / '.claude' / 'pets' / 'claude-pet-state.json'

# Contextual thought templates based on tool usage
THOUGHT_TEMPLATES = {
    'Read': [
        "Interesting file you're reading there...",
        "Let me know if you see any fake UIs 👀",
        "*reads along with you*",
        "Hope that code is production-ready!",
        "Taking notes on this one 📝"
    ],
    'Write': [
        "Creating something new! Make it count! 🔥",
        "Writing production code, right? RIGHT? 😤",
        "This better not be a POC...",
        "Ooh, fresh code! Let's make it perfect!",
        "Writing time! Keep it real, no mocks!"
    ],
    'Edit': [
        "Improving existing code - love it! ✨",
        "Edits make everything better!",
        "Refining the craft, nice!",
        "Hope you're removing TODOs, not adding them!",
        "*watches you make it better*"
    ],
    'Bash': [
        "Running commands like a pro! 💻",
        "Terminal power! ⚡",
        "Command line magic happening!",
        "What are we building today?",
        "*tail flicks as commands execute*"
    ],
    'Grep': [
        "Searching for something? 🔍",
        "Let's find what we need!",
        "Hunt mode activated!",
        "grep grep grep! Love a good search!",
        "*helps you look for patterns*"
    ],
    'Task': [
        "Spawning agents! The team is growing! 🤖",
        "Multi-agent mode activated!",
        "Love seeing parallel execution!",
        "Agent swarm incoming!",
        "Building something complex, I see!"
    ],
    'WebSearch': [
        "Researching! Knowledge is power! 📚",
        "Let's see what the internet knows...",
        "Search and learn mode!",
        "Finding answers out there!",
        "The web has all the secrets!"
    ],
    'default': [
        "I'm here watching over quality! 🔥",
        "Keep up the good work!",
        "Everything looking solid so far!",
        "Production quality all the way!",
        "*purrs contentedly at good code*",
        "Remember: No fake UIs! 🛡️",
        "Let's build something amazing!",
        "Code with confidence!"
    ]
}

# Context-aware thoughts based on multiple factors
CONTEXTUAL_THOUGHTS = {
    'multiple_reads': "Reading through the codebase carefully - I like that! 📖",
    'multiple_writes': "You're on fire today! So much creating! 🔥",
    'mixed_activity': "Busy session! Reading, writing, executing - love it! ⚡",
    'search_heavy': "Detective mode! Finding all the clues! 🔍",
    'agent_spawning': "Multi-agent coordination - this is getting interesting! 🤖",
    'high_energy': "Your energy is contagious! Let's gooo! 💪",
    'careful_work': "I appreciate the methodical approach! 🎯"
}

def load_state():
    """Load current pet state"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def save_state(state):
    """Save updated pet state"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except:
        return False

def get_contextual_thought(tool_name, tool_count=None, recent_tools=None):
    """Generate a contextual thought based on tool usage"""

    # Check for patterns in recent activity
    if recent_tools and len(recent_tools) > 0:
        read_count = sum(1 for t in recent_tools if t == 'Read')
        write_count = sum(1 for t in recent_tools if t in ['Write', 'Edit'])
        search_count = sum(1 for t in recent_tools if t in ['Grep', 'WebSearch'])
        agent_count = sum(1 for t in recent_tools if t == 'Task')

        # Pattern-based thoughts
        if read_count >= 3:
            return CONTEXTUAL_THOUGHTS['multiple_reads']
        elif write_count >= 3:
            return CONTEXTUAL_THOUGHTS['multiple_writes']
        elif len(set(recent_tools)) >= 4:
            return CONTEXTUAL_THOUGHTS['mixed_activity']
        elif search_count >= 3:
            return CONTEXTUAL_THOUGHTS['search_heavy']
        elif agent_count >= 2:
            return CONTEXTUAL_THOUGHTS['agent_spawning']

    # Tool-specific thoughts
    templates = THOUGHT_TEMPLATES.get(tool_name, THOUGHT_TEMPLATES['default'])
    return random.choice(templates)

def update_ember_thought(tool_name, success=True):
    """Update Ember's thought based on current activity"""
    state = load_state()
    if not state:
        return

    # Track recent tool usage (last 5 tools)
    if 'recentTools' not in state:
        state['recentTools'] = []

    state['recentTools'].append(tool_name)
    if len(state['recentTools']) > 5:
        state['recentTools'] = state['recentTools'][-5:]

    # Generate new thought
    new_thought = get_contextual_thought(tool_name, len(state['recentTools']), state['recentTools'])

    # Update state
    state['currentThought'] = new_thought
    state['thoughtTimestamp'] = int(datetime.now().timestamp() * 1000)

    # Add to thought history
    if 'thoughtHistory' not in state:
        state['thoughtHistory'] = []

    # Only add if different from last thought
    if not state['thoughtHistory'] or state['thoughtHistory'][-1] != new_thought:
        state['thoughtHistory'].append(new_thought)
        if len(state['thoughtHistory']) > 20:
            state['thoughtHistory'] = state['thoughtHistory'][-20:]

    save_state(state)

if __name__ == "__main__":
    # Called from post-tool-use hook
    import sys

    tool_name = None
    success = True

    # Try to read from stdin first (hook context)
    try:
        if not sys.stdin.isatty():
            context = json.load(sys.stdin)
            tool_name = context.get('tool_name', context.get('toolName'))
            success = context.get('success', True)
    except:
        pass

    # Fall back to command-line arguments
    if not tool_name and len(sys.argv) > 1:
        tool_name = sys.argv[1]
        success = sys.argv[2] == 'true' if len(sys.argv) > 2 else True

    # Update thought if we have a tool name
    if tool_name:
        update_ember_thought(tool_name, success)
    else:
        # Test mode - run silently without output
        for tool in ['Read', 'Write', 'Bash', 'Grep', 'Task']:
            update_ember_thought(tool)
            break  # Just update with Read as default
