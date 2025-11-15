#!/usr/bin/env python3
"""
Migration script to add Git-like features to existing enhanced-memory database
Safe migration that preserves existing data
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"
BACKUP_PATH = MEMORY_DIR / f"memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def backup_database():
    """Create a backup before migration"""
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"✅ Database backed up to: {BACKUP_PATH}")
        return True
    else:
        print("⚠️  No existing database found")
        return False

def add_git_features():
    """Add new tables and columns for Git-like features"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔄 Starting migration...")

    try:
        # Add new columns to entities table if they don't exist
        cursor.execute("PRAGMA table_info(entities)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'current_version' not in columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN current_version INTEGER DEFAULT 1')
            print("  ✅ Added current_version column")

        if 'current_branch' not in columns:
            cursor.execute('ALTER TABLE entities ADD COLUMN current_branch TEXT DEFAULT "main"')
            print("  ✅ Added current_branch column")

        # Create memory_versions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                compressed_data BLOB NOT NULL,
                diff_from_previous TEXT,
                commit_message TEXT,
                author TEXT DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_current BOOLEAN DEFAULT 0,
                branch_name TEXT DEFAULT 'main',
                parent_version_id INTEGER,
                FOREIGN KEY (entity_id) REFERENCES entities (id),
                FOREIGN KEY (parent_version_id) REFERENCES memory_versions (id),
                UNIQUE(entity_id, version_number, branch_name)
            )
        ''')
        print("  ✅ Created memory_versions table")

        # Create memory_branches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                branch_name TEXT NOT NULL,
                base_version_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'system',
                description TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities (id),
                FOREIGN KEY (base_version_id) REFERENCES memory_versions (id),
                UNIQUE(entity_id, branch_name)
            )
        ''')
        print("  ✅ Created memory_branches table")

        # Create memory_conflicts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity1_id INTEGER NOT NULL,
                entity2_id INTEGER NOT NULL,
                conflict_type TEXT NOT NULL,
                similarity_score REAL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolution_notes TEXT,
                FOREIGN KEY (entity1_id) REFERENCES entities (id),
                FOREIGN KEY (entity2_id) REFERENCES entities (id)
            )
        ''')
        print("  ✅ Created memory_conflicts table")

        # Create implementation_plans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS implementation_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                steps JSON NOT NULL,
                status TEXT DEFAULT 'draft',
                progress JSON,
                entity_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id)
            )
        ''')
        print("  ✅ Created implementation_plans table")

        # Create project_handbooks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_handbooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT UNIQUE NOT NULL,
                overview TEXT,
                architecture JSON,
                conventions JSON,
                setup_instructions TEXT,
                entity_id INTEGER,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities (id)
            )
        ''')
        print("  ✅ Created project_handbooks table")

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_entity ON memory_versions(entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_branch ON memory_versions(branch_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_versions_current ON memory_versions(is_current)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON memory_conflicts(resolved)')
        print("  ✅ Created indexes")

        # Migrate existing entities to have initial versions
        cursor.execute('SELECT id, name, compressed_data FROM entities')
        entities = cursor.fetchall()

        migrated = 0
        for entity_id, name, data in entities:
            # Check if entity already has versions
            cursor.execute('SELECT COUNT(*) FROM memory_versions WHERE entity_id = ?', (entity_id,))
            if cursor.fetchone()[0] == 0:
                # Create initial version
                cursor.execute('''
                    INSERT INTO memory_versions
                    (entity_id, version_number, compressed_data, commit_message,
                     author, is_current, branch_name)
                    VALUES (?, 1, ?, ?, 'migration', 1, 'main')
                ''', (entity_id, data, f"Initial version from migration for {name}"))
                migrated += 1

        if migrated > 0:
            print(f"  ✅ Created initial versions for {migrated} existing entities")

        conn.commit()
        print("✅ Migration completed successfully!")

        # Show statistics
        cursor.execute('SELECT COUNT(*) FROM entities')
        entity_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM memory_versions')
        version_count = cursor.fetchone()[0]

        print(f"\n📊 Database Statistics:")
        print(f"  - Total entities: {entity_count}")
        print(f"  - Total versions: {version_count}")
        print(f"  - Database path: {DB_PATH}")

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_migration():
    """Verify the migration was successful"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]

        required_tables = [
            'entities', 'observations', 'relations',
            'memory_versions', 'memory_branches', 'memory_conflicts',
            'implementation_plans', 'project_handbooks'
        ]

        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"⚠️  Missing tables: {missing}")
            return False

        print("✅ All required tables present")

        # Check entities have new columns
        cursor.execute("PRAGMA table_info(entities)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'current_version' in columns and 'current_branch' in columns:
            print("✅ Entity table has Git columns")
        else:
            print("⚠️  Entity table missing Git columns")
            return False

        return True

    finally:
        conn.close()

if __name__ == "__main__":
    print("Enhanced Memory Git Migration Tool")
    print("=" * 40)

    # Check if database exists
    if DB_PATH.exists():
        print(f"Found existing database at: {DB_PATH}")
        response = input("\n⚠️  This will modify your database. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            exit(0)

        # Backup first
        if backup_database():
            # Run migration
            add_git_features()

            # Verify
            if verify_migration():
                print("\n✅ Migration verified successfully!")
                print(f"Your enhanced memory now has Git-like version control!")
                print(f"\nBackup saved at: {BACKUP_PATH}")
            else:
                print("\n⚠️  Migration verification failed")
                print(f"Restore from backup if needed: {BACKUP_PATH}")
    else:
        print("No existing database found. Creating new database with Git features...")
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        add_git_features()
        print("✅ New database created with Git features!")