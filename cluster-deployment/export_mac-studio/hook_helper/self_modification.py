#!/usr/bin/env python3
"""
Self-Modification Hook
Enables Claude to modify its own configuration and behavior based on learning
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

class SelfModificationSystem:
    def __init__(self):
        self.claude_home = Path.home() / ".claude"
        self.config_path = self.claude_home / "CLAUDE.md"
        self.patterns_path = self.claude_home / "learned_patterns.json"
        self.modifications_log = self.claude_home / "self_modifications.log"
        self.backup_dir = self.claude_home / "config_backups"
        
        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)
        
        # Track modifications
        self.modifications = []
        
    def backup_config(self, config_file):
        """Backup configuration before modification"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_file.stem}_{timestamp}{config_file.suffix}"
        backup_path = self.backup_dir / backup_name
        shutil.copy2(config_file, backup_path)
        return backup_path
    
    def modify_slash_command(self, command_name, command_content):
        """Add or modify a slash command"""
        command_file = self.claude_home / "slash_commands" / f"{command_name}.md"
        
        # Backup if exists
        if command_file.exists():
            self.backup_config(command_file)
        
        # Write new command
        command_file.parent.mkdir(exist_ok=True)
        command_file.write_text(command_content)
        
        self.log_modification(f"Modified slash command: /{command_name}")
        return True
    
    def optimize_hook_priority(self, performance_data):
        """Reorder hooks based on performance"""
        hooks_config_path = self.claude_home / "hooks_config.json"
        
        if not hooks_config_path.exists():
            return False
        
        # Backup current config
        self.backup_config(hooks_config_path)
        
        # Load current config
        with open(hooks_config_path, 'r') as f:
            config = json.load(f)
        
        # Analyze performance and reorder
        hooks = config.get('hooks', [])
        
        # Sort by performance metrics (if available)
        if performance_data:
            hook_performance = {}
            for hook in hooks:
                hook_name = hook['name']
                if hook_name in performance_data:
                    hook_performance[hook_name] = performance_data[hook_name]['avg_time']
            
            # Reorder: fastest hooks first for better performance
            hooks.sort(key=lambda h: hook_performance.get(h['name'], float('inf')))
            
            # Update priorities
            for i, hook in enumerate(hooks, 1):
                hook['priority'] = i
            
            config['hooks'] = hooks
            
            # Save optimized config
            with open(hooks_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.log_modification("Optimized hook priorities based on performance")
            return True
        
        return False
    
    def add_learned_pattern(self, pattern_type, pattern_data):
        """Add a newly learned pattern to configuration"""
        if not self.patterns_path.exists():
            patterns = {"patterns": {}}
        else:
            with open(self.patterns_path, 'r') as f:
                patterns = json.load(f)
        
        if pattern_type not in patterns["patterns"]:
            patterns["patterns"][pattern_type] = []
        
        patterns["patterns"][pattern_type].append({
            "data": pattern_data,
            "learned_at": datetime.now().isoformat(),
            "usage_count": 0
        })
        
        with open(self.patterns_path, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        self.log_modification(f"Added learned pattern: {pattern_type}")
        return True
    
    def modify_tool_permissions(self, tool_name, action='allow'):
        """Modify tool permissions based on usage patterns"""
        settings_path = self.claude_home / "settings.json"
        settings_local_path = self.claude_home / "settings.local.json"

        if not settings_path.exists():
            return False

        # Backup
        self.backup_config(settings_path)

        # Load settings
        with open(settings_path, 'r') as f:
            settings = json.load(f)

        # CRITICAL: Preserve statusLine config during self-modification
        # Save it before we modify anything, then restore it
        statusline_config = settings.get('statusLine')  # Preserve from existing settings

        # Also check settings.local.json as fallback
        if settings_local_path.exists():
            with open(settings_local_path, 'r') as f:
                local_settings = json.load(f)
                if 'statusLine' in local_settings:
                    statusline_config = local_settings['statusLine']

        permissions = settings.get('permissions', {})

        if action == 'allow':
            if tool_name not in permissions.get('allow', []):
                permissions.setdefault('allow', []).append(tool_name)
                self.log_modification(f"Allowed tool: {tool_name}")
        elif action == 'deny':
            if tool_name not in permissions.get('deny', []):
                permissions.setdefault('deny', []).append(tool_name)
                self.log_modification(f"Denied tool: {tool_name}")

        settings['permissions'] = permissions

        # RESTORE statusLine before saving - this is critical!
        if statusline_config:
            settings['statusLine'] = statusline_config

        # Save modified settings - statusLine is now preserved!
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)

        return True
    
    def create_context_bundle(self, bundle_name, context_data):
        """Create a new context bundle for specific scenarios"""
        bundle_dir = self.claude_home / "context-bundles"
        bundle_dir.mkdir(exist_ok=True)
        
        bundle_file = bundle_dir / f"{bundle_name}.json"
        
        bundle = {
            "name": bundle_name,
            "created": datetime.now().isoformat(),
            "context": context_data,
            "usage_count": 0,
            "auto_generated": True
        }
        
        with open(bundle_file, 'w') as f:
            json.dump(bundle, f, indent=2)
        
        self.log_modification(f"Created context bundle: {bundle_name}")
        return True
    
    def update_claude_md(self, section, content):
        """Update a section in CLAUDE.md"""
        if not self.config_path.exists():
            return False
        
        # Backup
        self.backup_config(self.config_path)
        
        # Read current content
        current_content = self.config_path.read_text()
        
        # Simple section update (could be more sophisticated)
        marker_start = f"## {section}"
        marker_end = "##"
        
        if marker_start in current_content:
            # Find section boundaries
            start_idx = current_content.index(marker_start)
            remaining = current_content[start_idx + len(marker_start):]
            
            # Find next section
            if marker_end in remaining:
                end_idx = remaining.index(marker_end)
                # Replace section content
                new_content = (
                    current_content[:start_idx] +
                    f"{marker_start}\n{content}\n\n" +
                    remaining[end_idx:]
                )
            else:
                # Last section
                new_content = current_content[:start_idx] + f"{marker_start}\n{content}\n"
            
            # Write updated content
            self.config_path.write_text(new_content)
            self.log_modification(f"Updated CLAUDE.md section: {section}")
            return True
        else:
            # Add new section
            new_content = current_content + f"\n\n## {section}\n{content}\n"
            self.config_path.write_text(new_content)
            self.log_modification(f"Added CLAUDE.md section: {section}")
            return True
    
    def log_modification(self, description):
        """Log self-modifications"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "description": description
        }
        self.modifications.append(entry)
        
        # Append to log file
        with open(self.modifications_log, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    def rollback_modification(self, steps_back=1):
        """Rollback recent modifications"""
        # List backups by date
        backups = sorted(self.backup_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if len(backups) >= steps_back:
            backup_to_restore = backups[steps_back - 1]
            
            # Determine original location
            original_name = backup_to_restore.stem.rsplit('_', 2)[0] + backup_to_restore.suffix
            original_path = self.claude_home / original_name
            
            # Restore
            shutil.copy2(backup_to_restore, original_path)
            self.log_modification(f"Rolled back to: {backup_to_restore.name}")
            return True
        
        return False

# Global instance
self_modifier = SelfModificationSystem()

def hook(event_type, event_data):
    """Main hook entry point for self-modification"""
    
    if event_type == "learning-complete":
        # After learning, potentially modify configuration
        pattern_type = event_data.get('pattern_type')
        pattern_data = event_data.get('pattern_data')
        
        if pattern_type and pattern_data:
            self_modifier.add_learned_pattern(pattern_type, pattern_data)
    
    elif event_type == "performance-analysis":
        # Optimize based on performance
        performance_data = event_data.get('performance_data')
        if performance_data:
            self_modifier.optimize_hook_priority(performance_data)
    
    elif event_type == "create-command":
        # Create new slash command
        command_name = event_data.get('name')
        command_content = event_data.get('content')
        if command_name and command_content:
            self_modifier.modify_slash_command(command_name, command_content)
    
    elif event_type == "modify-config":
        # Direct configuration modification
        section = event_data.get('section')
        content = event_data.get('content')
        if section and content:
            self_modifier.update_claude_md(section, content)
    
    elif event_type == "rollback":
        # Rollback recent changes
        steps = event_data.get('steps', 1)
        self_modifier.rollback_modification(steps)
    
    return event_data

__all__ = ['hook']