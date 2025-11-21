#!/usr/bin/env python3
"""
Run database migration to add source attribution and conflict resolution support
"""

import sqlite3
from pathlib import Path

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

def run_migration():
    """Apply source attribution migration"""
    print(f"Running migration on {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(entities)")
        columns = [col[1] for col in cursor.fetchall()]

        # Track what we're adding
        added = []

        # Add source_session
        if 'source_session' not in columns:
            print("Adding 'source_session' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN source_session TEXT")
            added.append("source_session")
        else:
            print("✓ Column 'source_session' already exists")

        # Add source_timestamp
        if 'source_timestamp' not in columns:
            print("Adding 'source_timestamp' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN source_timestamp TIMESTAMP")
            # Set current timestamp for existing rows
            cursor.execute("UPDATE entities SET source_timestamp = CURRENT_TIMESTAMP WHERE source_timestamp IS NULL")
            added.append("source_timestamp")
        else:
            print("✓ Column 'source_timestamp' already exists")

        # Add extraction_method
        if 'extraction_method' not in columns:
            print("Adding 'extraction_method' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN extraction_method TEXT DEFAULT 'manual'")
            added.append("extraction_method")
        else:
            print("✓ Column 'extraction_method' already exists")

        # Add last_confirmed
        if 'last_confirmed' not in columns:
            print("Adding 'last_confirmed' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN last_confirmed TIMESTAMP")
            # Set current timestamp for existing rows
            cursor.execute("UPDATE entities SET last_confirmed = CURRENT_TIMESTAMP WHERE last_confirmed IS NULL")
            added.append("last_confirmed")
        else:
            print("✓ Column 'last_confirmed' already exists")

        # Add relevance_score
        if 'relevance_score' not in columns:
            print("Adding 'relevance_score' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN relevance_score REAL DEFAULT 1.0")
            added.append("relevance_score")
        else:
            print("✓ Column 'relevance_score' already exists")

        # Add parent_entity_id
        if 'parent_entity_id' not in columns:
            print("Adding 'parent_entity_id' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN parent_entity_id INTEGER")
            added.append("parent_entity_id")
        else:
            print("✓ Column 'parent_entity_id' already exists")

        # Add conflict_resolution_method
        if 'conflict_resolution_method' not in columns:
            print("Adding 'conflict_resolution_method' column...")
            cursor.execute("ALTER TABLE entities ADD COLUMN conflict_resolution_method TEXT")
            added.append("conflict_resolution_method")
        else:
            print("✓ Column 'conflict_resolution_method' already exists")

        # Create indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_source_session ON entities(source_session)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_extraction_method ON entities(extraction_method)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_relevance_score ON entities(relevance_score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_parent_entity ON entities(parent_entity_id)")
        print("✓ Indexes created successfully")

        # Create conflicts table
        print("Creating conflicts table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                conflicting_entity_id INTEGER,
                conflict_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                suggested_action TEXT,
                resolution_status TEXT DEFAULT 'pending',
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution_notes TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities (id),
                FOREIGN KEY (conflicting_entity_id) REFERENCES entities (id)
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON conflicts(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(resolution_status)")
        print("✓ Conflicts table created successfully")

        conn.commit()
        print("\n✅ Migration completed successfully")

        if added:
            print(f"\nAdded columns: {', '.join(added)}")

        # Show stats
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        print(f"Total entities in database: {total}")

        # Check for conflicts table
        cursor.execute("SELECT COUNT(*) FROM conflicts")
        conflicts = cursor.fetchone()[0]
        print(f"Total conflicts tracked: {conflicts}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
