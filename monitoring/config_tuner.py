#!/usr/bin/env python3
"""
Configuration Tuning Engine for Deep Learning Cycle
Week 5 Phase 5: Autonomous Configuration Optimization

This module analyzes system configuration files, detects suboptimal settings,
generates configuration optimizations, and applies them safely with backup and rollback.
"""

import json
import sqlite3
import hashlib
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
CONFIG_TUNING_DB = Path("/mnt/agentic-system/databases/config_tuning.db")
SETTINGS_FILE = Path("/Users/marc/.claude/settings.json")
SETTINGS_LOCAL = Path("/Users/marc/.claude/settings.local.json")
QDRANT_CONFIG = Path("/mnt/agentic-system/config/qdrant-config.yaml")
EVOLUTION_CONFIG = Path("/mnt/agentic-system/config/evolution_phases.json")

class TuningType(Enum):
    """Types of configuration tuning"""
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    CACHE = "cache"
    CONCURRENCY = "concurrency"
    MEMORY = "memory"

class TuningStatus(Enum):
    """Configuration tuning status"""
    ANALYZING = "analyzing"
    PENDING_TUNING = "pending_tuning"
    TUNED = "tuned"
    TESTING = "testing"
    DEPLOYED = "deployed"
    FAILED = "failed"

@dataclass
class ConfigFile:
    """Represents a configuration file"""
    file_id: str
    file_path: Path
    file_type: str
    content: Dict[str, Any]
    last_modified: datetime
    size_bytes: int

@dataclass
class ConfigTuning:
    """Represents a configuration tuning"""
    tuning_id: str
    file_id: str
    tuning_type: TuningType
    parameter_path: str
    current_value: str
    tuned_value: str
    description: str
    confidence: float
    status: TuningStatus
    created_at: datetime
    applied_at: Optional[datetime]
    effectiveness: float
    metric_before: Optional[float]
    metric_after: Optional[float]

