#!/usr/bin/env python3
"""
GitHub Repository Hygiene Agent

Ensures repositories are clean, secure, and free of sensitive data before pushing.
Provides automated auditing and pre-push safety checks.

Features:
- Pre-push hook validation (blocks sensitive data)
- Repository audit for exposed secrets/databases/configs
- .gitignore enforcement and generation
- Multi-repo maintenance for published MCP servers
- Automated cleanup recommendations

Usage:
    python3 github_hygiene_agent.py --audit              # Audit current repo
    python3 github_hygiene_agent.py --audit-all          # Audit all published repos
    python3 github_hygiene_agent.py --generate-gitignore # Generate comprehensive .gitignore
    python3 github_hygiene_agent.py --pre-push-check     # Run pre-push validation
    python3 github_hygiene_agent.py --daemon             # Run as continuous daemon
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path.home() / "agentic-system" / "logs" / "github-hygiene.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# SENSITIVE DATA PATTERNS
# ============================================================================

SENSITIVE_FILE_PATTERNS = {
    # Databases
    "databases": [
        r".*\.db$",
        r".*\.sqlite$",
        r".*\.sqlite3$",
        r".*\.db-shm$",
        r".*\.db-wal$",
        r"databases/.*",
        r".*\.ldb$",  # LevelDB
        r".*\.sst$",  # RocksDB
    ],

    # Configuration with secrets
    "config_secrets": [
        r".*\.env$",
        r".*\.env\..*",
        r"\.env\.local$",
        r"\.env\.production$",
        r"config\.local\..*",
        r"secrets\..*",
        r"credentials\..*",
        r".*_credentials\..*",
        r".*\.pem$",
        r".*\.key$",
        r".*\.p12$",
        r".*\.pfx$",
        r".*\.keystore$",
        r"id_rsa.*",
        r"id_ed25519.*",
        r".*_rsa$",
        r".*\.gpg$",
    ],

    # Personal data
    "personal": [
        r"\$HOME/.*",
        r"~/.*/.*",
        r".*/\.claude/.*",
        r".*pet.*state.*\.json$",
        r".*session.*\.json$",
        r".*history.*\.json$",
        r".*personal.*\..*$",
    ],

    # Logs (may contain sensitive info)
    "logs": [
        r".*\.log$",
        r".*\.log\.\d+$",
        r"logs/.*",
        r".*-log\..*",
    ],

    # Binary artifacts
    "binaries": [
        r"bin/.*",
        r".*\.exe$",
        r".*\.dll$",
        r".*\.so$",
        r".*\.dylib$",
        r".*\.a$",
        r".*\.o$",
        r".*\.pyc$",
        r"__pycache__/.*",
        r"\.venv/.*",
        r"venv/.*",
        r"node_modules/.*",
    ],

    # Temporary files
    "temporary": [
        r"tmp-workspace/.*",
        r"tmp/.*",
        r"temp/.*",
        r"\.tmp$",
        r".*\.swp$",
        r".*\.swo$",
        r".*~$",
    ],

    # Cache
    "cache": [
        r"\.cache/.*",
        r".*cache.*",
        r"\.pytest_cache/.*",
        r"\.mypy_cache/.*",
        r"\.ruff_cache/.*",
    ],

    # OS files
    "os_files": [
        r"\.DS_Store$",
        r"Thumbs\.db$",
        r"desktop\.ini$",
    ],
}

# Content patterns that indicate secrets
SECRET_CONTENT_PATTERNS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key"),
    (r"sk-ant-[a-zA-Z0-9-]{32,}", "Anthropic API Key"),
    (r"AIza[a-zA-Z0-9_-]{35}", "Google API Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"github_pat_[a-zA-Z0-9_]{82}", "GitHub Fine-Grained PAT"),
    (r"xox[baprs]-[a-zA-Z0-9-]+", "Slack Token"),
    (r"AKIA[A-Z0-9]{16}", "AWS Access Key ID"),
    (r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Key"),
    (r"-----BEGIN CERTIFICATE-----", "Certificate"),
    (r"postgres://[^:]+:[^@]+@", "PostgreSQL Connection String"),
    (r"mysql://[^:]+:[^@]+@", "MySQL Connection String"),
    (r"mongodb(\+srv)?://[^:]+:[^@]+@", "MongoDB Connection String"),
    (r"redis://:[^@]+@", "Redis Connection String"),
    (r"Bearer [a-zA-Z0-9_-]{20,}", "Bearer Token"),
    (r"Basic [a-zA-Z0-9+/=]{20,}", "Basic Auth Token"),
    (r"password\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded Password"),
    (r"api[_-]?key\s*[=:]\s*['\"][^'\"]+['\"]", "API Key Assignment"),
    (r"secret\s*[=:]\s*['\"][^'\"]+['\"]", "Secret Assignment"),
]

# Size thresholds
MAX_FILE_SIZE_MB = 50  # GitHub recommends <50MB
MAX_REPO_SIZE_MB = 500  # Warning threshold


@dataclass
class AuditFinding:
    """A single audit finding"""
    severity: str  # critical, high, medium, low
    category: str
    file_path: str
    description: str
    recommendation: str
    line_number: Optional[int] = None
    matched_pattern: Optional[str] = None


@dataclass
class AuditReport:
    """Complete audit report for a repository"""
    repo_path: str
    repo_name: str
    timestamp: str
    findings: List[AuditFinding] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return len([f for f in self.findings if f.severity == "critical"])

    @property
    def high_count(self) -> int:
        return len([f for f in self.findings if f.severity == "high"])

    @property
    def is_safe_to_push(self) -> bool:
        return self.critical_count == 0

    def to_dict(self) -> Dict:
        return {
            "repo_path": self.repo_path,
            "repo_name": self.repo_name,
            "timestamp": self.timestamp,
            "summary": {
                "total_findings": len(self.findings),
                "critical": self.critical_count,
                "high": self.high_count,
                "safe_to_push": self.is_safe_to_push,
            },
            "findings": [
                {
                    "severity": f.severity,
                    "category": f.category,
                    "file_path": f.file_path,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in self.findings
            ],
            "stats": self.stats,
            "recommendations": self.recommendations,
        }


class GitHubHygieneAgent:
    """Agent for maintaining GitHub repository hygiene"""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.storage_base = Path(os.environ.get(
            "STORAGE_BASE",
            "/Volumes/SSDRAID0/agentic-system"
        ))

        # Compiled regex patterns for performance
        self._file_patterns = {
            category: [re.compile(p, re.IGNORECASE) for p in patterns]
            for category, patterns in SENSITIVE_FILE_PATTERNS.items()
        }
        self._content_patterns = [
            (re.compile(p), desc) for p, desc in SECRET_CONTENT_PATTERNS
        ]

    def get_tracked_files(self) -> List[str]:
        """Get list of files tracked by git"""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
        except Exception as e:
            logger.error(f"Failed to get tracked files: {e}")
            return []

    def get_staged_files(self) -> List[str]:
        """Get list of files staged for commit"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
            return []
        except Exception as e:
            logger.error(f"Failed to get staged files: {e}")
            return []

    def check_file_patterns(self, file_path: str) -> List[Tuple[str, str]]:
        """Check if file matches sensitive patterns"""
        matches = []
        for category, patterns in self._file_patterns.items():
            for pattern in patterns:
                if pattern.search(file_path):
                    matches.append((category, pattern.pattern))
        return matches

    def check_file_content(self, file_path: Path) -> List[Tuple[str, int, str]]:
        """Check file content for secrets"""
        matches = []
        try:
            # Skip binary files
            if self._is_binary(file_path):
                return matches

            # Skip large files
            if file_path.stat().st_size > 1_000_000:  # 1MB
                return matches

            content = file_path.read_text(errors="ignore")
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for pattern, description in self._content_patterns:
                    if pattern.search(line):
                        # Don't include actual secret in report
                        matches.append((description, i, line[:50] + "..."))
        except Exception as e:
            logger.debug(f"Could not check content of {file_path}: {e}")

        return matches

    def _is_binary(self, file_path: Path) -> bool:
        """Check if file is binary"""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)
                return b"\x00" in chunk
        except:
            return True

    def get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in MB"""
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except:
            return 0

    def audit_repository(self) -> AuditReport:
        """Perform comprehensive repository audit"""
        logger.info(f"Auditing repository: {self.repo_path}")

        report = AuditReport(
            repo_path=str(self.repo_path),
            repo_name=self.repo_path.name,
            timestamp=datetime.now().isoformat(),
        )

        tracked_files = self.get_tracked_files()
        report.stats["total_tracked_files"] = len(tracked_files)

        total_size_mb = 0
        large_files = []

        for file_str in tracked_files:
            if not file_str:
                continue

            file_path = self.repo_path / file_str

            # Check file patterns
            pattern_matches = self.check_file_patterns(file_str)
            for category, pattern in pattern_matches:
                severity = "critical" if category in ["databases", "config_secrets"] else "high"
                if category in ["logs", "temporary", "cache"]:
                    severity = "medium"
                if category == "os_files":
                    severity = "low"

                report.findings.append(AuditFinding(
                    severity=severity,
                    category=category,
                    file_path=file_str,
                    description=f"Sensitive file pattern detected: {category}",
                    recommendation=f"Add to .gitignore and remove from tracking",
                    matched_pattern=pattern,
                ))

            # Check file size
            if file_path.exists():
                size_mb = self.get_file_size_mb(file_path)
                total_size_mb += size_mb

                if size_mb > MAX_FILE_SIZE_MB:
                    report.findings.append(AuditFinding(
                        severity="critical",
                        category="large_file",
                        file_path=file_str,
                        description=f"File exceeds GitHub recommended size: {size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB",
                        recommendation="Use Git LFS or add to .gitignore",
                    ))
                    large_files.append((file_str, size_mb))

                # Check content for secrets
                content_matches = self.check_file_content(file_path)
                for description, line_num, preview in content_matches:
                    report.findings.append(AuditFinding(
                        severity="critical",
                        category="secret_in_content",
                        file_path=file_str,
                        description=f"Potential {description} found in content",
                        recommendation="Remove secret and rotate credential immediately",
                        line_number=line_num,
                    ))

        report.stats["total_size_mb"] = round(total_size_mb, 2)
        report.stats["large_files_count"] = len(large_files)

        # Generate recommendations
        if report.critical_count > 0:
            report.recommendations.append("CRITICAL: Do not push until critical issues are resolved")

        if large_files:
            report.recommendations.append(
                f"Consider using Git LFS for {len(large_files)} large files"
            )

        categories_found = set(f.category for f in report.findings)
        if "databases" in categories_found:
            report.recommendations.append(
                "Add 'databases/' and '*.db' to .gitignore"
            )
        if "logs" in categories_found:
            report.recommendations.append(
                "Add 'logs/' and '*.log' to .gitignore"
            )

        logger.info(f"Audit complete: {len(report.findings)} findings "
                   f"({report.critical_count} critical, {report.high_count} high)")

        return report

    def pre_push_check(self) -> Tuple[bool, AuditReport]:
        """
        Run pre-push validation.
        Returns (is_safe, report)
        """
        logger.info("Running pre-push safety check...")

        report = self.audit_repository()

        # Also check staged files specifically
        staged = self.get_staged_files()
        for file_str in staged:
            if not file_str:
                continue
            pattern_matches = self.check_file_patterns(file_str)
            if pattern_matches:
                for category, pattern in pattern_matches:
                    if category in ["databases", "config_secrets"]:
                        # Already in findings from audit, but emphasize it's staged
                        logger.error(f"BLOCKED: Staged file matches sensitive pattern: {file_str}")

        is_safe = report.is_safe_to_push

        if is_safe:
            logger.info("Pre-push check PASSED - safe to push")
        else:
            logger.error(f"Pre-push check FAILED - {report.critical_count} critical issues")
            for finding in report.findings:
                if finding.severity == "critical":
                    logger.error(f"  - {finding.file_path}: {finding.description}")

        return is_safe, report

    def generate_gitignore(self) -> str:
        """Generate comprehensive .gitignore content"""
        gitignore = """# ============================================================================
