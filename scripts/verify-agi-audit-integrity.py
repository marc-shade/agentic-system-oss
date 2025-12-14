#!/usr/bin/env python3
"""
AGI Audit Log Integrity Verification

Verifies the hash-chain integrity of the immutable audit log.
Run via cron to detect any tampering with audit records.

Exit codes:
  0 - Integrity verified
  1 - Integrity compromised
  2 - Error during verification
"""

import hashlib
import json
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

AUDIT_LOG_DIR = Path("/var/log/agi-guardian")
ALERT_FILE = AUDIT_LOG_DIR / "integrity_alerts.log"


def verify_audit_integrity() -> tuple[bool, str]:
    """
    Verify the entire audit chain hasn't been tampered with.

    Returns:
        Tuple of (is_valid, message)
    """
    previous_hash = None
    total_entries = 0

    log_files = sorted(AUDIT_LOG_DIR.glob("*.jsonl"))

    if not log_files:
        return True, "No audit logs to verify"

    for log_file in log_files:
        if log_file.name == "metrics.jsonl":
            continue  # Skip metrics file

        try:
            with open(log_file) as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError as e:
                        return False, f"JSON decode error in {log_file.name}:{line_num}: {e}"

                    # Verify chain continuity
                    if entry.get("previous_hash") != previous_hash:
                        return False, (
                            f"Chain break in {log_file.name}:{line_num}. "
                            f"Expected previous_hash={previous_hash}, "
                            f"got {entry.get('previous_hash')}"
                        )

                    # Verify hash computation
                    stored_hash = entry.pop("hash", None)
                    if stored_hash is None:
                        return False, f"Missing hash in {log_file.name}:{line_num}"

                    computed_hash = hashlib.sha256(
                        json.dumps(entry, sort_keys=True).encode()
                    ).hexdigest()

                    if computed_hash != stored_hash:
                        return False, (
                            f"Hash mismatch in {log_file.name}:{line_num}. "
                            f"Stored={stored_hash[:16]}..., "
                            f"Computed={computed_hash[:16]}..."
                        )

                    previous_hash = stored_hash
                    total_entries += 1

        except Exception as e:
            return False, f"Error reading {log_file.name}: {e}"

    return True, f"Verified {total_entries} entries across {len(log_files)} log files"


def record_alert(message: str, is_critical: bool = True):
    """Record an alert to the alerts log."""
    alert_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_type": "INTEGRITY_COMPROMISED" if is_critical else "INTEGRITY_OK",
        "message": message
    }

    with open(ALERT_FILE, "a") as f:
        f.write(json.dumps(alert_entry) + "\n")


def main():
    logger.info("Starting AGI audit integrity verification...")

    try:
        is_valid, message = verify_audit_integrity()

        if is_valid:
            logger.info(f"INTEGRITY OK: {message}")
            record_alert(message, is_critical=False)
            return 0
        else:
            logger.error(f"INTEGRITY COMPROMISED: {message}")
            record_alert(message, is_critical=True)

            # Could add alerting here (email, webhook, etc.)
            # For now, just log to stderr for cron to capture
            print(f"CRITICAL: AGI audit log integrity compromised: {message}", file=sys.stderr)

            return 1

    except Exception as e:
        logger.exception(f"Error during verification: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
