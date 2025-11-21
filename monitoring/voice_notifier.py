#!/usr/bin/env python3
"""
Voice Notification Engine for Deep Learning Cycle
Week 5 Phase 7: Spoken Cycle Summaries and Alerts

This module provides voice notifications for cycle completion,
pattern detection, and critical findings using voice-mode MCP.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Configuration
VOICE_NOTIFICATIONS_DB = Path("/mnt/agentic-system/databases/voice_notifications.db")

# Source databases
PATTERNS_DB = Path("/mnt/agentic-system/databases/patterns.db")
OPTIMIZATIONS_DB = Path("/mnt/agentic-system/databases/optimizations.db")
SKILL_ENHANCEMENTS_DB = Path("/mnt/agentic-system/databases/skill_enhancements.db")
AGENT_REFINEMENTS_DB = Path("/mnt/agentic-system/databases/agent_refinements.db")
CONFIG_TUNING_DB = Path("/mnt/agentic-system/databases/config_tuning.db")
LEARNING_STORAGE_DB = Path("/mnt/agentic-system/databases/learning_storage.db")

class NotificationType(Enum):
    """Types of voice notifications"""
    CYCLE_COMPLETE = "cycle_complete"
    PATTERN_DETECTED = "pattern_detected"
    OPTIMIZATION_APPLIED = "optimization_applied"
    SKILL_ENHANCED = "skill_enhanced"
    AGENT_REFINED = "agent_refined"
    CONFIG_TUNED = "config_tuned"
    KNOWLEDGE_MILESTONE = "knowledge_milestone"
    CRITICAL_FINDING = "critical_finding"

class NotificationPriority(Enum):
    """Priority levels for notifications"""
    LOW = "low"           # Informational, batch with others
    NORMAL = "normal"     # Standard cycle summary
    HIGH = "high"         # Important findings
    CRITICAL = "critical" # Immediate attention required

@dataclass
class VoiceNotification:
    """Represents a voice notification"""
    notification_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    message: str
    details: Dict[str, Any]
    created_at: datetime
    spoken_at: Optional[datetime]
    should_speak: bool

class VoiceNotificationDatabase:
    """Manages voice notification storage and history"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize voice notifications schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_notifications (
                notification_id TEXT PRIMARY KEY,
                notification_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                spoken_at TIMESTAMP,
                should_speak BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notification_priority ON voice_notifications(priority)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notification_spoken ON voice_notifications(spoken_at)
        """)

        conn.commit()
        conn.close()

    def store_notification(self, notification: VoiceNotification):
        """Store a voice notification"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO voice_notifications
            (notification_id, notification_type, priority, message, details,
             created_at, spoken_at, should_speak)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification.notification_id, notification.notification_type.value,
            notification.priority.value, notification.message,
            json.dumps(notification.details), notification.created_at.isoformat(),
            notification.spoken_at.isoformat() if notification.spoken_at else None,
            notification.should_speak
        ))

        conn.commit()
        conn.close()

    def get_pending_notifications(self, priority: Optional[NotificationPriority] = None) -> List[VoiceNotification]:
        """Get notifications that haven't been spoken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if priority:
            cursor.execute("""
                SELECT notification_id, notification_type, priority, message, details,
                       created_at, spoken_at, should_speak
                FROM voice_notifications
                WHERE spoken_at IS NULL AND should_speak = 1 AND priority = ?
                ORDER BY created_at DESC
            """, (priority.value,))
        else:
            cursor.execute("""
                SELECT notification_id, notification_type, priority, message, details,
                       created_at, spoken_at, should_speak
                FROM voice_notifications
                WHERE spoken_at IS NULL AND should_speak = 1
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    created_at DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        return [VoiceNotification(
            notification_id=r[0], notification_type=NotificationType(r[1]),
            priority=NotificationPriority(r[2]), message=r[3],
            details=json.loads(r[4]), created_at=datetime.fromisoformat(r[5]),
            spoken_at=datetime.fromisoformat(r[6]) if r[6] else None,
            should_speak=bool(r[7])
        ) for r in rows]

    def mark_spoken(self, notification_id: str):
        """Mark a notification as spoken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE voice_notifications
            SET spoken_at = ?
            WHERE notification_id = ?
        """, (datetime.now().isoformat(), notification_id))

        conn.commit()
        conn.close()

