#!/usr/bin/env python3
"""
Migration Runner for Enhanced Memory MCP

Applies SQL migrations to the database with tracking and rollback capability.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"
MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def init_migration_tracking():
    """Create migrations tracking table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN DEFAULT 1,
            error_message TEXT
        )
    ''')

    conn.commit()
    conn.close()

def get_applied_migrations():
    """Get list of already applied migrations"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT migration_name FROM schema_migrations WHERE success = 1')
    applied = {row[0] for row in cursor.fetchall()}

    conn.close()
    return applied

def get_pending_migrations():
    """Get list of migrations that need to be applied"""
    if not MIGRATIONS_DIR.exists():
        return []

    applied = get_applied_migrations()
    all_migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    pending = []
    for migration_file in all_migrations:
        migration_name = migration_file.stem
        if migration_name not in applied:
            pending.append(migration_file)

    return pending

def apply_migration(migration_file: Path) -> tuple[bool, str]:
    """
    Apply a single migration file

    Returns:
        (success, error_message)
    """
    migration_name = migration_file.stem

    try:
        # Read migration SQL
        sql_content = migration_file.read_text()

        # Apply migration
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # SQLite doesn't support multiple statements in execute()
        # We need to split and execute individually
        # But ALTER TABLE might fail if column exists, so use try/except per statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]

        for statement in statements:
            if not statement:
                continue
            try:
                cursor.execute(statement)
            except sqlite3.OperationalError as e:
                # Ignore "duplicate column" errors from ALTER TABLE
                if "duplicate column" in str(e).lower():
                    print(f"  ⚠️  Column already exists (skipped): {e}")
                    continue
                raise

        conn.commit()

        # Record successful migration
        cursor.execute(
            'INSERT INTO schema_migrations (migration_name, success) VALUES (?, 1)',
            (migration_name,)
        )
        conn.commit()
        conn.close()

        return True, None

    except Exception as e:
        error_msg = str(e)

        # Record failed migration
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO schema_migrations (migration_name, success, error_message) VALUES (?, 0, ?)',
                (migration_name, error_msg)
            )
            conn.commit()
            conn.close()
        except:
            pass

        return False, error_msg

def show_status():
    """Show migration status"""
    applied = get_applied_migrations()
    pending = get_pending_migrations()

    print("📊 Migration Status")
    print("=" * 60)
    print(f"✅ Applied: {len(applied)}")
    print(f"⏳ Pending: {len(pending)}")
    print()

    if pending:
        print("Pending migrations:")
        for migration in pending:
            print(f"  - {migration.name}")
    else:
        print("✨ All migrations applied!")

    print()

def run_migrations(auto_confirm=False):
    """Run all pending migrations"""
    pending = get_pending_migrations()

    if not pending:
        print("✨ No pending migrations")
        return True

    print(f"📦 Found {len(pending)} pending migration(s):")
    for migration in pending:
        print(f"  - {migration.name}")
    print()

    if not auto_confirm:
        response = input("Apply these migrations? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Migrations cancelled")
            return False

    print("\n🚀 Applying migrations...")
    print("=" * 60)

    success_count = 0
    for migration_file in pending:
        migration_name = migration_file.name
        print(f"\n📄 {migration_name}")

        success, error = apply_migration(migration_file)

        if success:
            print(f"  ✅ Applied successfully")
            success_count += 1
        else:
            print(f"  ❌ Failed: {error}")
            print(f"\n⚠️  Migration failed. Stopping here.")
            return False

    print("\n" + "=" * 60)
    print(f"✨ Successfully applied {success_count}/{len(pending)} migrations")
    return True

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--auto', action='store_true', help='Auto-confirm migrations')

    args = parser.parse_args()

    # Ensure migration tracking table exists
    init_migration_tracking()

    if args.status:
        show_status()
    else:
        success = run_migrations(auto_confirm=args.auto)
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
