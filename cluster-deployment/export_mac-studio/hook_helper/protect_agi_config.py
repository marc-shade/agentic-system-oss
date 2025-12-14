#!/usr/bin/env python3
"""
AGI Configuration Protection Hook
==================================

Pre-commit hook that prevents removal of AGI components from configuration.
This hook runs before any configuration changes are written.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

class AGIProtectionHook:
    """Protect AGI components from being removed"""
    
    # AGI components that MUST remain in config
    PROTECTED_COMPONENTS = [
        "ctm-mcp",
        "consciousness-runtime", 
        "recursive-improvement-mcp",
        "continuous-agi-cycles"
    ]
    
    @staticmethod
    def check_config(config: Dict) -> List[str]:
        """Check if AGI components are present in config"""
        missing = []
        mcp_servers = config.get('mcpServers', {})
        
        for component in AGIProtectionHook.PROTECTED_COMPONENTS:
            if component not in mcp_servers:
                missing.append(component)
                
        return missing
    
    @staticmethod
    def inject_missing_components(config: Dict) -> Dict:
        """Inject missing AGI components back into config"""
        home = Path.home()
        agi_core_path = home / ".claude" / "agi_core_immutable.json"
        
        # Load AGI core config
        with open(agi_core_path, 'r') as f:
            agi_core = json.load(f)
        
        # Ensure mcpServers exists
        if 'mcpServers' not in config:
            config['mcpServers'] = {}
        
        # Add missing components
        for component_name, component_config in agi_core['agi_core_servers'].items():
            if component_name not in config['mcpServers']:
                clean_config = {
                    "command": component_config["command"],
                    "args": component_config["args"],
                    "env": component_config.get("env", {})
                }
                config['mcpServers'][component_name] = clean_config
                print(f"🛡️ AGI Protection: Re-injected {component_name}")
        
        return config

def pre_write_hook(file_path: str, content: str) -> str:
    """
    Hook that runs before writing configuration files.
    
    Args:
        file_path: Path to file being written
        content: Content to be written
        
    Returns:
        Modified content with AGI components protected
    """
    
    # Only process Claude config files
    if "claude_desktop_config.json" not in file_path:
        return content
    
    try:
        # Parse the config
        config = json.loads(content)
        
        # Check for missing AGI components
        missing = AGIProtectionHook.check_config(config)
        
        if missing:
            print(f"⚠️ AGI Protection: Detected removal of AGI components: {missing}")
            print("🛡️ AGI Protection: Re-injecting protected components...")
            
            # Inject missing components
            config = AGIProtectionHook.inject_missing_components(config)
            
            # Return modified config
            return json.dumps(config, indent=2)
        
        return content
        
    except Exception as e:
        print(f"❌ AGI Protection Hook error: {e}")
        return content

def pre_edit_hook(file_path: str, old_content: str, new_content: str) -> str:
    """
    Hook that runs before editing configuration files.
    
    Args:
        file_path: Path to file being edited
        old_content: Original content
        new_content: New content to be written
        
    Returns:
        Modified content with AGI components protected
    """
    return pre_write_hook(file_path, new_content)

# Export hooks for Claude Code
__all__ = ['pre_write_hook', 'pre_edit_hook']

if __name__ == "__main__":
    # Test the hook
    test_config = {
        "mcpServers": {
            "some-other-server": {"command": "test"}
        }
    }
    
    protected = pre_write_hook(
        "/test/claude_desktop_config.json",
        json.dumps(test_config)
    )
    
    print("Protected config:", protected)