# COMPREHENSIVE .gitignore for Agentic System
# Generated by GitHub Hygiene Agent
# ============================================================================

# ============================================================================
# DATABASES - NEVER COMMIT
# ============================================================================
*.db
*.sqlite
*.sqlite3
*.db-shm
*.db-wal
*.ldb
*.sst
databases/
*.db.corrupted.*

# ============================================================================
# SECRETS & CREDENTIALS - NEVER COMMIT
# ============================================================================
.env
.env.*
.env.local
.env.production
*.env
secrets.*
credentials.*
*_credentials.*
*.pem
*.key
*.p12
*.pfx
*.keystore
id_rsa*
id_ed25519*
*_rsa
*.gpg
.netrc
.npmrc
.pypirc

# ============================================================================
# PERSONAL DATA - NEVER COMMIT
# ============================================================================
**/personal_memories.db
*session*.json
*history*.json
**/.claude/
*pet*state*.json

# ============================================================================
# LOGS - USUALLY DON'T COMMIT
# ============================================================================
*.log
*.log.*
logs/
*-log.*

# ============================================================================
# LARGE FILES (GitHub 100MB limit)
# ============================================================================
*.dmg
*.iso
*.tar.gz
*.tgz
*.zip
*.rar
bin/qdrant
bin/prometheus
bin/grafana*

