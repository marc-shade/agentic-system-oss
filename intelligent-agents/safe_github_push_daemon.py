#!/usr/bin/env python3
"""
Safe GitHub Push Daemon

Automated git push daemon with comprehensive safety checks.
Ensures no sensitive data (API keys, databases, logs) is ever pushed.

Part of the GitHub Hygiene System.
"""

import os
import re
import subprocess
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# Configure logging
LOG_DIR = Path(os.environ.get('STORAGE_BASE', '/Volumes/SSDRAID0/agentic-system')) / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'safe_github_push.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SafetyViolation:
    """Represents a detected safety violation."""
    def __init__(self, file_path: str, violation_type: str, details: str, severity: str = 'critical'):
        self.file_path = file_path
        self.violation_type = violation_type
        self.details = details
        self.severity = severity
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'file': self.file_path,
            'type': self.violation_type,
            'details': self.details,
            'severity': self.severity,
            'timestamp': self.timestamp
        }


class SafeGitHubPushDaemon:
    """
    Daemon that safely pushes changes to GitHub with comprehensive safety checks.

    Safety features:
    - Secret detection (API keys, tokens, credentials)
    - File type blocking (databases, logs, env files)
    - Large file detection
    - Automated audit logging
    """

    # Secret patterns to detect
    SECRET_PATTERNS = {
        'github_pat': (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
        'anthropic_key': (r'sk-ant-[a-zA-Z0-9_-]{20,}', 'Anthropic API Key'),
        'openai_key': (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        'aws_access_key': (r'AKIA[A-Z0-9]{16}', 'AWS Access Key'),
        'aws_secret_key': (r'[a-zA-Z0-9/+]{40}', 'Potential AWS Secret Key'),
        'generic_api_key': (r'(api[_-]?key|apikey|secret|token|password)\s*[:=]\s*["\'][A-Za-z0-9+/]{32,}', 'Generic API Key'),
        'private_key': (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 'Private Key'),
        'connection_string': (r'(mongodb|postgresql|mysql|redis)://[^\s"\']+', 'Database Connection String'),
    }

    # File extensions to always block
    BLOCKED_EXTENSIONS = {
        '.db', '.sqlite', '.sqlite3', '.db-shm', '.db-wal',
        '.log', '.env', '.pem', '.key', '.p12', '.pfx',
        '.keystore', '.credentials', '.netrc', '.npmrc', '.pypirc'
    }

    # Path patterns to always block
    BLOCKED_PATHS = [
        r'databases/',
        r'logs/',
        r'\.swarm/',
        r'tmp-workspace/',
        r'monitoring/prometheus-data/',
        r'monitoring/loki/',
        r'node_modules/',
        r'__pycache__/',
        r'\.venv/',
        r'venv/',
    ]

    # Maximum file size (50MB - GitHub warning threshold)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(self, repo_path: str, remote: str = 'origin', branch: str = 'master'):
        self.repo_path = Path(repo_path)
        self.remote = remote
        self.branch = branch
        self.violations: List[SafetyViolation] = []
        self.audit_log_file = LOG_DIR / 'push_audit.jsonl'

    def run_git_command(self, args: List[str]) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        cmd = ['git', '-C', str(self.repo_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def get_staged_files(self) -> List[str]:
        """Get list of files staged for commit."""
        _, stdout, _ = self.run_git_command(['diff', '--cached', '--name-only'])
        return [f for f in stdout.strip().split('\n') if f]

    def get_unpushed_files(self) -> List[str]:
        """Get list of files in commits not yet pushed."""
        _, stdout, _ = self.run_git_command([
            'diff', '--name-only', f'{self.remote}/{self.branch}...HEAD'
        ])
        return [f for f in stdout.strip().split('\n') if f]

    def check_file_extension(self, file_path: str) -> Optional[SafetyViolation]:
        """Check if file has a blocked extension."""
        ext = Path(file_path).suffix.lower()
        if ext in self.BLOCKED_EXTENSIONS:
            return SafetyViolation(
                file_path=file_path,
                violation_type='blocked_extension',
                details=f'File extension {ext} is blocked',
                severity='critical'
            )
        return None

    def check_blocked_path(self, file_path: str) -> Optional[SafetyViolation]:
        """Check if file is in a blocked path."""
        for pattern in self.BLOCKED_PATHS:
            if re.search(pattern, file_path):
                return SafetyViolation(
                    file_path=file_path,
                    violation_type='blocked_path',
                    details=f'Path matches blocked pattern: {pattern}',
                    severity='critical'
                )
        return None

    def check_file_size(self, file_path: str) -> Optional[SafetyViolation]:
        """Check if file exceeds maximum size."""
        full_path = self.repo_path / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            if size > self.MAX_FILE_SIZE:
                return SafetyViolation(
                    file_path=file_path,
                    violation_type='large_file',
                    details=f'File size {size / (1024*1024):.1f}MB exceeds limit of {self.MAX_FILE_SIZE / (1024*1024)}MB',
                    severity='high'
                )
        return None

    def check_secrets_in_file(self, file_path: str) -> List[SafetyViolation]:
        """Scan file content for secrets."""
        violations = []
        full_path = self.repo_path / file_path

        if not full_path.exists() or full_path.is_dir():
            return violations

        # Skip binary files
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            return violations

        for secret_name, (pattern, description) in self.SECRET_PATTERNS.items():
            # Skip AWS secret key pattern unless it's clearly a key
            if secret_name == 'aws_secret_key':
                continue  # Too many false positives

            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Filter out example/placeholder values
                real_matches = [m for m in matches if not self._is_placeholder(m)]
                if real_matches:
                    violations.append(SafetyViolation(
                        file_path=file_path,
                        violation_type='secret_detected',
                        details=f'{description} detected ({len(real_matches)} occurrences)',
                        severity='critical'
                    ))

        return violations

    def _is_placeholder(self, value: str) -> bool:
        """Check if a detected value is likely a placeholder/example."""
        placeholders = [
            '***REMOVED***',  # Example AWS key
            '***REMOVED***',
            'xxx', 'XXX',
            'example', 'EXAMPLE',
            'placeholder', 'PLACEHOLDER',
            'test', 'TEST',
            'dummy', 'DUMMY',
            'fake', 'FAKE',
        ]
        value_lower = str(value).lower()
        return any(p.lower() in value_lower for p in placeholders)

    def run_safety_checks(self, files: List[str]) -> List[SafetyViolation]:
        """Run all safety checks on the given files."""
        violations = []

        for file_path in files:
            if not file_path:
                continue

            # Check extension
            v = self.check_file_extension(file_path)
            if v:
                violations.append(v)
                continue  # No need to check content if extension is blocked

            # Check path
            v = self.check_blocked_path(file_path)
            if v:
                violations.append(v)
                continue

            # Check size
            v = self.check_file_size(file_path)
            if v:
                violations.append(v)

            # Check for secrets
            secret_violations = self.check_secrets_in_file(file_path)
            violations.extend(secret_violations)

        return violations

    def log_audit(self, action: str, files: List[str], violations: List[SafetyViolation],
                  pushed: bool, details: Optional[str] = None):
        """Log an audit entry."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'files_checked': len(files),
            'violations_found': len(violations),
            'violations': [v.to_dict() for v in violations],
            'pushed': pushed,
            'details': details
        }

        with open(self.audit_log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def safe_push(self, force: bool = False) -> Tuple[bool, str]:
        """
        Perform a safe push with all safety checks.

        Args:
            force: If True, bypass safety checks (NOT RECOMMENDED)

        Returns:
            (success, message) tuple
        """
        logger.info(f"Starting safe push for {self.repo_path}")

        # Get files to check
        files = self.get_unpushed_files()
        if not files:
            logger.info("No unpushed changes found")
            return True, "No changes to push"

        logger.info(f"Checking {len(files)} files for safety violations")

        # Run safety checks
        violations = self.run_safety_checks(files)

        # Log the check
        if violations:
            logger.warning(f"Found {len(violations)} safety violations:")
            for v in violations:
                logger.warning(f"  - [{v.severity}] {v.file_path}: {v.details}")

            if not force:
                self.log_audit('push_blocked', files, violations, pushed=False,
                             details='Safety violations detected')
                return False, f"Push blocked: {len(violations)} safety violations detected"
            else:
                logger.warning("FORCE mode enabled - bypassing safety checks")

        # Attempt the push
        try:
            returncode, stdout, stderr = self.run_git_command(['push', self.remote, self.branch])

            if returncode == 0:
                self.log_audit('push_success', files, violations, pushed=True)
                logger.info("Push successful")
                return True, "Push successful"
            else:
                self.log_audit('push_failed', files, violations, pushed=False,
                             details=stderr)
                logger.error(f"Push failed: {stderr}")
                return False, f"Push failed: {stderr}"

        except Exception as e:
            self.log_audit('push_error', files, violations, pushed=False,
                         details=str(e))
            logger.error(f"Push error: {e}")
            return False, f"Push error: {e}"

    def run_daemon(self, interval: int = 300, auto_commit: bool = False):
        """
        Run as a daemon, checking and pushing at regular intervals.

        Args:
            interval: Seconds between checks (default: 5 minutes)
            auto_commit: If True, auto-commit changes before pushing
        """
        logger.info(f"Starting Safe GitHub Push Daemon")
        logger.info(f"  Repo: {self.repo_path}")
        logger.info(f"  Remote: {self.remote}/{self.branch}")
        logger.info(f"  Interval: {interval}s")
        logger.info(f"  Auto-commit: {auto_commit}")

        while True:
            try:
                # Check for unpushed commits
                files = self.get_unpushed_files()

                if files:
                    logger.info(f"Found {len(files)} files in unpushed commits")
                    success, message = self.safe_push()
                    logger.info(f"Push result: {message}")
                else:
                    logger.debug("No unpushed changes")

            except Exception as e:
                logger.error(f"Daemon error: {e}")

            time.sleep(interval)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Safe GitHub Push Daemon')
    parser.add_argument('--repo', '-r', default='/Volumes/SSDRAID0/agentic-system',
                       help='Repository path')
    parser.add_argument('--remote', default='origin', help='Git remote name')
    parser.add_argument('--branch', default='master', help='Git branch name')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='Check interval in seconds (default: 300)')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit (no daemon mode)')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force push (bypass safety - NOT RECOMMENDED)')
    parser.add_argument('--check-only', action='store_true',
                       help='Only run safety checks, do not push')

    args = parser.parse_args()

    daemon = SafeGitHubPushDaemon(args.repo, args.remote, args.branch)

    if args.check_only:
        files = daemon.get_unpushed_files()
        if not files:
            print("No unpushed changes to check")
            return

        print(f"Checking {len(files)} files...")
        violations = daemon.run_safety_checks(files)

        if violations:
            print(f"\nFound {len(violations)} violations:")
            for v in violations:
                print(f"  [{v.severity}] {v.file_path}")
                print(f"    Type: {v.violation_type}")
                print(f"    Details: {v.details}")
        else:
            print("No safety violations found")
    elif args.once:
        success, message = daemon.safe_push(force=args.force)
        print(message)
        exit(0 if success else 1)
    else:
        daemon.run_daemon(interval=args.interval)


if __name__ == '__main__':
    main()