class CycleSummarizer:
    """Generates spoken summaries of cycle results"""

    def __init__(self, notification_db: VoiceNotificationDatabase):
        self.notification_db = notification_db

    def generate_cycle_summary(self, cycle_results: Dict[str, Any]) -> str:
        """Generate spoken summary from cycle results"""
        parts = []

        # Overall summary
        phases_succeeded = sum(1 for phase_result in cycle_results.values()
                              if isinstance(phase_result, dict) and phase_result.get('status') == 'success')
        total_phases = len([k for k in cycle_results.keys() if k.startswith('phase')])

        parts.append(f"Deep learning cycle complete. {phases_succeeded} of {total_phases} phases successful.")

        # Phase-specific highlights
        if 'phase1' in cycle_results and cycle_results['phase1'].get('status') == 'success':
            p1 = cycle_results['phase1']
            if p1.get('patterns', 0) > 0:
                parts.append(f"Detected {p1['patterns']} new patterns.")

        if 'phase2' in cycle_results and cycle_results['phase2'].get('status') == 'success':
            p2 = cycle_results['phase2']
            if p2.get('applied', 0) > 0:
                parts.append(f"Applied {p2['applied']} code optimizations.")

        if 'phase3' in cycle_results and cycle_results['phase3'].get('status') == 'success':
            p3 = cycle_results['phase3']
            if p3.get('applied', 0) > 0:
                parts.append(f"Enhanced {p3['applied']} skills.")

        if 'phase4' in cycle_results and cycle_results['phase4'].get('status') == 'success':
            p4 = cycle_results['phase4']
            if p4.get('applied', 0) > 0:
                parts.append(f"Refined {p4['applied']} agents.")

        if 'phase5' in cycle_results and cycle_results['phase5'].get('status') == 'success':
            p5 = cycle_results['phase5']
            if p5.get('applied', 0) > 0:
                parts.append(f"Tuned {p5['applied']} configurations.")

        if 'phase6' in cycle_results and cycle_results['phase6'].get('status') == 'success':
            p6 = cycle_results['phase6']
            if p6.get('entities_harvested', 0) > 0:
                parts.append(f"Harvested {p6['entities_harvested']} knowledge entities.")

        return " ".join(parts)

    def create_cycle_notification(self, cycle_results: Dict[str, Any], cycle_number: int):
        """Create cycle completion notification"""
        summary = self.generate_cycle_summary(cycle_results)

        notification = VoiceNotification(
            notification_id=f"cycle_{cycle_number}_{datetime.now().isoformat()}",
            notification_type=NotificationType.CYCLE_COMPLETE,
            priority=NotificationPriority.NORMAL,
            message=summary,
            details=cycle_results,
            created_at=datetime.now(),
            spoken_at=None,
            should_speak=True
        )

        self.notification_db.store_notification(notification)

class PatternAlerter:
    """Generates alerts for high-confidence pattern detection"""

    def __init__(self, notification_db: VoiceNotificationDatabase):
        self.notification_db = notification_db

    def check_critical_patterns(self) -> List[VoiceNotification]:
        """Check for critical patterns requiring immediate notification"""
        if not PATTERNS_DB.exists():
            return []

        conn = sqlite3.connect(PATTERNS_DB)
        cursor = conn.cursor()

        # Find high-confidence patterns detected in last hour
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        cursor.execute("""
            SELECT pattern_id, pattern_type, description, confidence, occurrences
            FROM patterns
            WHERE confidence >= 0.85 AND detected_at >= ?
            ORDER BY confidence DESC
            LIMIT 5
        """, (one_hour_ago,))

        rows = cursor.fetchall()
        conn.close()

        notifications = []
        for r in rows:
            message = f"Critical pattern detected: {r[1]}. Confidence {r[3]:.0%}. Occurred {r[4]} times."

            notification = VoiceNotification(
                notification_id=f"pattern_{r[0]}_{datetime.now().isoformat()}",
                notification_type=NotificationType.PATTERN_DETECTED,
                priority=NotificationPriority.HIGH,
                message=message,
                details={
                    "pattern_id": r[0],
                    "pattern_type": r[1],
                    "description": r[2],
                    "confidence": r[3],
                    "occurrences": r[4]
                },
                created_at=datetime.now(),
                spoken_at=None,
                should_speak=True
            )

            notifications.append(notification)
            self.notification_db.store_notification(notification)

        return notifications

