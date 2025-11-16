#!/usr/bin/env python3
"""
Run database migration to add always_include column
"""

import sqlite3
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

def run_migration():
    """Apply always_include migration"""
    print(f"Running migration on {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(entities)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'always_include' in columns:
            print("✓ Column 'always_include' already exists")
        else:
            print("Adding 'always_include' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN always_include BOOLEAN DEFAULT 0")
            print("✓ Column added successfully")

        # Create index
        print("Creating index...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_always_include ON entities(always_include)")
        print("✓ Index created successfully")

        conn.commit()
        print("\n✅ Migration completed successfully")

        # Show stats
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        print(f"Total entities in database: {total}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
