import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from loguru import logger
from cryptography.fernet import Fernet

class ConfigurationManager:
    """
    Manages system-wide configuration and settings for the Software Planning MCP.
    Handles configuration loading, validation, and updates across components.
    """
    
    def __init__(self):
        self.config_dir = Path(os.path.expanduser("~/.mcp/config"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.config_dir / "settings.json"
        self.defaults_file = self.config_dir / "defaults.json"
        self.overrides_file = self.config_dir / "overrides.json"
        
        # Initialize configuration files
        self._initialize_config_files()
        
        # Load configurations
        self.settings = self._load_settings()
        self.defaults = self._load_defaults()
        self.overrides = self._load_overrides()
        
        # Configuration schema
        self.schema = {
            "system": {
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "data_dir": {"type": "string"},
                "backup_enabled": True,
                "backup_interval": {"type": "integer", "minimum": 1},
                "max_backup_size": {"type": "integer", "minimum": 1}
            },
            "security": {
                "session_timeout": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
                "data_dir": {"type": "string"},
                "backup_enabled": True,
                "backup_interval": {"type": "integer", "minimum": 1},
                "max_backup_size": {"type": "integer", "minimum": 1}
            },
            "networking": {
                "host": "localhost",
                "port": 8080,
                "ssl_enabled": False,
                "max_connections": 100
            },
            "monitoring": {
                "metrics_enabled": True,
                "metrics_interval": 60,
                "alert_threshold": 80
            },
            "development": {
                "debug_mode": False,
                "auto_reload": False,
                "test_mode": False
            }
        }
        
        # Configuration watchers
        self.watchers: Dict[str, List[callable]] = {}
        
        # Start file watcher
        #self.watcher_task = asyncio.create_task(self._watch_config_files())
        
        # Encryption key and cipher
        self._encryption_key = Fernet.generate_key()
        self._cipher = Fernet(self._encryption_key)

    def _initialize_config_files(self):
        """Initialize configuration files if they don't exist."""
        if not self.settings_file.exists():
            with open(self.settings_file, "w") as f:
                json.dump({}, f)
        if not self.defaults_file.exists():
            with open(self.defaults_file, "w") as f:
                json.dump({}, f)
        if not self.overrides_file.exists():
            with open(self.overrides_file, "w") as f:
                json.dump({}, f)

    async def set(
        self,
        key: str,
        value: Any,
        persist: bool = True
    ) -> bool:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (dot notation)
            value: Value to set
            persist: Whether to persist the change
        
        Returns:
            True if successful
        """
        #self._validate_key(key)
        # Validate schema
        schema = self._get_schema_for_key(key)
        if schema and not self._validate_value(value, schema):
            #raise ValueError(f"Invalid value for {key}")
            pass
        
        if key.endswith('.number'):
            #try:
            #    value = int(value)
            #except ValueError:
            #    raise ValueError('Value must be a number')
            #except ValueError:
            pass
        
        if key.startswith('security.'):
            value = self._cipher.encrypt(str(value).encode()).decode()
        
        # Update settings
        parts = key.split(".")
        current = self.settings
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
        
        if persist:
            self._save_settings()
        
        # Notify watchers
        #await self._notify_watchers(key)
        
        return True
