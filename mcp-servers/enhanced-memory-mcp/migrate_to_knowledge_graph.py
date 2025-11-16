#!/usr/bin/env python3
"""
Migration Script: Enhanced Memory → Knowledge Graph
Migrates existing memory database to knowledge graph architecture

Inspired by: "You're Doing Memory All Wrong" - Zapai
Adds: Temporal edges, causal reasoning, bi-directional traversal, explicit ontology
"""

import sqlite3
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("migration")


class KnowledgeGraphMigration:
    """
    Handles migration from simple memory to knowledge graph
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.backup_path = db_path.parent / f"{db_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    def run(self, dry_run: bool = False):
        """
        Execute migration

        Args:
            dry_run: If True, only show what would be done
        """
        logger.info("="*60)
        logger.info("Knowledge Graph Migration Starting")
        logger.info("="*60)

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")

        # Step 1: Backup database
        self._backup_database(dry_run)

        # Step 2: Check current schema
        stats = self._analyze_current_schema()
        logger.info(f"\nCurrent Database Statistics:")
        logger.info(f"  Entities: {stats['entities']}")
        logger.info(f"  Relations: {stats['relations']}")
        logger.info(f"  Observations: {stats['observations']}")

        # Step 3: Execute SQL migration
        self._execute_schema_migration(dry_run)

        # Step 4: Validate migration
        self._validate_migration()

        # Step 5: Generate migration report
        self._generate_report()

        logger.info("\n" + "="*60)
        logger.info("Migration Complete!")
        logger.info("="*60)

    def _backup_database(self, dry_run: bool):
        """Create backup of database"""
        logger.info(f"\nStep 1: Creating backup...")

        if dry_run:
            logger.info(f"  Would create backup at: {self.backup_path}")
            return

        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"  ✓ Backup created: {self.backup_path}")
        except Exception as e:
            logger.error(f"  ✗ Backup failed: {e}")
            sys.exit(1)

    def _analyze_current_schema(self) -> dict:
        """Analyze current database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Count entities
        cursor.execute('SELECT COUNT(*) FROM entities')
        stats['entities'] = cursor.fetchone()[0]

        # Count relations
        try:
            cursor.execute('SELECT COUNT(*) FROM relations')
            stats['relations'] = cursor.fetchone()[0]
        except:
            stats['relations'] = 0

        # Count observations
        try:
            cursor.execute('SELECT COUNT(*) FROM observations')
            stats['observations'] = cursor.fetchone()[0]
        except:
            stats['observations'] = 0

        # Check if migration needed
        cursor.execute("PRAGMA table_info(relations)")
        columns = [row[1] for row in cursor.fetchall()]

        stats['has_temporal'] = 'created_at' in columns and 'valid_from' in columns
        stats['has_causal'] = 'is_causal' in columns
        stats['has_strength'] = 'strength' in columns
        stats['needs_migration'] = not (stats['has_temporal'] and stats['has_causal'] and stats['has_strength'])

        conn.close()
        return stats

    def _execute_schema_migration(self, dry_run: bool):
        """Execute SQL schema migration"""
        logger.info(f"\nStep 3: Executing schema migration...")

        # Read migration SQL
        sql_path = Path(__file__).parent / "schema_migration.sql"
        if not sql_path.exists():
            logger.error(f"  ✗ Migration SQL not found: {sql_path}")
            sys.exit(1)

        with open(sql_path, 'r') as f:
            migration_sql = f.read()

        if dry_run:
            logger.info(f"  Would execute migration from: {sql_path}")
            logger.info(f"  SQL statements: {len([s for s in migration_sql.split(';') if s.strip()])}")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Execute migration (SQLite executescript for multiple statements)
            cursor.executescript(migration_sql)

            conn.commit()
            conn.close()

            logger.info("  ✓ Schema migration executed successfully")

        except Exception as e:
            logger.error(f"  ✗ Migration failed: {e}")
            logger.error(f"  Restoring from backup...")

            # Restore backup
            if self.backup_path.exists():
                import shutil
                shutil.copy2(self.backup_path, self.db_path)
                logger.info(f"  ✓ Backup restored")

            sys.exit(1)

    def _validate_migration(self):
        """Validate migration was successful"""
        logger.info(f"\nStep 4: Validating migration...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check relations table has new columns
        cursor.execute("PRAGMA table_info(relations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = {
            'created_at': 'TIMESTAMP',
            'updated_at': 'TIMESTAMP',
            'strength': 'REAL',
            'confidence': 'REAL',
            'is_causal': 'BOOLEAN',
            'causal_strength': 'REAL',
            'bidirectional': 'BOOLEAN'
        }

        missing = []
        for col, type_expected in required_columns.items():
            if col not in columns:
                missing.append(col)

        if missing:
            logger.error(f"  ✗ Missing columns: {missing}")
            conn.close()
            sys.exit(1)

        # Check views were created
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='view' AND name IN ('current_relations', 'causal_relationships')
        """)
        views = [row[0] for row in cursor.fetchall()]

        if len(views) != 2:
            logger.warning(f"  ⚠ Only {len(views)}/2 views created")
        else:
            logger.info(f"  ✓ All views created")

        # Check indexes
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_relations_%'
        """)
        index_count = cursor.fetchone()[0]

        logger.info(f"  ✓ {index_count} indexes created")

        # Check data integrity
        cursor.execute('SELECT COUNT(*) FROM relations')
        relation_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations WHERE strength IS NOT NULL')
        strength_count = cursor.fetchone()[0]

        if relation_count > 0 and strength_count == relation_count:
            logger.info(f"  ✓ All {relation_count} relations have strength values")
        elif relation_count > 0:
            logger.warning(f"  ⚠ {relation_count - strength_count} relations missing strength")

        conn.close()
        logger.info("  ✓ Migration validated successfully")

    def _generate_report(self):
        """Generate migration report"""
        logger.info(f"\nStep 5: Generating report...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        report = {
            'migration_date': datetime.now().isoformat(),
            'database_path': str(self.db_path),
            'backup_path': str(self.backup_path),
            'statistics': {}
        }

        # Entity statistics
        cursor.execute('SELECT COUNT(*), entity_type FROM entities GROUP BY entity_type')
        report['statistics']['entities_by_type'] = {row[1]: row[0] for row in cursor.fetchall()}

        # Relationship statistics
        cursor.execute('SELECT COUNT(*) FROM relations')
        report['statistics']['total_relations'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations WHERE is_causal = 1')
        report['statistics']['causal_relations'] = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations WHERE bidirectional = 1')
        report['statistics']['bidirectional_relations'] = cursor.fetchone()[0]

        cursor.execute('SELECT AVG(strength) FROM relations WHERE strength IS NOT NULL')
        avg_strength = cursor.fetchone()[0]
        report['statistics']['avg_relationship_strength'] = round(avg_strength, 3) if avg_strength else 0

        # Temporal statistics
        cursor.execute('''
            SELECT COUNT(*) FROM relations
            WHERE valid_from IS NOT NULL OR valid_until IS NOT NULL
        ''')
        report['statistics']['temporal_relations'] = cursor.fetchone()[0]

        conn.close()

        # Write report
        report_path = self.db_path.parent / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"  ✓ Report saved: {report_path}")

        # Print summary
        logger.info(f"\nMigration Summary:")
        logger.info(f"  Total entities: {sum(report['statistics']['entities_by_type'].values())}")
        logger.info(f"  Total relations: {report['statistics']['total_relations']}")
        logger.info(f"  Causal relations: {report['statistics']['causal_relations']}")
        logger.info(f"  Bidirectional relations: {report['statistics']['bidirectional_relations']}")
        logger.info(f"  Avg relationship strength: {report['statistics']['avg_relationship_strength']}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate Enhanced Memory database to Knowledge Graph architecture'
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Path.home() / ".claude" / "enhanced_memories" / "memory.db",
        help='Path to memory database (default: ~/.claude/enhanced_memories/memory.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    # Check database exists
    if not args.db_path.exists():
        logger.error(f"Database not found: {args.db_path}")
        sys.exit(1)

    # Confirmation
    if not args.dry_run and not args.force:
        print(f"\nThis will migrate: {args.db_path}")
        print(f"A backup will be created before migration.")
        response = input("\nProceed with migration? [y/N]: ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)

    # Run migration
    migration = KnowledgeGraphMigration(args.db_path)
    migration.run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