# ============================================================================
# TEMPORARY & WORKSPACE
# ============================================================================
tmp-workspace/
tmp/
temp/
*.tmp
*.swp
*.swo
*~
.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# ============================================================================
# PYTHON
# ============================================================================
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
ENV/
*.egg-info/
dist/
build/
.eggs/

# ============================================================================
# NODE.JS
# ============================================================================
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn

# ============================================================================
# IDE & EDITORS
# ============================================================================
.vscode/
.idea/
*.sublime-*
.project
.settings/
*.code-workspace

# ============================================================================
# OS FILES
# ============================================================================
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
Thumbs.db
ehthumbs.db
Desktop.ini

# ============================================================================
# EMBEDDED REPOS (submodules managed separately)
# ============================================================================
agentic-cluster-comms/
caveman-compression/
chatterbox-server/
claude-flow/
mcp-servers/nuclei-mcp/
mcp-servers/SAFLA/
openai-edge-tts/
services/kutiraai/

# ============================================================================
# MONITORING DATA
# ============================================================================
monitoring/prometheus-data/
monitoring/loki/chunks/
monitoring/grafana/grafana.db

# ============================================================================
# VOICE & MEDIA CACHE
# ============================================================================
voice-cache/
*.wav
*.mp3
*.m4a

# ============================================================================
# DOCKER
# ============================================================================
DockerDesktopUpdates/
com.docker.install/
"""
        return gitignore

    def audit_remote_repo(self, repo_name: str) -> AuditReport:
        """Audit a remote GitHub repository"""
        import tempfile

        logger.info(f"Auditing remote repo: {repo_name}")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Clone repo
            result = subprocess.run(
                ["git", "clone", "--depth=1", f"https://github.com/{repo_name}.git", "repo"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                logger.error(f"Failed to clone {repo_name}: {result.stderr}")
                return AuditReport(
                    repo_path=repo_name,
                    repo_name=repo_name,
                    timestamp=datetime.now().isoformat(),
                    findings=[AuditFinding(
                        severity="high",
                        category="clone_failed",
                        file_path="",
                        description=f"Failed to clone repository: {result.stderr}",
                        recommendation="Check repository access"
                    )]
                )

            # Audit cloned repo
            agent = GitHubHygieneAgent(Path(tmpdir) / "repo")
            return agent.audit_repository()

    def audit_all_mcp_repos(self, username: str = "marc-shade") -> List[AuditReport]:
        """Audit all MCP repositories for a user"""
        # Get list of repos
        result = subprocess.run(
            ["gh", "repo", "list", username, "--limit", "100", "--json", "name,isPrivate"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"Failed to list repos: {result.stderr}")
            return []

        repos = json.loads(result.stdout)
        mcp_repos = [
            r["name"] for r in repos
            if "mcp" in r["name"].lower() and not r["isPrivate"]
        ]

        logger.info(f"Found {len(mcp_repos)} public MCP repos to audit")

        reports = []
        for repo_name in mcp_repos:
            try:
                report = self.audit_remote_repo(f"{username}/{repo_name}")
                reports.append(report)
            except Exception as e:
                logger.error(f"Failed to audit {repo_name}: {e}")

        return reports

    def fix_gitignore(self) -> bool:
        """Update .gitignore with comprehensive patterns"""
        gitignore_path = self.repo_path / ".gitignore"

        new_content = self.generate_gitignore()

        # Backup existing
        if gitignore_path.exists():
            backup_path = gitignore_path.with_suffix(".gitignore.backup")
            gitignore_path.rename(backup_path)
            logger.info(f"Backed up existing .gitignore to {backup_path}")

        gitignore_path.write_text(new_content)
        logger.info(f"Generated new .gitignore at {gitignore_path}")

        return True

    def remove_sensitive_from_tracking(self, dry_run: bool = True) -> List[str]:
        """Remove sensitive files from git tracking (but keep local copies)"""
        removed = []
        tracked_files = self.get_tracked_files()

        for file_str in tracked_files:
            if not file_str:
                continue

            pattern_matches = self.check_file_patterns(file_str)
            if pattern_matches:
                for category, _ in pattern_matches:
                    if category in ["databases", "config_secrets", "logs", "binaries", "temporary"]:
                        if dry_run:
                            logger.info(f"Would remove from tracking: {file_str}")
                        else:
                            result = subprocess.run(
                                ["git", "rm", "--cached", file_str],
                                cwd=self.repo_path,
                                capture_output=True,
                                text=True
                            )
                            if result.returncode == 0:
                                logger.info(f"Removed from tracking: {file_str}")
                            else:
                                logger.error(f"Failed to remove {file_str}: {result.stderr}")
                        removed.append(file_str)
                        break

        return removed


def main():
    parser = argparse.ArgumentParser(description="GitHub Repository Hygiene Agent")
    parser.add_argument("--audit", action="store_true", help="Audit current repository")
    parser.add_argument("--audit-all", action="store_true", help="Audit all published MCP repos")
    parser.add_argument("--generate-gitignore", action="store_true", help="Generate comprehensive .gitignore")
    parser.add_argument("--pre-push-check", action="store_true", help="Run pre-push validation")
    parser.add_argument("--fix", action="store_true", help="Fix issues (update .gitignore, remove from tracking)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--repo", type=str, help="Repository path (default: current directory)")
    parser.add_argument("--output", type=str, help="Output report to file (JSON)")

    args = parser.parse_args()

    repo_path = Path(args.repo) if args.repo else Path.cwd()
    agent = GitHubHygieneAgent(repo_path)

    if args.generate_gitignore:
        content = agent.generate_gitignore()
        if args.output:
            Path(args.output).write_text(content)
        else:
            print(content)
        return

    if args.audit:
        report = agent.audit_repository()

        if args.output:
            Path(args.output).write_text(json.dumps(report.to_dict(), indent=2))
            logger.info(f"Report saved to {args.output}")
        else:
            print("\n" + "="*60)
            print(f"AUDIT REPORT: {report.repo_name}")
            print("="*60)
            print(f"Timestamp: {report.timestamp}")
            print(f"Total findings: {len(report.findings)}")
            print(f"  - Critical: {report.critical_count}")
            print(f"  - High: {report.high_count}")
            print(f"Safe to push: {'YES' if report.is_safe_to_push else 'NO'}")
            print()

            if report.findings:
                print("FINDINGS:")
                for finding in sorted(report.findings, key=lambda f: ["critical", "high", "medium", "low"].index(f.severity)):
                    print(f"  [{finding.severity.upper()}] {finding.file_path}")
                    print(f"    Category: {finding.category}")
                    print(f"    {finding.description}")
                    print(f"    Recommendation: {finding.recommendation}")
                    print()

            if report.recommendations:
                print("RECOMMENDATIONS:")
                for rec in report.recommendations:
                    print(f"  - {rec}")
        return

    if args.audit_all:
        reports = agent.audit_all_mcp_repos()

        print("\n" + "="*60)
        print("MCP REPOSITORY AUDIT SUMMARY")
        print("="*60)

        for report in reports:
            status = "" if report.is_safe_to_push else ""
            print(f"{status} {report.repo_name}: {len(report.findings)} findings ({report.critical_count} critical)")

        if args.output:
            all_reports = [r.to_dict() for r in reports]
            Path(args.output).write_text(json.dumps(all_reports, indent=2))
        return

    if args.pre_push_check:
        is_safe, report = agent.pre_push_check()
        sys.exit(0 if is_safe else 1)

    if args.fix:
        if args.dry_run:
            print("DRY RUN - showing what would be done:")
            print()

        # Update .gitignore
        if not args.dry_run:
            agent.fix_gitignore()
        else:
            print("Would generate new .gitignore")

        # Remove sensitive files from tracking
        removed = agent.remove_sensitive_from_tracking(dry_run=args.dry_run)
        if removed:
            print(f"\n{'Would remove' if args.dry_run else 'Removed'} {len(removed)} files from tracking")

        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