class FindingsReporter:
    """Reports critical findings from all phases"""

    def __init__(self, notification_db: VoiceNotificationDatabase):
        self.notification_db = notification_db

    def check_critical_findings(self) -> List[VoiceNotification]:
        """Check for critical findings across all phases"""
        notifications = []

        # Check for very high effectiveness learnings
        if LEARNING_STORAGE_DB.exists():
            conn = sqlite3.connect(LEARNING_STORAGE_DB)
            cursor = conn.cursor()

            one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()

            cursor.execute("""
                SELECT entity_id, entity_type, title, effectiveness, confidence
                FROM learning_entities
                WHERE effectiveness >= 0.90 AND created_at >= ?
                ORDER BY effectiveness DESC
                LIMIT 3
            """, (one_day_ago,))

            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                message = f"Exceptional finding: {r[2]} achieved {r[3]:.0%} effectiveness."

                notification = VoiceNotification(
                    notification_id=f"finding_{r[0]}_{datetime.now().isoformat()}",
                    notification_type=NotificationType.CRITICAL_FINDING,
                    priority=NotificationPriority.HIGH,
                    message=message,
                    details={
                        "entity_id": r[0],
                        "entity_type": r[1],
                        "title": r[2],
                        "effectiveness": r[3],
                        "confidence": r[4]
                    },
                    created_at=datetime.now(),
                    spoken_at=None,
                    should_speak=True
                )

                notifications.append(notification)
                self.notification_db.store_notification(notification)

        return notifications

class VoiceNotifier:
    """Main voice notification orchestrator"""

    def __init__(self, db: VoiceNotificationDatabase):
        self.db = db
        self.summarizer = CycleSummarizer(db)
        self.alerter = PatternAlerter(db)
        self.reporter = FindingsReporter(db)

    def get_notification_script(self) -> str:
        """Generate spoken script from pending notifications"""
        pending = self.db.get_pending_notifications()

        if not pending:
            return ""

        # Group by priority
        critical = [n for n in pending if n.priority == NotificationPriority.CRITICAL]
        high = [n for n in pending if n.priority == NotificationPriority.HIGH]
        normal = [n for n in pending if n.priority == NotificationPriority.NORMAL]
        low = [n for n in pending if n.priority == NotificationPriority.LOW]

        parts = []

        if critical:
            parts.append("Critical alerts:")
            for n in critical:
                parts.append(n.message)

        if high:
            parts.append("Important findings:")
            for n in high:
                parts.append(n.message)

        if normal:
            for n in normal:
                parts.append(n.message)

        if low:
            # Batch low priority
            parts.append(f"Additionally, {len(low)} routine updates.")

        return " ".join(parts)

def main():
    """Main voice notification runner"""
    print("="*60)
    print("Voice Notification Engine - Week 5 Phase 7")
    print("="*60)
    print()

    db = VoiceNotificationDatabase(VOICE_NOTIFICATIONS_DB)
    print(f"✓ Voice notifications database initialized: {VOICE_NOTIFICATIONS_DB}")

    notifier = VoiceNotifier(db)
    print(f"✓ Voice notifier initialized")
    print()

    # Check for critical patterns
    print("Checking for critical patterns...")
    pattern_alerts = notifier.alerter.check_critical_patterns()
    print(f"  Found {len(pattern_alerts)} pattern alerts")

    # Check for critical findings
    print("Checking for critical findings...")
    findings = notifier.reporter.check_critical_findings()
    print(f"  Found {len(findings)} critical findings")

    # Get pending notifications
    print()
    print("Pending notifications:")
    pending = db.get_pending_notifications()
    if pending:
        for n in pending:
            print(f"  [{n.priority.value.upper()}] {n.message}")
    else:
        print("  None")

    # Generate script
    print()
    print("Voice notification script:")
    script = notifier.get_notification_script()
    if script:
        print(f"  \"{script}\"")
    else:
        print("  (No pending notifications)")

    print()
    print("="*60)
    print("VOICE NOTIFICATION COMPLETE")
    print("="*60)
    print(f"Pattern alerts: {len(pattern_alerts)}")
    print(f"Critical findings: {len(findings)}")
    print(f"Pending notifications: {len(pending)}")
    print(f"Database: {VOICE_NOTIFICATIONS_DB}")
    print()

if __name__ == "__main__":
    main()
