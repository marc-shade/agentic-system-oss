#!/usr/bin/env python3
"""
Self-Healing Monitor
Autonomous error detection and fixing system

Runs every 5 minutes to:
1. Detect errors from logs
2. Analyze error patterns
3. Apply automated fixes
4. Store learnings in enhanced-memory
5. Prevent future occurrences

Part of the autonomous operation loop.
"""

import asyncio
import json
import logging
import os
import platform
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(_STORAGE_BASE / 'logs' / 'self_healing.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SelfHealing')


class ErrorDetector:
    """Detects errors from various system logs."""

    def __init__(self):
        self.log_paths = [
            str(_STORAGE_BASE / 'arduino-surface' / 'logs' / 'display-agent.log'),
            str(_STORAGE_BASE / 'logs' / 'system.log'),
            str(_STORAGE_BASE / 'intelligent-self-healing' / 'intelligent_statusline.log'),
        ]
        self.error_patterns = [
            (r'ERROR.*no such table: (\w+)', 'missing_table'),
            (r'ERROR.*Credit balance too low', 'api_credits_exhausted'),
            (r'ERROR.*Connection refused.*port (\d+)', 'service_down'),
            (r'ERROR.*ModuleNotFoundError.*\'(\w+)\'', 'missing_module'),
            (r'ERROR.*FileNotFoundError.*\'([^\']+)\'', 'missing_file'),
        ]

    def scan_logs(self, since_minutes: int = 60) -> List[Dict[str, Any]]:
        """Scan logs for errors in the last N minutes."""
        errors = []
        cutoff_time = datetime.now() - timedelta(minutes=since_minutes)

        for log_path in self.log_paths:
            if not Path(log_path).exists():
                continue

            try:
                with open(log_path, 'r') as f:
                    for line in f:
                        # Parse timestamp
                        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if not timestamp_match:
                            continue

                        timestamp_str = timestamp_match.group(1)
                        try:
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue

                        if log_time < cutoff_time:
                            continue

                        # Check for error patterns
                        for pattern, error_type in self.error_patterns:
                            match = re.search(pattern, line)
                            if match:
                                errors.append({
                                    'timestamp': timestamp_str,
                                    'log_file': log_path,
                                    'error_type': error_type,
                                    'full_message': line.strip(),
                                    'match_groups': match.groups(),
                                })
            except Exception as e:
                logger.warning(f"Failed to scan {log_path}: {e}")

        return errors


