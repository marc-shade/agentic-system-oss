#!/usr/bin/env python3
"""
Memory Replication Service
Ensures AGI memories survive node failures

Responsibilities:
- Replicate shared_memories.db every 5 minutes
- Verify integrity after replication
- Maintain backup history (30 days)
- Alert on replication failures
- Provide recovery capabilities
"""

import sys
import time
import shutil
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import json

# Add cluster deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'cluster-deployment'))
from toon_config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/var/log/memory-replication.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MemoryReplicator:
    """Replicate and protect cluster memory"""

    def __init__(self, config_path: str = None):
        """Initialize replicator with configuration"""
        config_path = config_path or str(Path.home() / '.claude' / 'node-config')
        self.config = load_config(config_path)

        self.node_id = self.config.get('node_id', 'bpi-sentinel')

        # Service configuration
        service_config = self.config.get('services', {}).get('memory_replication', {})
        self.sync_interval = service_config.get('sync_interval_minutes', 5) * 60
        self.retention_days = service_config.get('backup_retention_days', 30)
        self.verify_integrity = service_config.get('verify_integrity', True)

        # Paths
        agentic_root = Path.home() / 'agentic-system'
        self.source_db = agentic_root / 'databases' / 'cluster' / 'shared_memories.db'
        self.replication_target = Path(self.config.get('cluster', {}).get('replication_target', '/mnt/sentinel-data/cluster-backup'))
        self.replication_target.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.total_replications = 0
        self.failed_replications = 0
        self.last_successful_replication: Optional[datetime] = None
        self.last_hash: Optional[str] = None

        logger.info(f"Memory Replicator initialized: {self.node_id}")
        logger.info(f"Source: {self.source_db}")
        logger.info(f"Target: {self.replication_target}")

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_database_integrity(self, db_path: Path) -> bool:
        """Verify SQLite database integrity"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result[0] == 'ok':
                return True
            else:
                logger.error(f"Database integrity check failed: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Failed to verify database integrity: {e}")
            return False

    def get_database_stats(self, db_path: Path) -> dict:
        """Get database statistics"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get entity count
            cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = cursor.fetchone()[0]

            # Get database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]

            # Get last modification
            cursor.execute("SELECT MAX(updated_at) FROM entities")
            last_updated = cursor.fetchone()[0]

            conn.close()

            return {
                'entity_count': entity_count,
                'size_bytes': db_size,
                'size_mb': round(db_size / 1024 / 1024, 2),
                'last_updated': last_updated
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def create_replication(self) -> bool:
        """Create a replication of the cluster memory database"""
        try:
            # Check if source exists
            if not self.source_db.exists():
                logger.error(f"Source database not found: {self.source_db}")
                return False

            # Get source hash
            source_hash = self.compute_file_hash(self.source_db)

            # Check if database has changed
            if source_hash == self.last_hash:
                logger.debug("Database unchanged, skipping replication")
                return True

            # Get source stats
            source_stats = self.get_database_stats(self.source_db)
            logger.info(f"Replicating database: {source_stats['entity_count']} entities, {source_stats['size_mb']} MB")

            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"shared_memories_{timestamp}.db"
            backup_path = self.replication_target / backup_name

            # Copy database
            shutil.copy2(self.source_db, backup_path)
            logger.info(f"✓ Copied to: {backup_path}")

            # Verify integrity if enabled
            if self.verify_integrity:
                if not self.verify_database_integrity(backup_path):
                    logger.error("Backup integrity check failed, removing corrupted backup")
                    backup_path.unlink()
                    return False
                logger.info("✓ Integrity verified")

            # Verify hash matches
            backup_hash = self.compute_file_hash(backup_path)
            if backup_hash != source_hash:
                logger.error("Hash mismatch after copy, removing corrupted backup")
                backup_path.unlink()
                return False
            logger.info("✓ Hash verified")

            # Create symlink to latest
            latest_link = self.replication_target / 'shared_memories_latest.db'
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(backup_name)

            # Update metrics
            self.total_replications += 1
            self.last_successful_replication = datetime.now()
            self.last_hash = source_hash

            # Log replication to cluster memory
            self.log_replication_event(backup_path, source_stats)

            logger.info(f"✓ Replication complete: {backup_name}")
            return True

        except Exception as e:
            logger.error(f"Replication failed: {e}", exc_info=True)
            self.failed_replications += 1
            return False

    def log_replication_event(self, backup_path: Path, stats: dict):
        """Log replication event to cluster memory"""
        try:
            # Log to the SOURCE database (so other nodes see it)
            conn = sqlite3.connect(str(self.source_db))
            cursor = conn.cursor()

            event = {
                'type': 'memory_replication',
                'timestamp': datetime.now().isoformat(),
                'backup_path': str(backup_path),
                'stats': stats,
                'sentinel_node': self.node_id,
                'total_replications': self.total_replications,
                'failed_replications': self.failed_replications
            }

            cursor.execute("""
                INSERT INTO entities (name, entity_type, observations, node_id, created_at, updated_at)
                VALUES (?, 'system_event', ?, ?, datetime('now'), datetime('now'))
            """, (
                f"replication_{int(time.time())}",
                json.dumps([json.dumps(event)]),
                self.node_id
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log replication event: {e}")

    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            removed_count = 0

            for backup_file in self.replication_target.glob("shared_memories_*.db"):
                # Skip the latest symlink
                if backup_file.is_symlink():
                    continue

                # Parse timestamp from filename
                try:
                    timestamp_str = backup_file.stem.split('_', 2)[2]
                    file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                    if file_time < cutoff:
                        backup_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed old backup: {backup_file.name}")
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp from {backup_file.name}: {e}")

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old backups (retention: {self.retention_days} days)")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

    def get_backup_list(self) -> list:
        """Get list of available backups"""
        backups = []
        for backup_file in sorted(self.replication_target.glob("shared_memories_*.db"), reverse=True):
            if backup_file.is_symlink():
                continue

            try:
                timestamp_str = backup_file.stem.split('_', 2)[2]
                file_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                stats = self.get_database_stats(backup_file)

                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'timestamp': file_time.isoformat(),
                    'age_hours': (datetime.now() - file_time).total_seconds() / 3600,
                    'size_mb': stats.get('size_mb', 0),
                    'entity_count': stats.get('entity_count', 0)
                })
            except Exception as e:
                logger.warning(f"Failed to parse backup {backup_file.name}: {e}")

        return backups

    def print_status(self):
        """Print replication status"""
        logger.info("=" * 60)
        logger.info("MEMORY REPLICATION STATUS")
        logger.info("=" * 60)
        logger.info(f"Node: {self.node_id}")
        logger.info(f"Total replications: {self.total_replications}")
        logger.info(f"Failed replications: {self.failed_replications}")
        logger.info(f"Success rate: {((self.total_replications - self.failed_replications) / max(self.total_replications, 1) * 100):.1f}%")

        if self.last_successful_replication:
            age = datetime.now() - self.last_successful_replication
            logger.info(f"Last successful: {age.total_seconds() / 60:.1f} minutes ago")

        backups = self.get_backup_list()
        logger.info(f"Available backups: {len(backups)}")

        if backups:
            latest = backups[0]
            logger.info(f"Latest backup: {latest['filename']} ({latest['entity_count']} entities, {latest['size_mb']} MB)")

        logger.info("=" * 60)

    def run_replication_cycle(self):
        """Run one complete replication cycle"""
        logger.info("Starting replication cycle...")

        # Create replication
        success = self.create_replication()

        # Cleanup old backups
        if success:
            self.cleanup_old_backups()

        # Print status periodically
        if self.total_replications % 12 == 0:  # Every hour at 5-min intervals
            self.print_status()

    def run(self):
        """Main replication loop"""
        logger.info(f"🔄 Memory Replication Service starting (interval: {self.sync_interval / 60:.0f} minutes)")

        # Do initial replication immediately
        self.run_replication_cycle()

        try:
            while True:
                time.sleep(self.sync_interval)

                try:
                    self.run_replication_cycle()
                except Exception as e:
                    logger.error(f"Error in replication cycle: {e}", exc_info=True)
                    self.failed_replications += 1

        except KeyboardInterrupt:
            logger.info("Replication service shutting down gracefully...")
            self.print_status()
        except Exception as e:
            logger.error(f"Fatal error in replication service: {e}", exc_info=True)
            raise


def main():
    """Entry point"""
    replicator = MemoryReplicator()
    replicator.run()


if __name__ == '__main__':
    main()
