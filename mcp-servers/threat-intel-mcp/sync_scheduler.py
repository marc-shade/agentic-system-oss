#!/usr/bin/env python3
"""
Threat Intelligence Feed Sync Scheduler
========================================

Runs as a background daemon to periodically sync threat intelligence feeds.
Can be run standalone or integrated with the main MCP server.

Schedule:
- Full sync: Every 6 hours
- Quick sync (ThreatFox only): Every hour

Usage:
    python sync_scheduler.py                    # Run daemon
    python sync_scheduler.py --once             # Sync once and exit
    python sync_scheduler.py --feed threatfox   # Sync specific feed
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from server import ThreatIntelDatabase, ThreatFeedFetcher, DB_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("threat-intel-scheduler")

# Sync intervals (in seconds)
FULL_SYNC_INTERVAL = 6 * 60 * 60    # 6 hours
QUICK_SYNC_INTERVAL = 60 * 60       # 1 hour


class ThreatSyncScheduler:
    """Manages scheduled threat feed synchronization."""

    def __init__(self):
        self.db = ThreatIntelDatabase(DB_PATH)
        self.fetcher = ThreatFeedFetcher(self.db)
        self.running = False
        self.last_full_sync = None
        self.last_quick_sync = None

    async def sync_once(self, feed: str = "all"):
        """Perform a single sync operation."""
        logger.info(f"Starting sync: {feed}")

        try:
            if feed == "all":
                results = await self.fetcher.sync_all_feeds()
                total = sum(r[0] for r in results.values())
                logger.info(f"Full sync complete: {total} indicators added")
                return results
            elif feed == "threatfox":
                return await self.fetcher.fetch_threatfox()
            elif feed == "urlhaus":
                return await self.fetcher.fetch_urlhaus()
            elif feed == "cisa_kev":
                return await self.fetcher.fetch_cisa_kev()
            elif feed == "feodo_tracker":
                return await self.fetcher.fetch_feodo_tracker()
            else:
                logger.error(f"Unknown feed: {feed}")
                return None
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return None

    async def run_scheduler(self):
        """Run the sync scheduler daemon."""
        self.running = True
        logger.info("Threat Intel Sync Scheduler started")
        logger.info(f"Full sync interval: {FULL_SYNC_INTERVAL / 3600:.1f} hours")
        logger.info(f"Quick sync interval: {QUICK_SYNC_INTERVAL / 3600:.1f} hours")

        # Initial full sync
        await self.sync_once("all")
        self.last_full_sync = datetime.now(timezone.utc)
        self.last_quick_sync = datetime.now(timezone.utc)

        while self.running:
            try:
                now = datetime.now(timezone.utc)

                # Check if full sync needed
                if self.last_full_sync is None or \
                   (now - self.last_full_sync).total_seconds() >= FULL_SYNC_INTERVAL:
                    logger.info("Starting scheduled full sync...")
                    await self.sync_once("all")
                    self.last_full_sync = now
                    self.last_quick_sync = now

                # Check if quick sync needed (ThreatFox - most frequently updated)
                elif self.last_quick_sync is None or \
                     (now - self.last_quick_sync).total_seconds() >= QUICK_SYNC_INTERVAL:
                    logger.info("Starting scheduled quick sync (ThreatFox)...")
                    await self.sync_once("threatfox")
                    self.last_quick_sync = now

                # Sleep for check interval
                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

        await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        await self.fetcher.close()
        logger.info("Scheduler stopped")

    def stop(self):
        """Signal scheduler to stop."""
        self.running = False


async def main():
    parser = argparse.ArgumentParser(description="Threat Intelligence Feed Sync Scheduler")
    parser.add_argument("--once", action="store_true", help="Sync once and exit")
    parser.add_argument("--feed", choices=["all", "threatfox", "urlhaus", "cisa_kev", "feodo_tracker"],
                        default="all", help="Specific feed to sync")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (default behavior)")

    args = parser.parse_args()

    scheduler = ThreatSyncScheduler()

    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        scheduler.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.once:
        # Single sync
        result = await scheduler.sync_once(args.feed)
        if result:
            if isinstance(result, dict):
                total = sum(r[0] for r in result.values())
                print(f"Sync complete: {total} indicators added")
            else:
                print(f"Sync complete: {result[0]} added, {result[1]} updated")
        await scheduler.cleanup()
    else:
        # Run as daemon
        await scheduler.run_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
