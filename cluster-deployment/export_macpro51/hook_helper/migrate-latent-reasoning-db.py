#!/usr/bin/env python3
"""
Database Migration Script
Migrates existing latent-reasoning-monitor.db to include AgentDebug error taxonomy columns
Preserves all existing data
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / ".claude" / "latent-reasoning-monitor.db"
BACKUP_PATH = Path.home() / ".claude" / f"latent-reasoning-monitor-backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_database():
    """Create backup of existing database"""
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"✓ Backup created: {BACKUP_PATH}")
        return True
    else:
        print("ℹ No existing database to migrate")
        return False

def migrate_database():
    """Add error taxonomy columns to existing tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(task_executions)")
    columns = [col[1] for col in cursor.fetchall()]

    migrations_needed = []

    # Check for new columns
    new_columns = {
        'error_module': 'TEXT',
        'error_type': 'TEXT',
        'error_severity': 'TEXT',
        'error_evidence': 'TEXT',
        'is_cascade': 'BOOLEAN DEFAULT 0',
        'root_cause_step': 'INTEGER'
    }

    for col_name, col_type in new_columns.items():
        if col_name not in columns:
            migrations_needed.append((col_name, col_type))

    # Apply migrations
    if migrations_needed:
        print(f"\n📊 Migrating task_executions table...")
        for col_name, col_type in migrations_needed:
            print(f"  Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE task_executions ADD COLUMN {col_name} {col_type}")
        print(f"✓ Added {len(migrations_needed)} new columns")
    else:
        print("✓ task_executions table already up to date")

    # Create new tables if they don't exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='error_patterns'
    """)
    if not cursor.fetchone():
        print("\n📊 Creating error_patterns table...")
        cursor.execute("""
            CREATE TABLE error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_type TEXT,
                execution_method TEXT,
                error_module TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_severity TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_seen TEXT NOT NULL
            )
        """)
        print("✓ error_patterns table created")
    else:
        print("✓ error_patterns table already exists")

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='quality_metrics'
    """)
    if not cursor.fetchone():
        print("\n📊 Creating quality_metrics table...")
        cursor.execute("""
            CREATE TABLE quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent_type TEXT,
                execution_method TEXT,
                total_executions INTEGER,
                success_count INTEGER,
                error_count INTEGER,
                critical_error_count INTEGER,
                cascade_count INTEGER,
                avg_tokens INTEGER,
                success_rate REAL,
                error_rate REAL,
                critical_error_rate REAL
            )
        """)
        print("✓ quality_metrics table created")
    else:
        print("✓ quality_metrics table already exists")

    conn.commit()
    conn.close()

    return True

def verify_migration():
    """Verify migration was successful"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check task_executions columns
    cursor.execute("PRAGMA table_info(task_executions)")
    columns = [col[1] for col in cursor.fetchall()]

    required_columns = [
        'error_module', 'error_type', 'error_severity',
        'error_evidence', 'is_cascade', 'root_cause_step'
    ]

    missing = [col for col in required_columns if col not in columns]

    if missing:
        print(f"\n❌ Migration incomplete. Missing columns: {missing}")
        return False

    # Check new tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('error_patterns', 'quality_metrics')
    """)
    tables = [row[0] for row in cursor.fetchall()]

    if len(tables) != 2:
        print(f"\n❌ Migration incomplete. Missing tables")
        return False

    # Count existing records
    cursor.execute("SELECT COUNT(*) FROM task_executions")
    record_count = cursor.fetchone()[0]

    conn.close()

    print(f"\n✅ Migration successful!")
    print(f"   • All error taxonomy columns added")
    print(f"   • error_patterns table created")
    print(f"   • quality_metrics table created")
    print(f"   • {record_count} existing records preserved")

    return True

def main():
    print("=" * 70)
    print("  LATENT REASONING DATABASE MIGRATION")
    print("  Adding AgentDebug Error Taxonomy Support")
    print("=" * 70 + "\n")

    # Step 1: Backup
    print("Step 1: Creating backup...")
    has_existing = backup_database()

    # Step 2: Migrate
    print("\nStep 2: Applying migrations...")
    migrate_database()

    # Step 3: Verify
    print("\nStep 3: Verifying migration...")
    success = verify_migration()

    if success:
        print("\n" + "=" * 70)
        print("  MIGRATION COMPLETE")
        print("=" * 70)
        if has_existing:
            print(f"\n  Original database backed up to:")
            print(f"  {BACKUP_PATH}")
        print(f"\n  Enhanced database ready at:")
        print(f"  {DB_PATH}")
        print("\n  Next steps:")
        print("  1. Replace latent-reasoning-monitor.py with enhanced version")
        print("  2. Test with: python3 /home/marc/.claude/hooks/latent-reasoning-monitor-enhanced.py")
        print("  3. View dashboard: /home/marc/.claude/latent-reasoning-dashboard")
        print("\n" + "=" * 70 + "\n")
        return 0
    else:
        print("\n❌ Migration failed. Original database preserved.")
        return 1

if __name__ == "__main__":
    exit(main())