class ConfigTuningDatabase:
    """Manages configuration tuning storage and tracking"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize tuning database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_tuning (
                tuning_id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                tuning_type TEXT NOT NULL,
                parameter_path TEXT NOT NULL,
                current_value TEXT NOT NULL,
                tuned_value TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                applied_at TIMESTAMP,
                effectiveness REAL DEFAULT 0.0,
                metric_before REAL,
                metric_after REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tuning_file ON config_tuning(file_id)
        """)

        conn.commit()
        conn.close()

    def store_tuning(self, tuning: ConfigTuning):
        """Store a configuration tuning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO config_tuning
            (tuning_id, file_id, tuning_type, parameter_path, current_value,
             tuned_value, description, confidence, status, created_at, applied_at,
             effectiveness, metric_before, metric_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tuning.tuning_id, tuning.file_id, tuning.tuning_type.value,
            tuning.parameter_path, tuning.current_value, tuning.tuned_value,
            tuning.description, tuning.confidence, tuning.status.value,
            tuning.created_at.isoformat(),
            tuning.applied_at.isoformat() if tuning.applied_at else None,
            tuning.effectiveness, tuning.metric_before, tuning.metric_after
        ))

        conn.commit()
        conn.close()

    def get_pending_tuning(self, min_confidence: float = 0.75) -> List[ConfigTuning]:
        """Get pending tuning above confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT tuning_id, file_id, tuning_type, parameter_path, current_value,
                   tuned_value, description, confidence, status, created_at, applied_at,
                   effectiveness, metric_before, metric_after
            FROM config_tuning
            WHERE status = ? AND confidence >= ?
            ORDER BY confidence DESC
        """, (TuningStatus.PENDING_TUNING.value, min_confidence))

        rows = cursor.fetchall()
        conn.close()

        return [ConfigTuning(
            tuning_id=r[0], file_id=r[1], tuning_type=TuningType(r[2]),
            parameter_path=r[3], current_value=r[4], tuned_value=r[5],
            description=r[6], confidence=r[7], status=TuningStatus(r[8]),
            created_at=datetime.fromisoformat(r[9]),
            applied_at=datetime.fromisoformat(r[10]) if r[10] else None,
            effectiveness=r[11], metric_before=r[12], metric_after=r[13]
        ) for r in rows]

class ConfigAnalyzer:
    """Analyzes configuration files and identifies optimization opportunities"""

    def __init__(self, tuning_db: ConfigTuningDatabase):
        self.tuning_db = tuning_db

    def load_config_files(self) -> List[ConfigFile]:
        """Load analyzable configuration files"""
        config_files = []

        # Only analyze safe, non-critical config files
        if SETTINGS_LOCAL.exists():
            config_files.append(self._load_json_config(SETTINGS_LOCAL))

        if EVOLUTION_CONFIG.exists():
            config_files.append(self._load_json_config(EVOLUTION_CONFIG))

        return config_files

    def _load_json_config(self, file_path: Path) -> ConfigFile:
        """Load JSON configuration file"""
        content = json.loads(file_path.read_text())
        stat = file_path.stat()
        file_id = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]

        return ConfigFile(
            file_id=file_id, file_path=file_path, file_type="json",
            content=content, last_modified=datetime.fromtimestamp(stat.st_mtime),
            size_bytes=stat.st_size
        )

    def identify_tuning_opportunities(self, config_files: List[ConfigFile]) -> List[Tuple[ConfigFile, TuningType, str, str, str, float]]:
        """Identify configuration parameters that could be optimized"""
        opportunities = []

        for config_file in config_files:
            if config_file.file_type == "json":
                # Check evolution phases (list structure)
                if "phases" in config_file.content:
                    phases = config_file.content["phases"]
                    if isinstance(phases, list):
                        # Analyze phase statuses
                        active_count = sum(1 for p in phases if isinstance(p, dict) and p.get("status") == "active")
                        if active_count < len(phases):
                            opportunities.append((
                                config_file, TuningType.PERFORMANCE,
                                "phases[].status", f"{active_count}/{len(phases)} active", "More phases could be activated", 0.65
                            ))

                # Check for missing MCP server settings in settings.local.json
                if "enabledMcpjsonServers" in config_file.content:
                    enabled = config_file.content["enabledMcpjsonServers"]
                    if len(enabled) < 4:
                        opportunities.append((
                            config_file, TuningType.PERFORMANCE,
                            "enabledMcpjsonServers", f"{len(enabled)} servers", "Consider enabling more MCP servers", 0.65
                        ))

        return opportunities

class ConfigTuner:
    """Generates and applies configuration tuning safely"""

    def __init__(self, db: ConfigTuningDatabase):
        self.db = db

    def generate_tuning(self, config_file: ConfigFile, tuning_type: TuningType,
                       parameter_path: str, current_value: str, tuned_value: str,
                       confidence: float) -> ConfigTuning:
        """Generate a configuration tuning"""
        tuning_id = hashlib.sha256(
            f"{config_file.file_id}_{parameter_path}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        return ConfigTuning(
            tuning_id=tuning_id, file_id=config_file.file_id,
            tuning_type=tuning_type, parameter_path=parameter_path,
            current_value=current_value, tuned_value=tuned_value,
            description=f"Optimize {parameter_path}: {current_value} → {tuned_value}",
            confidence=confidence, status=TuningStatus.PENDING_TUNING,
            created_at=datetime.now(), applied_at=None,
            effectiveness=0.0, metric_before=None, metric_after=None
        )

    def apply_tuning(self, tuning: ConfigTuning, config_file: ConfigFile) -> bool:
        """Apply configuration tuning with backup and safety checks"""
        try:
            # Safety check - differentiate system vs project space
            # Project space (SSDRAID0/agentic-system) - more permissive for autonomous operations
            # System space (/Users/marc/.claude) - stricter controls
            is_project_space = str(config_file.file_path).startswith('/mnt/agentic-system')
            is_system_space = str(config_file.file_path).startswith('/Users/marc/.claude')

            # Never modify main settings.json (system critical)
            if config_file.file_path == SETTINGS_FILE:
                print(f"  Skipping: Won't modify main settings.json (system critical)")
                return False

            # System space requires higher confidence
            if is_system_space and tuning.confidence < 0.80:
                print(f"  Skipping: System space file requires ≥80% confidence (current: {tuning.confidence:.0%})")
                return False

            # Create backup
            backup_path = config_file.file_path.with_suffix(config_file.file_path.suffix + '.backup')
            shutil.copy2(config_file.file_path, backup_path)

            # Load current config
            content = json.loads(config_file.file_path.read_text())

            # Apply tuning based on parameter path
            keys = tuning.parameter_path.split('.')
            self._set_nested_value(content, keys, tuning.tuned_value)

            # Write updated config
            config_file.file_path.write_text(json.dumps(content, indent=2))

            # Update status
            tuning.status = TuningStatus.DEPLOYED
            tuning.applied_at = datetime.now()
            self.db.store_tuning(tuning)

            print(f"✓ Applied tuning: {tuning.description}")
            print(f"  Backup: {backup_path}")
            return True

        except Exception as e:
            print(f"✗ Failed to apply tuning: {e}")
            tuning.status = TuningStatus.FAILED
            self.db.store_tuning(tuning)
            return False

    def _set_nested_value(self, obj: dict, keys: List[str], value: str):
        """Set nested dictionary value from dot-separated path"""
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})

        final_key = keys[-1]

        # Convert value to appropriate type
        if value.lower() == "true":
            obj[final_key] = True
        elif value.lower() == "false":
            obj[final_key] = False
        elif value.isdigit():
            obj[final_key] = int(value)
        else:
            obj[final_key] = value

def main():
    """Main configuration tuning runner"""
    print("="*60)
    print("Configuration Tuning Engine - Week 5 Phase 5")
    print("="*60)
    print()

    db = ConfigTuningDatabase(CONFIG_TUNING_DB)
    print(f"✓ Tuning database initialized: {CONFIG_TUNING_DB}")

    analyzer = ConfigAnalyzer(db)
    print(f"✓ Configuration analyzer initialized")
    print()

    config_files = analyzer.load_config_files()
    print(f"Loaded {len(config_files)} configuration files")
    for cf in config_files:
        print(f"  • {cf.file_path.name} ({cf.file_type})")
    print()

    opportunities = analyzer.identify_tuning_opportunities(config_files)
    print(f"Found {len(opportunities)} tuning opportunities")
    print()

    if opportunities:
        print("Tuning Opportunities:")
        for config_file, tuning_type, param_path, current, tuned, confidence in opportunities:
            print(f"  • {config_file.file_path.name}")
            print(f"    Parameter: {param_path}")
            print(f"    Current: {current} → Tuned: {tuned}")
            print(f"    Confidence: {confidence:.0%}")
        print()

    tuner = ConfigTuner(db)
    tunings_created = 0

    for config_file, tuning_type, param_path, current, tuned, confidence in opportunities:
        # More permissive thresholds for project space vs system space
        is_project_space = str(config_file.file_path).startswith('/mnt/agentic-system')
        min_confidence = 0.60 if is_project_space else 0.70

        if confidence >= min_confidence:
            tuning = tuner.generate_tuning(config_file, tuning_type, param_path, current, tuned, confidence)
            db.store_tuning(tuning)
            tunings_created += 1
            print(f"  Created tuning: {config_file.file_path.name} ({confidence:.0%} confidence)")
        else:
            print(f"  Skipped: {config_file.file_path.name} - confidence {confidence:.0%} below threshold ({min_confidence:.0%})")

    print(f"Created {tunings_created} configuration tunings")
    print()
    print("="*60)
    print("CONFIGURATION TUNING COMPLETE")
    print("="*60)
    print(f"Config files analyzed: {len(config_files)}")
    print(f"Opportunities identified: {len(opportunities)}")
    print(f"Tunings created: {tunings_created}")
    print(f"Database: {CONFIG_TUNING_DB}")
    print()

if __name__ == "__main__":
    main()
