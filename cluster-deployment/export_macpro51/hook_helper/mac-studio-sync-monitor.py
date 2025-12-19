#!/usr/bin/env python3
"""
Mac Studio Sync Monitor
Regularly checks Mac Studio for new builds, MCP servers, and configuration updates
"""

import os
import json
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path

# Configuration
MAC_STUDIO_IP = "192.168.1.16"
MASTER_CONFIG_PATH = "/Volumes/marc/.claude"
AGENTIC_SYSTEM_PATH = "/Volumes/FILES/agentic-system"
LOCAL_CLAUDE_PATH = "/home/marc/.claude"
STATE_FILE = f"{LOCAL_CLAUDE_PATH}/sync-state.json"

def get_file_hash(filepath):
    """Calculate hash of file for change detection"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_directory_state(path):
    """Get state of all files in directory"""
    state = {}
    if not os.path.exists(path):
        return state

    for root, dirs, files in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            # Skip broken symlinks
            if not os.path.exists(filepath):
                continue
            rel_path = os.path.relpath(filepath, path)
            state[rel_path] = {
                'hash': get_file_hash(filepath),
                'mtime': os.path.getmtime(filepath)
            }
    return state

def load_sync_state():
    """Load previous sync state"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sync_state(state):
    """Save current sync state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def check_for_changes():
    """Check for new builds and updates on Mac Studio"""
    changes = {
        'timestamp': datetime.now().isoformat(),
        'new_items': [],
        'modified_items': [],
        'new_mcp_servers': []
    }

    # Load previous state
    prev_state = load_sync_state()

    # Check master config directory
    if os.path.exists(MASTER_CONFIG_PATH):
        current_config_state = get_directory_state(MASTER_CONFIG_PATH)
        prev_config_state = prev_state.get('master_config', {})

        for path, info in current_config_state.items():
            if path not in prev_config_state:
                changes['new_items'].append(f"Config: {path}")
            elif info['hash'] != prev_config_state.get(path, {}).get('hash'):
                changes['modified_items'].append(f"Config: {path}")

    # Check agentic system directory
    if os.path.exists(AGENTIC_SYSTEM_PATH):
        current_agentic_state = get_directory_state(AGENTIC_SYSTEM_PATH)
        prev_agentic_state = prev_state.get('agentic_system', {})

        for path, info in current_agentic_state.items():
            if path not in prev_agentic_state:
                changes['new_items'].append(f"Agentic: {path}")
            elif info['hash'] != prev_agentic_state.get(path, {}).get('hash'):
                changes['modified_items'].append(f"Agentic: {path}")

    # Check for new MCP servers
    mcp_dir = f"{MASTER_CONFIG_PATH}/../Documents/Cline/MCP"
    if os.path.exists(mcp_dir):
        for item in os.listdir(mcp_dir):
            item_path = os.path.join(mcp_dir, item)
            if os.path.isdir(item_path) and item.endswith('-mcp'):
                if item not in prev_state.get('known_mcp_servers', []):
                    changes['new_mcp_servers'].append(item)

    # Save current state
    new_state = {
        'master_config': current_config_state if os.path.exists(MASTER_CONFIG_PATH) else {},
        'agentic_system': current_agentic_state if os.path.exists(AGENTIC_SYSTEM_PATH) else {},
        'known_mcp_servers': prev_state.get('known_mcp_servers', []) + changes['new_mcp_servers'],
        'last_check': changes['timestamp']
    }
    save_sync_state(new_state)

    return changes

def notify_changes(changes):
    """Notify user of changes found"""
    if not any([changes['new_items'], changes['modified_items'], changes['new_mcp_servers']]):
        return

    # Create notification file
    report_file = f"{LOCAL_CLAUDE_PATH}/sync-updates.md"
    with open(report_file, 'w') as f:
        f.write(f"# Mac Studio Updates - {changes['timestamp']}\n\n")

        if changes['new_mcp_servers']:
            f.write("## New MCP Servers\n")
            for server in changes['new_mcp_servers']:
                f.write(f"- {server}\n")
            f.write("\n")

        if changes['new_items']:
            f.write("## New Files\n")
            for item in changes['new_items']:
                f.write(f"- {item}\n")
            f.write("\n")

        if changes['modified_items']:
            f.write("## Modified Files\n")
            for item in changes['modified_items']:
                f.write(f"- {item}\n")
            f.write("\n")

    # Voice notification
    summary = []
    if changes['new_mcp_servers']:
        summary.append(f"{len(changes['new_mcp_servers'])} new MCP servers")
    if changes['new_items']:
        summary.append(f"{len(changes['new_items'])} new files")
    if changes['modified_items']:
        summary.append(f"{len(changes['modified_items'])} modified files")

    message = f"Mac Studio sync found: {', '.join(summary)}"
    subprocess.run(['say', '-v', 'Moira', '-r', '180', message], check=False)

    print(f"\nSync report written to: {report_file}")
    print(message)

if __name__ == "__main__":
    print(f"Checking Mac Studio ({MAC_STUDIO_IP}) for updates...")
    changes = check_for_changes()
    notify_changes(changes)

    if not any([changes['new_items'], changes['modified_items'], changes['new_mcp_servers']]):
        print("No changes detected")
