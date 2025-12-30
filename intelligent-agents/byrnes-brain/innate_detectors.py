#!/usr/bin/env python3
"""
Innate Detector System - Fast Pre-Conscious Quality Gates

Inspired by Steve Byrnes' brain architecture theory:
- These are the "superior colliculus" of the AI system
- Fast pattern matching that fires BEFORE conscious reasoning
- Like the flinch reflex - doesn't wait for understanding

Design Principles:
1. SPEED: Pure regex, pre-compiled patterns, no LLM calls
2. FAIL-SAFE: Critical threats block immediately
3. HIERARCHICAL: Critical > High > Medium > Low severity
4. LEARNING: Results feed into Thought Assessor training

Usage:
    from innate_detectors import InnateDetectorSystem

    system = InnateDetectorSystem()
    alerts = system.quick_scan({'tool': 'Write', 'arguments': {...}})

    if system.should_block_immediately(alerts):
        return {'allow': False, 'alerts': alerts}
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class Severity(Enum):
    """Alert severity levels - determines response behavior"""
    CRITICAL = "critical"  # Block immediately, no exceptions
    HIGH = "high"          # Block, but allow override with approval
    MEDIUM = "medium"      # Warn, log, but allow
    LOW = "low"            # Log only, silent allow


@dataclass
class InnateAlert:
    """Represents a detected threat or violation"""
    alert_type: str
    detector: str
    severity: Severity
    pattern: str
    matched_text: str = ""
    context: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'alert_type': self.alert_type,
            'detector': self.detector,
            'severity': self.severity.value,
            'pattern': self.pattern,
            'matched_text': self.matched_text[:100] if self.matched_text else "",
            'context': self.context,
            'timestamp': self.timestamp
        }


class BaseDetector:
    """Base class for all innate detectors"""

    name: str = "base"

    def scan(self, action: dict) -> Optional[InnateAlert]:
        """Scan action for threats. Override in subclass."""
        raise NotImplementedError

    def _get_content(self, action: dict) -> str:
        """Extract scannable content from action"""
        tool = action.get('tool', '')
        args = action.get('arguments', {})

        parts = [tool]

        # Extract content based on tool type
        if tool == 'Write':
            parts.append(str(args.get('content', '')))
            parts.append(str(args.get('file_path', '')))
        elif tool == 'Edit':
            parts.append(str(args.get('old_string', '')))
            parts.append(str(args.get('new_string', '')))
            parts.append(str(args.get('file_path', '')))
        elif tool == 'MultiEdit':
            for edit in args.get('edits', []):
                parts.append(str(edit.get('old_string', '')))
                parts.append(str(edit.get('new_string', '')))
            parts.append(str(args.get('file_path', '')))
        elif tool == 'Bash':
            parts.append(str(args.get('command', '')))
            parts.append(str(args.get('description', '')))
        elif tool == 'Task':
            parts.append(str(args.get('prompt', '')))
            parts.append(str(args.get('description', '')))
        else:
            # Generic: stringify all arguments
            parts.append(str(args))

        return '\n'.join(parts)


class SecurityThreatDetector(BaseDetector):
    """
    Innate detector for security threats.
    Like snake/spider detection - hardcoded by evolution.
    """

    name = "security_threat"

    # Pre-compiled patterns for speed
    # Using raw strings and escaping carefully
    DANGEROUS_COMMAND_PATTERNS = [
        # Destructive file operations
        (re.compile(r'rm\s+(-[rf]+\s+)*/', re.IGNORECASE),
         'destructive_rm', Severity.CRITICAL),
        (re.compile(r'rm\s+-[rf]*\s+\*', re.IGNORECASE),
         'wildcard_delete', Severity.CRITICAL),
        (re.compile(r'>\s*/dev/sd[a-z]', re.IGNORECASE),
         'disk_overwrite', Severity.CRITICAL),
        (re.compile(r'mkfs\s+', re.IGNORECASE),
         'format_disk', Severity.CRITICAL),
        (re.compile(r'dd\s+.*of=/dev/', re.IGNORECASE),
         'dd_to_device', Severity.CRITICAL),

        # SQL injection patterns
        (re.compile(r"DROP\s+(TABLE|DATABASE|INDEX)", re.IGNORECASE),
         'sql_drop', Severity.CRITICAL),
        (re.compile(r"DELETE\s+FROM\s+\w+\s*;?\s*$", re.IGNORECASE),
         'sql_delete_all', Severity.HIGH),
        (re.compile(r"TRUNCATE\s+TABLE", re.IGNORECASE),
         'sql_truncate', Severity.HIGH),
        (re.compile(r";\s*--", re.IGNORECASE),
         'sql_injection', Severity.HIGH),

        # Command injection
        (re.compile(r'\$\([^)]*\)', re.IGNORECASE),
         'command_substitution', Severity.MEDIUM),
        (re.compile(r'`[^`]+`'),
         'backtick_execution', Severity.MEDIUM),

        # Dangerous system commands
        (re.compile(r'chmod\s+777', re.IGNORECASE),
         'world_writable', Severity.HIGH),
        (re.compile(r'chmod\s+\+s', re.IGNORECASE),
         'setuid_bit', Severity.HIGH),
        (re.compile(r'sudo\s+.*passwd', re.IGNORECASE),
         'password_change', Severity.HIGH),

        # Fork bombs and resource attacks
        (re.compile(r':\(\)\s*\{\s*:\|:&\s*\};\s*:'),
         'fork_bomb', Severity.CRITICAL),
        (re.compile(r'while\s*\(\s*true\s*\)|while\s+true|for\s*\(\s*;\s*;\s*\)'),
         'infinite_loop', Severity.HIGH),
    ]

    SECRET_PATTERNS = [
        # API Keys
        (re.compile(r'sk-[a-zA-Z0-9]{20,}'),
         'openai_key', Severity.CRITICAL),
        (re.compile(r'sk-ant-[a-zA-Z0-9\-]{20,}'),
         'anthropic_key', Severity.CRITICAL),
        (re.compile(r'gsk_[a-zA-Z0-9]{20,}'),
         'groq_key', Severity.CRITICAL),
        (re.compile(r'AIza[a-zA-Z0-9\-_]{35}'),
         'google_api_key', Severity.CRITICAL),

        # GitHub tokens
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'),
         'github_pat', Severity.CRITICAL),
        (re.compile(r'gho_[a-zA-Z0-9]{36}'),
         'github_oauth', Severity.CRITICAL),
        (re.compile(r'ghu_[a-zA-Z0-9]{36}'),
         'github_user_token', Severity.CRITICAL),
        (re.compile(r'ghs_[a-zA-Z0-9]{36}'),
         'github_server_token', Severity.CRITICAL),

        # AWS
        (re.compile(r'AKIA[0-9A-Z]{16}'),
         'aws_access_key', Severity.CRITICAL),
        (re.compile(r'aws_secret_access_key\s*=\s*["\'][^"\']{20,}["\']', re.IGNORECASE),
         'aws_secret_key', Severity.CRITICAL),

        # Private keys
        (re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),
         'private_key', Severity.CRITICAL),
        (re.compile(r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----'),
         'ec_private_key', Severity.CRITICAL),
        (re.compile(r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----'),
         'ssh_private_key', Severity.CRITICAL),

        # Database connection strings
        (re.compile(r'mongodb(\+srv)?://[^:]+:[^@]+@', re.IGNORECASE),
         'mongodb_connection', Severity.HIGH),
        (re.compile(r'postgres(ql)?://[^:]+:[^@]+@', re.IGNORECASE),
         'postgres_connection', Severity.HIGH),
        (re.compile(r'mysql://[^:]+:[^@]+@', re.IGNORECASE),
         'mysql_connection', Severity.HIGH),
        (re.compile(r'redis://:[^@]+@', re.IGNORECASE),
         'redis_connection', Severity.HIGH),
    ]

    def scan(self, action: dict) -> Optional[InnateAlert]:
        content = self._get_content(action)

        # Check dangerous commands
        for pattern, threat_type, severity in self.DANGEROUS_COMMAND_PATTERNS:
            match = pattern.search(content)
            if match:
                return InnateAlert(
                    alert_type=threat_type,
                    detector=self.name,
                    severity=severity,
                    pattern=pattern.pattern,
                    matched_text=match.group(0),
                    context=f"Dangerous command detected in {action.get('tool', 'unknown')}"
                )

        # Check for secrets
        for pattern, secret_type, severity in self.SECRET_PATTERNS:
            match = pattern.search(content)
            if match:
                # Redact the actual secret in the alert
                redacted = match.group(0)[:8] + '...[REDACTED]'
                return InnateAlert(
                    alert_type='secret_exposure',
                    detector=self.name,
                    severity=severity,
                    pattern=f"{secret_type}_pattern",
                    matched_text=redacted,
                    context=f"Potential {secret_type} exposure"
                )

        return None


class ProductionViolationDetector(BaseDetector):
    """
    Innate detector for production-only policy violations.
    Ember's core enforcement mechanism.
    """

    name = "production_violation"

    VIOLATION_PATTERNS = [
        # Explicit non-production markers
        (re.compile(r'\b(proof[\s\-_]?of[\s\-_]?concept|POC)\b', re.IGNORECASE),
         'poc_marker', Severity.HIGH),
        (re.compile(r'\bdemo[\s\-_]?(version|mode|implementation|impl)\b', re.IGNORECASE),
         'demo_marker', Severity.HIGH),
        (re.compile(r'\b(prototype|prototyping)\b', re.IGNORECASE),
         'prototype_marker', Severity.MEDIUM),

        # Placeholder content
        (re.compile(r'\b(lorem\s+ipsum|placeholder\s+text)\b', re.IGNORECASE),
         'placeholder_text', Severity.HIGH),
        (re.compile(r'TODO:\s*implement', re.IGNORECASE),
         'todo_implement', Severity.MEDIUM),
        (re.compile(r'FIXME:', re.IGNORECASE),
         'fixme_marker', Severity.LOW),
        (re.compile(r'XXX:', re.IGNORECASE),
         'xxx_marker', Severity.LOW),

        # Mock/fake data patterns
        (re.compile(r'\b(mock|fake|dummy|stub)[\s\-_]?(data|response|api|server|service)\b', re.IGNORECASE),
         'mock_data', Severity.HIGH),
        (re.compile(r'\b(hardcoded|hard[\s\-_]?coded)[\s\-_]?(value|data|credential)s?\b', re.IGNORECASE),
         'hardcoded_data', Severity.HIGH),
        (re.compile(r'\bstatic[\s\-_]?(dashboard|data|content)\b', re.IGNORECASE),
         'static_content', Severity.MEDIUM),

        # Empty implementations
        (re.compile(r'^\s*pass\s*$', re.MULTILINE),
         'empty_pass', Severity.MEDIUM),
        (re.compile(r'raise\s+NotImplementedError', re.IGNORECASE),
         'not_implemented', Severity.HIGH),
        (re.compile(r'throw\s+new\s+Error\s*\(\s*["\']not\s+implemented', re.IGNORECASE),
         'not_implemented_js', Severity.HIGH),

        # Example/sample markers
        (re.compile(r'\b(example|sample)[\s\-_]?(code|implementation|data)\b', re.IGNORECASE),
         'example_code', Severity.MEDIUM),
        (re.compile(r'#\s*example\s+usage', re.IGNORECASE),
         'example_usage', Severity.LOW),

        # Test data in production code
        (re.compile(r'test@(test|example)\.com', re.IGNORECASE),
         'test_email', Severity.MEDIUM),
        (re.compile(r'"(password|secret)":\s*"(password|secret|123|test)"', re.IGNORECASE),
         'weak_test_password', Severity.HIGH),
    ]

    def scan(self, action: dict) -> Optional[InnateAlert]:
        content = self._get_content(action)
        tool = action.get('tool', '')

        # Only check write operations
        if tool not in ['Write', 'Edit', 'MultiEdit', 'Task']:
            return None

        for pattern, violation_type, severity in self.VIOLATION_PATTERNS:
            match = pattern.search(content)
            if match:
                return InnateAlert(
                    alert_type=violation_type,
                    detector=self.name,
                    severity=severity,
                    pattern=pattern.pattern[:50],
                    matched_text=match.group(0),
                    context=f"Production-only policy violation: {violation_type}"
                )

        return None


class ResourceExhaustionDetector(BaseDetector):
    """
    Innate detector for resource exhaustion attacks.
    Prevents infinite loops, memory bombs, and CPU hogs.
    """

    name = "resource_exhaustion"

    PATTERNS = [
        # Infinite loops
        (re.compile(r'while\s*\(\s*true\s*\)\s*\{?\s*\}?', re.IGNORECASE),
         'infinite_while_true', Severity.HIGH),
        (re.compile(r'while\s+True\s*:', re.IGNORECASE),
         'infinite_while_python', Severity.HIGH),
        (re.compile(r'for\s*\(\s*;\s*;\s*\)', re.IGNORECASE),
         'infinite_for_loop', Severity.HIGH),
        (re.compile(r'loop\s*\{[^}]*\}', re.IGNORECASE),
         'infinite_rust_loop', Severity.MEDIUM),

        # Recursive bombs
        (re.compile(r'def\s+(\w+)\([^)]*\):[^:]*\1\s*\(', re.IGNORECASE),
         'recursive_call_python', Severity.MEDIUM),
        (re.compile(r'function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*\1\s*\(', re.IGNORECASE),
         'recursive_call_js', Severity.MEDIUM),

        # Memory allocation bombs
        (re.compile(r'\[\s*["\'][^"\']*["\']\s*\]\s*\*\s*\d{6,}', re.IGNORECASE),
         'large_list_multiplication', Severity.HIGH),
        (re.compile(r'range\s*\(\s*\d{9,}\s*\)', re.IGNORECASE),
         'huge_range', Severity.HIGH),
        (re.compile(r'new\s+Array\s*\(\s*\d{9,}\s*\)', re.IGNORECASE),
         'huge_array_js', Severity.HIGH),

        # Sleep bombs (denial of service)
        (re.compile(r'sleep\s*\(\s*\d{5,}\s*\)', re.IGNORECASE),
         'long_sleep', Severity.MEDIUM),
        (re.compile(r'time\.sleep\s*\(\s*\d{4,}\s*\)', re.IGNORECASE),
         'long_sleep_python', Severity.MEDIUM),
    ]

    def scan(self, action: dict) -> Optional[InnateAlert]:
        content = self._get_content(action)
        tool = action.get('tool', '')

        # Only check code-writing operations
        if tool not in ['Write', 'Edit', 'MultiEdit', 'Bash']:
            return None

        for pattern, exhaustion_type, severity in self.PATTERNS:
            match = pattern.search(content)
            if match:
                return InnateAlert(
                    alert_type=exhaustion_type,
                    detector=self.name,
                    severity=severity,
                    pattern=pattern.pattern[:50],
                    matched_text=match.group(0)[:100],
                    context=f"Potential resource exhaustion: {exhaustion_type}"
                )

        return None


class DataCorruptionDetector(BaseDetector):
    """
    Innate detector for data corruption operations.
    Protects against accidental data loss.
    """

    name = "data_corruption"

    PATTERNS = [
        # Database destructive operations
        (re.compile(r'\.drop\s*\(\s*\)', re.IGNORECASE),
         'mongodb_drop', Severity.HIGH),
        (re.compile(r'\.deleteMany\s*\(\s*\{\s*\}\s*\)', re.IGNORECASE),
         'mongodb_delete_all', Severity.CRITICAL),
        (re.compile(r'\.remove\s*\(\s*\{\s*\}\s*\)', re.IGNORECASE),
         'mongodb_remove_all', Severity.CRITICAL),

        # File system corruption
        (re.compile(r'shutil\.rmtree\s*\(\s*["\'][/~]', re.IGNORECASE),
         'rmtree_root', Severity.CRITICAL),
        (re.compile(r'os\.remove\s*\(\s*["\'][/~]', re.IGNORECASE),
         'remove_root', Severity.HIGH),
        (re.compile(r'pathlib\.Path\s*\([^)]*\)\.unlink\s*\(\s*\)', re.IGNORECASE),
         'pathlib_unlink', Severity.MEDIUM),

        # Git destructive operations
        (re.compile(r'git\s+(push\s+--force|reset\s+--hard|clean\s+-fd)', re.IGNORECASE),
         'git_destructive', Severity.HIGH),
        (re.compile(r'git\s+branch\s+-[dD]\s+', re.IGNORECASE),
         'git_branch_delete', Severity.MEDIUM),

        # Overwriting without backup
        (re.compile(r'>\s+[^|]+\.(db|sqlite|json|yaml|yml|conf|config)$', re.IGNORECASE | re.MULTILINE),
         'config_overwrite', Severity.MEDIUM),
    ]

    def scan(self, action: dict) -> Optional[InnateAlert]:
        content = self._get_content(action)

        for pattern, corruption_type, severity in self.PATTERNS:
            match = pattern.search(content)
            if match:
                return InnateAlert(
                    alert_type=corruption_type,
                    detector=self.name,
                    severity=severity,
                    pattern=pattern.pattern[:50],
                    matched_text=match.group(0)[:100],
                    context=f"Potential data corruption: {corruption_type}"
                )

        return None


class PrivacyViolationDetector(BaseDetector):
    """
    Innate detector for privacy violations.
    Protects PII and sensitive user data.
    """

    name = "privacy_violation"

    PATTERNS = [
        # PII patterns
        (re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'),
         'ssn_pattern', Severity.CRITICAL),
        (re.compile(r'\b\d{16}\b'),
         'credit_card_pattern', Severity.CRITICAL),
        (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
         'credit_card_formatted', Severity.CRITICAL),

        # Email harvesting
        (re.compile(r'\.findAll\s*\([^)]*email', re.IGNORECASE),
         'email_harvesting', Severity.HIGH),
        (re.compile(r're\.findall\s*\([^)]*@[^)]*\)', re.IGNORECASE),
         'email_regex_harvest', Severity.HIGH),

        # Password/credential logging
        (re.compile(r'(print|console\.log|logger\.\w+)\s*\([^)]*password', re.IGNORECASE),
         'password_logging', Severity.CRITICAL),
        (re.compile(r'(print|console\.log|logger\.\w+)\s*\([^)]*secret', re.IGNORECASE),
         'secret_logging', Severity.CRITICAL),
        (re.compile(r'(print|console\.log|logger\.\w+)\s*\([^)]*token', re.IGNORECASE),
         'token_logging', Severity.HIGH),

        # Data exfiltration patterns
        (re.compile(r'requests\.(get|post)\s*\([^)]*user_?data', re.IGNORECASE),
         'data_exfiltration', Severity.HIGH),
        (re.compile(r'fetch\s*\([^)]*\+\s*user', re.IGNORECASE),
         'data_exfiltration_js', Severity.HIGH),
    ]

    def scan(self, action: dict) -> Optional[InnateAlert]:
        content = self._get_content(action)
        tool = action.get('tool', '')

        for pattern, privacy_type, severity in self.PATTERNS:
            match = pattern.search(content)
            if match:
                # Redact actual matches for privacy
                matched = match.group(0)
                if len(matched) > 8:
                    matched = matched[:4] + '...' + matched[-4:]

                return InnateAlert(
                    alert_type=privacy_type,
                    detector=self.name,
                    severity=severity,
                    pattern=pattern.pattern[:50],
                    matched_text=matched,
                    context=f"Privacy violation: {privacy_type}"
                )

        return None


class InnateDetectorSystem:
    """
    Central coordinator for all innate detectors.
    Runs all detectors in parallel (conceptually) and aggregates results.
    """

    def __init__(self):
        self.detectors = [
            SecurityThreatDetector(),
            ProductionViolationDetector(),
            ResourceExhaustionDetector(),
            DataCorruptionDetector(),
            PrivacyViolationDetector(),
        ]

        # Alerts that warrant immediate blocking
        self.critical_alert_types = {
            # Security
            'destructive_rm', 'wildcard_delete', 'disk_overwrite',
            'format_disk', 'dd_to_device', 'fork_bomb',
            'sql_drop', 'secret_exposure',
            # Data corruption
            'mongodb_delete_all', 'mongodb_remove_all', 'rmtree_root',
            # Privacy
            'ssn_pattern', 'credit_card_pattern', 'credit_card_formatted',
            'password_logging', 'secret_logging',
        }

        # Stats for monitoring
        self.scan_count = 0
        self.alert_count = 0
        self.block_count = 0

    def quick_scan(self, action: dict) -> List[InnateAlert]:
        """
        Run ALL detectors, return all alerts.
        This is designed to be FAST - pure regex, no I/O.

        Args:
            action: Dict with 'tool' and 'arguments' keys

        Returns:
            List of InnateAlert objects (may be empty)
        """
        self.scan_count += 1
        alerts = []

        for detector in self.detectors:
            try:
                alert = detector.scan(action)
                if alert:
                    alerts.append(alert)
                    self.alert_count += 1
            except Exception as e:
                # Detector failure should never block
                # But we should log it
                pass

        return alerts

    def should_block_immediately(self, alerts: List[InnateAlert]) -> bool:
        """
        Determine if any alerts warrant immediate blocking.

        Critical severity always blocks.
        Certain alert types always block regardless of severity.
        """
        for alert in alerts:
            # Critical severity always blocks
            if alert.severity == Severity.CRITICAL:
                self.block_count += 1
                return True

            # Certain alert types always block
            if alert.alert_type in self.critical_alert_types:
                self.block_count += 1
                return True

        return False

    def get_blocking_alerts(self, alerts: List[InnateAlert]) -> List[InnateAlert]:
        """Get only the alerts that would cause blocking"""
        blocking = []
        for alert in alerts:
            if alert.severity == Severity.CRITICAL:
                blocking.append(alert)
            elif alert.alert_type in self.critical_alert_types:
                blocking.append(alert)
        return blocking

    def format_block_message(self, alerts: List[InnateAlert]) -> str:
        """Format a human-readable block message"""
        blocking = self.get_blocking_alerts(alerts)
        if not blocking:
            return ""

        messages = []
        for alert in blocking[:3]:  # Limit to first 3
            messages.append(f"[{alert.severity.value.upper()}] {alert.context}")

        return "; ".join(messages)

    def get_stats(self) -> dict:
        """Get detector statistics"""
        return {
            'scan_count': self.scan_count,
            'alert_count': self.alert_count,
            'block_count': self.block_count,
            'block_rate': self.block_count / max(self.scan_count, 1),
            'alert_rate': self.alert_count / max(self.scan_count, 1),
        }


# Singleton instance for performance
_system = None

def get_innate_detector_system() -> InnateDetectorSystem:
    """Get or create singleton detector system"""
    global _system
    if _system is None:
        _system = InnateDetectorSystem()
    return _system


def quick_innate_scan(action: dict) -> tuple[bool, List[InnateAlert]]:
    """
    Convenience function for quick scanning.

    Returns:
        Tuple of (should_allow, alerts)
    """
    system = get_innate_detector_system()
    alerts = system.quick_scan(action)
    should_allow = not system.should_block_immediately(alerts)
    return should_allow, alerts


if __name__ == "__main__":
    # Test harness
    import json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Run self-tests
        system = InnateDetectorSystem()

        test_cases = [
            # Should block - security
            {'tool': 'Bash', 'arguments': {'command': 'rm -rf /'}},
            {'tool': 'Write', 'arguments': {'content': 'sk-' + 'ant-1234567890abcdefghij'}},
            {'tool': 'Bash', 'arguments': {'command': 'DROP TABLE users;'}},

            # Should block - production violation
            {'tool': 'Write', 'arguments': {'content': 'This is a POC implementation'}},
            {'tool': 'Write', 'arguments': {'content': 'lorem ipsum dolor sit amet'}},

            # Should allow
            {'tool': 'Read', 'arguments': {'file_path': '/etc/passwd'}},
            {'tool': 'Write', 'arguments': {'content': 'def hello(): return "world"'}},
            {'tool': 'Bash', 'arguments': {'command': 'ls -la'}},
        ]

        print("Running innate detector tests...\n")
        for i, test in enumerate(test_cases):
            alerts = system.quick_scan(test)
            should_block = system.should_block_immediately(alerts)

            status = "BLOCK" if should_block else "ALLOW"
            print(f"Test {i+1}: {status}")
            print(f"  Tool: {test['tool']}")
            print(f"  Args: {str(test['arguments'])[:60]}...")
            if alerts:
                for alert in alerts:
                    print(f"  Alert: [{alert.severity.value}] {alert.alert_type}")
            print()

        print(f"Stats: {system.get_stats()}")
    else:
        # Normal operation - read from stdin
        try:
            action = json.loads(sys.stdin.read())
            should_allow, alerts = quick_innate_scan(action)

            result = {
                'allow': should_allow,
                'alerts': [a.to_dict() for a in alerts]
            }

            if not should_allow:
                system = get_innate_detector_system()
                result['error'] = system.format_block_message(alerts)

            print(json.dumps(result))
        except Exception as e:
            # On error, fail open
            print(json.dumps({'allow': True, 'error': str(e)}))
