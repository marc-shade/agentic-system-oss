#!/usr/bin/env python3
"""
File Change Tracker for Claude Code Control MCP
Tracks file modifications during task execution
"""
import platform

import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime
import os

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


logger = logging.getLogger("claude-code-control.file-tracker")


@dataclass
class FileChange:
    """Represents a file change during execution"""
    path: str
    action: str  # 'created', 'modified', 'deleted', 'read'
    timestamp: str
    before_hash: Optional[str] = None
    after_hash: Optional[str] = None
    before_size: Optional[int] = None
    after_size: Optional[int] = None
    line_changes: Optional[Dict[str, int]] = None


class FileTracker:
    """Tracks file changes during task execution"""

    def __init__(self, working_directory: str = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))):
        self.working_directory = Path(working_directory)
        self.tracked_files: Dict[str, str] = {}  # path -> hash
        self.changes: List[FileChange] = []
        self.read_files: Set[str] = set()

    def _hash_file(self, path: Path) -> Optional[str]:
        """Calculate SHA256 hash of a file"""
        try:
            if not path.exists() or not path.is_file():
                return None
            with open(path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash file {path}: {e}")
            return None

    def _get_file_size(self, path: Path) -> Optional[int]:
        """Get file size in bytes"""
        try:
            return path.stat().st_size if path.exists() else None
        except Exception:
            return None

    def track_file(self, path: str):
        """Start tracking a file"""
        file_path = self.working_directory / path
        file_hash = self._hash_file(file_path)
        if file_hash:
            self.tracked_files[path] = file_hash
            logger.debug(f"Tracking file: {path} (hash: {file_hash[:8]}...)")

    def record_read(self, path: str):
        """Record that a file was read"""
        self.read_files.add(path)
        if path not in self.tracked_files:
            self.track_file(path)

    def check_changes(self) -> List[FileChange]:
        """Check for changes in tracked files"""
        changes = []
        timestamp = datetime.utcnow().isoformat()

        for path, original_hash in self.tracked_files.items():
            file_path = self.working_directory / path
            current_hash = self._hash_file(file_path)

            if current_hash is None and original_hash is not None:
                # File was deleted
                change = FileChange(
                    path=path,
                    action='deleted',
                    timestamp=timestamp,
                    before_hash=original_hash,
                    after_hash=None,
                    before_size=self._get_file_size(file_path)
                )
                changes.append(change)
                logger.info(f"File deleted: {path}")

            elif current_hash != original_hash:
                # File was modified
                before_size = self._get_file_size(file_path)
                after_size = self._get_file_size(file_path)

                change = FileChange(
                    path=path,
                    action='modified',
                    timestamp=timestamp,
                    before_hash=original_hash,
                    after_hash=current_hash,
                    before_size=before_size,
                    after_size=after_size
                )
                changes.append(change)
                logger.info(f"File modified: {path}")

        # Check for newly created files
        try:
            for path in self.working_directory.rglob('*'):
                if path.is_file():
                    rel_path = str(path.relative_to(self.working_directory))
                    if rel_path not in self.tracked_files:
                        current_hash = self._hash_file(path)
                        if current_hash:
                            change = FileChange(
                                path=rel_path,
                                action='created',
                                timestamp=timestamp,
                                before_hash=None,
                                after_hash=current_hash,
                                after_size=self._get_file_size(path)
                            )
                            changes.append(change)
                            logger.info(f"File created: {rel_path}")
        except Exception as e:
            logger.error(f"Error scanning for new files: {e}")

        self.changes.extend(changes)
        return changes

    def get_summary(self) -> Dict:
        """Get summary of all changes"""
        created = [c for c in self.changes if c.action == 'created']
        modified = [c for c in self.changes if c.action == 'modified']
        deleted = [c for c in self.changes if c.action == 'deleted']

        return {
            'total_changes': len(self.changes),
            'files_created': len(created),
            'files_modified': len(modified),
            'files_deleted': len(deleted),
            'files_read': len(self.read_files),
            'created_files': [c.path for c in created],
            'modified_files': [c.path for c in modified],
            'deleted_files': [c.path for c in deleted],
            'read_files': list(self.read_files),
            'detailed_changes': [
                {
                    'path': c.path,
                    'action': c.action,
                    'timestamp': c.timestamp,
                    'before_hash': c.before_hash,
                    'after_hash': c.after_hash,
                    'size_change': (c.after_size - c.before_size) if c.before_size and c.after_size else None
                }
                for c in self.changes
            ]
        }

    def reset(self):
        """Reset tracker state"""
        self.tracked_files.clear()
        self.changes.clear()
        self.read_files.clear()
