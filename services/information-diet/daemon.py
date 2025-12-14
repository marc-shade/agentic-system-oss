#!/usr/bin/env python3
"""
Information Diet Daemon - Unified Service Manager
Runs all information diet services in a single process.

Usage:
    python3 daemon.py                  # Start all services
    python3 daemon.py --no-webhook     # Skip webhook server
    python3 daemon.py --config FILE    # Custom config
"""

import asyncio
import json
import os
import platform
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
import logging


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent


AGENTIC_PATH = _get_storage_base()

# Setup logging
log_dir = AGENTIC_PATH / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "information-diet.log")
    ]
)
logger = logging.getLogger("information-diet")

# Import services
from rss_ingestion import process_all_feeds
from research_paper_monitor import check_all_topics
from youtube_channel_monitor import check_all_channels
from scheduled_consolidation import consolidate
from proactive_digest import generate_digest
CONFIG_FILE = AGENTIC_PATH / "config" / "information-diet-daemon.json"

DEFAULT_CONFIG = {
    "rss": {
        "enabled": True,
        "interval_minutes": 60
    },
    "research": {
        "enabled": True,
        "interval_hours": 6
    },
    "youtube": {
        "enabled": True,
        "interval_hours": 12
    },
    "consolidation": {
        "enabled": True,
        "interval_hours": 6,
        "full_interval_hours": 24
    },
    "digest": {
        "enabled": True,
        "daily_hour": 8,
        "weekly_day": 0  # Monday
    },
    "webhook": {
        "enabled": True,
        "port": 8110
    }
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    # Save default
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG


class InformationDietDaemon:
    def __init__(self, config: dict, run_webhook: bool = True):
        self.config = config
        self.run_webhook = run_webhook
        self.running = True
        self.tasks = []

    async def rss_loop(self):
        """RSS feed ingestion loop."""
        cfg = self.config.get("rss", {})
        if not cfg.get("enabled", True):
            return

        interval = cfg.get("interval_minutes", 60) * 60
        logger.info(f"RSS loop starting (interval={interval/60}m)")

        while self.running:
            try:
                await process_all_feeds()
            except Exception as e:
                logger.error(f"RSS error: {e}")
            await asyncio.sleep(interval)

    async def research_loop(self):
        """Research paper monitoring loop."""
        cfg = self.config.get("research", {})
        if not cfg.get("enabled", True):
            return

        interval = cfg.get("interval_hours", 6) * 3600
        logger.info(f"Research loop starting (interval={interval/3600}h)")

        while self.running:
            try:
                await check_all_topics()
            except Exception as e:
                logger.error(f"Research error: {e}")
            await asyncio.sleep(interval)

    async def youtube_loop(self):
        """YouTube channel monitoring loop."""
        cfg = self.config.get("youtube", {})
        if not cfg.get("enabled", True):
            return

        interval = cfg.get("interval_hours", 12) * 3600
        logger.info(f"YouTube loop starting (interval={interval/3600}h)")

        while self.running:
            try:
                await check_all_channels()
            except Exception as e:
                logger.error(f"YouTube error: {e}")
            await asyncio.sleep(interval)

    async def consolidation_loop(self):
        """Memory consolidation loop."""
        cfg = self.config.get("consolidation", {})
        if not cfg.get("enabled", True):
            return

        interval = cfg.get("interval_hours", 6) * 3600
        full_interval = cfg.get("full_interval_hours", 24) * 3600
        logger.info(f"Consolidation loop starting (interval={interval/3600}h, full={full_interval/3600}h)")

        last_full = datetime.now()

        while self.running:
            try:
                hours_since_full = (datetime.now() - last_full).total_seconds()
                full = hours_since_full >= full_interval
                await consolidate(full=full)
                if full:
                    last_full = datetime.now()
            except Exception as e:
                logger.error(f"Consolidation error: {e}")
            await asyncio.sleep(interval)

    async def digest_loop(self):
        """Digest generation loop."""
        cfg = self.config.get("digest", {})
        if not cfg.get("enabled", True):
            return

        daily_hour = cfg.get("daily_hour", 8)
        weekly_day = cfg.get("weekly_day", 0)
        logger.info(f"Digest loop starting (daily at {daily_hour}:00)")

        while self.running:
            now = datetime.now()
            if now.hour == daily_hour and now.minute < 5:
                try:
                    await generate_digest("daily", speak=True)
                    if now.weekday() == weekly_day:
                        await generate_digest("weekly", speak=False)
                except Exception as e:
                    logger.error(f"Digest error: {e}")
            await asyncio.sleep(300)

    def start_webhook(self):
        """Start webhook server in thread."""
        cfg = self.config.get("webhook", {})
        if not cfg.get("enabled", True) or not self.run_webhook:
            return

        from webhook_receiver import app
        port = cfg.get("port", 8110)
        logger.info(f"Starting webhook server on port {port}")

        def run():
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    async def run(self):
        """Run all services."""
        logger.info("Information Diet Daemon starting...")

        # Start webhook in thread
        self.start_webhook()

        # Start async loops
        self.tasks = [
            asyncio.create_task(self.rss_loop()),
            asyncio.create_task(self.research_loop()),
            asyncio.create_task(self.youtube_loop()),
            asyncio.create_task(self.consolidation_loop()),
            asyncio.create_task(self.digest_loop()),
        ]

        # Wait for shutdown
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Daemon shutting down...")

    def stop(self):
        """Stop all services."""
        self.running = False
        for task in self.tasks:
            task.cancel()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Information Diet Daemon")
    parser.add_argument("--no-webhook", action="store_true", help="Don't start webhook server")
    parser.add_argument("--config", help="Custom config file")
    args = parser.parse_args()

    config = load_config()
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    daemon = InformationDietDaemon(config, run_webhook=not args.no_webhook)

    # Handle signals
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