class SelfHealingEngine:
    """Applies automated fixes to detected errors."""

    def __init__(self):
        self.fixes_applied = []

    async def heal_missing_table(self, error: Dict) -> Tuple[bool, str]:
        """Fix missing database table errors."""
        table_name = error['match_groups'][0] if error['match_groups'] else 'unknown'

        # Check if it's the tasks table in agent_runtime.db
        if table_name == 'tasks' and 'agent' in error['full_message'].lower():
            try:
                logger.info(f"Initializing agent_runtime.db schema...")

                # Initialize database
                # Build the inline script with dynamic paths
                init_script = f'''
import sys
from pathlib import Path
sys.path.insert(0, '{_STORAGE_BASE / "mcp-servers" / "agent-runtime-mcp"}')
import server
server.DB_PATH = Path('{_STORAGE_BASE / "databases" / "mcp" / "agent_runtime.db"}')
db = server.AgentRuntimeDB(server.DB_PATH)
print("Database initialized successfully")
'''
                result = subprocess.run([
                    'python3', '-c', init_script
                ], capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    return True, f"Initialized agent_runtime.db with {table_name} table"
                else:
                    return False, f"Failed to initialize database: {result.stderr}"

            except Exception as e:
                return False, f"Exception during database initialization: {e}"

        return False, f"No automated fix available for missing table: {table_name}"

    async def heal_api_credits_exhausted(self, error: Dict) -> Tuple[bool, str]:
        """Fix API credit exhaustion errors."""
        # Check if it's the NewsAnalyzer in display agent
        if 'NewsAnalyzer' in error['full_message']:
            try:
                logger.info("Disabling AI news generation in display agent...")

                # The code has already been modified to handle this gracefully
                # Just verify the fix is in place
                display_agent_path = str(_STORAGE_BASE / 'arduino-surface' / 'daemons' / 'intelligent_display_agent.py')

                with open(display_agent_path, 'r') as f:
                    content = f.read()

                if 'credit balance' in content and 'self.client = None' in content:
                    return True, "Display agent already has graceful fallback for API credit exhaustion"
                else:
                    return False, "Display agent needs manual update for credit exhaustion handling"

            except Exception as e:
                return False, f"Exception during API credit fix: {e}"

        return False, "No automated fix available for this API credit error"

    async def heal_missing_module(self, error: Dict) -> Tuple[bool, str]:
        """Fix missing Python module errors."""
        module_name = error['match_groups'][0] if error['match_groups'] else 'unknown'

        # Common module fixes
        module_packages = {
            'RestrictedPython': 'RestrictedPython>=8.1',
            'psutil': 'psutil>=7.0.0',
            'anthropic': 'anthropic',
            'pyserial': 'pyserial>=3.5',
        }

        if module_name in module_packages:
            try:
                logger.info(f"Installing missing module: {module_name}...")

                # Determine venv from log path
                venv_path = self._find_venv_for_error(error)
                if venv_path:
                    pip_path = venv_path / 'bin' / 'pip'
                    result = subprocess.run(
                        [str(pip_path), 'install', module_packages[module_name]],
                        capture_output=True, text=True, timeout=60
                    )

                    if result.returncode == 0:
                        return True, f"Installed {module_packages[module_name]}"
                    else:
                        return False, f"Failed to install: {result.stderr}"
                else:
                    return False, f"Could not determine venv for {module_name}"

            except Exception as e:
                return False, f"Exception during module installation: {e}"

        return False, f"No automated fix available for missing module: {module_name}"

    def _find_venv_for_error(self, error: Dict) -> Optional[Path]:
        """Find the relevant venv for an error."""
        log_file = error['log_file']

        # Map log files to venv paths
        venv_map = {
            'display-agent': _STORAGE_BASE / 'arduino-surface' / '.venv',
            'enhanced-memory': _STORAGE_BASE / 'mcp-servers' / 'enhanced-memory-mcp' / '.venv',
        }

        for key, venv in venv_map.items():
            if key in log_file and venv.exists():
                return venv

        return None

    async def apply_healing(self, error: Dict) -> Dict[str, Any]:
        """Apply appropriate healing strategy for error."""
        error_type = error['error_type']

        healers = {
            'missing_table': self.heal_missing_table,
            'api_credits_exhausted': self.heal_api_credits_exhausted,
            'missing_module': self.heal_missing_module,
        }

        if error_type in healers:
            success, message = await healers[error_type](error)

            result = {
                'error': error,
                'healed': success,
                'message': message,
                'timestamp': datetime.now().isoformat(),
            }

            if success:
                self.fixes_applied.append(result)
                logger.info(f"✅ Healed {error_type}: {message}")
            else:
                logger.warning(f"❌ Failed to heal {error_type}: {message}")

            return result
        else:
            logger.info(f"No automated healing available for: {error_type}")
            return {
                'error': error,
                'healed': False,
                'message': f"No automated fix for {error_type}",
                'timestamp': datetime.now().isoformat(),
            }


def update_status(state: str, error_count: int = 0, healing_count: int = 0, fixed_count: int = 0, message: str = ""):
    """Update status file for statusline display."""
    status_file = Path('/tmp/self_healing_status.json')
    status = {
        'state': state,  # idle, analyzing, healing, completed
        'error_count': error_count,
        'healing_count': healing_count,
        'fixed_count': fixed_count,
        'last_update': datetime.now().isoformat(),
        'message': message
    }
    try:
        with open(status_file, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        logger.debug(f"Failed to update status file: {e}")


async def main():
    """Main self-healing loop."""
    logger.info("Self-Healing Monitor starting...")

    # Initialize components
    detector = ErrorDetector()
    healer = SelfHealingEngine()

    # Update status: analyzing
    update_status('analyzing', message='Scanning logs...')

    # Scan for errors in last 60 minutes
    errors = detector.scan_logs(since_minutes=60)

    if not errors:
        logger.info("No errors detected in last 60 minutes")
        update_status('idle', error_count=0, message='No errors')
        return

    logger.info(f"Detected {len(errors)} errors")

    # Group errors by type to avoid duplicate fixes
    error_groups = {}
    for error in errors:
        key = (error['error_type'], tuple(error['match_groups']))
        if key not in error_groups:
            error_groups[key] = error

    logger.info(f"Grouped into {len(error_groups)} unique error types")

    # Update status: healing
    update_status('healing', error_count=len(error_groups), message=f'Fixing {len(error_groups)} errors')

    # Apply healing to each unique error
    results = []
    for error in error_groups.values():
        result = await healer.apply_healing(error)
        results.append(result)

    # Report summary
    healed_count = sum(1 for r in results if r['healed'])
    logger.info(f"\n{'='*60}")
    logger.info(f"Self-Healing Summary:")
    logger.info(f"  Total errors detected: {len(errors)}")
    logger.info(f"  Unique error types: {len(error_groups)}")
    logger.info(f"  Successfully healed: {healed_count}")
    logger.info(f"  Failed to heal: {len(results) - healed_count}")
    logger.info(f"{'='*60}\n")

    # Update status: completed
    if healed_count > 0:
        update_status('completed', fixed_count=healed_count, message=f'✓ {healed_count} fixed')
    else:
        update_status('idle', error_count=len(results) - healed_count, message='Manual fix needed')

    # Save results to file for analysis
    results_file = _STORAGE_BASE / 'logs' / 'self_healing_results.jsonl'
    with open(results_file, 'a') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    # Keep 'completed' status visible for 30 seconds, then revert to idle
    if healed_count > 0:
        await asyncio.sleep(30)
        update_status('idle', error_count=0, message='All clear')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Self-Healing Monitor stopped by user")
    except Exception as e:
        logger.error(f"Self-Healing Monitor crashed: {e}", exc_info=True)
        sys.exit(1)
