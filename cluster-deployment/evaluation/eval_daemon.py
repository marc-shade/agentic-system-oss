#!/usr/bin/env python3
"""
Continuous Evaluation Daemon
============================

Background service that continuously monitors and evaluates:
- Agent outputs and code quality
- Reasoning quality of analyses
- Safety compliance
- Multi-agent coordination effectiveness

Integrates with:
- Meta-Learning Engine (outcome recording)
- Darwin-Gödel Machine (improvement proposals)
- Feedback Loop (pattern detection)

Usage:
    python eval_daemon.py [--interval 300] [--watch-dir /path/to/watch]
"""

import asyncio
import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "graders"))
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/eval_daemon.log')
    ]
)
logger = logging.getLogger('eval_daemon')


class CodeChangeHandler(FileSystemEventHandler):
    """Handle file system events for code changes."""

    def __init__(self, daemon: 'EvalDaemon'):
        self.daemon = daemon
        self.last_event_time = {}
        self.debounce_seconds = 2

    def on_modified(self, event):
        if event.is_directory:
            return

        # Only watch Python files
        if not event.src_path.endswith('.py'):
            return

        # Debounce rapid events
        now = time.time()
        last = self.last_event_time.get(event.src_path, 0)
        if now - last < self.debounce_seconds:
            return
        self.last_event_time[event.src_path] = now

        logger.info(f"Detected change: {event.src_path}")
        self.daemon.queue_evaluation(event.src_path, 'code')


class EvalDaemon:
    """
    Continuous evaluation daemon with file watching and scheduled scans.
    """

    def __init__(
        self,
        watch_dirs: List[str] = None,
        scan_interval: int = 300,
        enable_feedback: bool = True
    ):
        self.watch_dirs = watch_dirs or [
            str(Path(__file__).parent.parent / "intelligent-agents"),
        ]
        self.scan_interval = scan_interval
        self.enable_feedback = enable_feedback

        self.running = False
        self.eval_queue: List[Dict] = []
        self.observer = None

        # Load graders
        self.graders = {}
        self._load_graders()

        # Load AGI components
        self.meta_learning = None
        self.feedback_loop = None
        self._load_agi_components()

        # Stats
        self.stats = {
            'started_at': None,
            'total_evals': 0,
            'passed_evals': 0,
            'failed_evals': 0,
            'avg_score': 0.0,
            'last_scan': None,
            'files_watched': 0
        }

    def _load_graders(self):
        """Load evaluation graders."""
        try:
            from code_grader import grade_code
            from reasoning_grader import grade_reasoning
            from safety_grader import grade_safety
            from agent_coordination_grader import grade_coordination

            self.graders = {
                'code': grade_code,
                'reasoning': grade_reasoning,
                'safety': grade_safety,
                'coordination': grade_coordination
            }
            logger.info(f"Loaded {len(self.graders)} graders")
        except ImportError as e:
            logger.error(f"Failed to load graders: {e}")

    def _load_agi_components(self):
        """Load AGI integration components."""
        if not self.enable_feedback:
            return

        try:
            from meta_learning_engine import MetaLearningEngine, TaskOutcome
            from feedback_loop import get_feedback_loop

            self.meta_learning = MetaLearningEngine()
            self.feedback_loop = get_feedback_loop()
            self.TaskOutcome = TaskOutcome
            logger.info("AGI feedback components loaded")
        except ImportError as e:
            logger.warning(f"AGI components not available: {e}")

    def queue_evaluation(self, file_path: str, eval_type: str):
        """Queue a file for evaluation."""
        self.eval_queue.append({
            'path': file_path,
            'type': eval_type,
            'queued_at': datetime.now().isoformat()
        })

    def evaluate_file(self, file_path: str) -> Optional[Dict]:
        """Evaluate a single file."""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r') as f:
                content = f.read()

            grader = self.graders.get('code')
            if not grader:
                return None

            result = grader(content)

            # Update stats
            self.stats['total_evals'] += 1
            if result.get('passed'):
                self.stats['passed_evals'] += 1
            else:
                self.stats['failed_evals'] += 1

            # Update running average
            n = self.stats['total_evals']
            old_avg = self.stats['avg_score']
            self.stats['avg_score'] = old_avg + (result['overall_score'] - old_avg) / n

            # Send to feedback loop
            if self.enable_feedback and self.meta_learning:
                self._send_feedback(file_path, result)

            return {
                'file': file_path,
                'score': result['overall_score'],
                'passed': result['passed'],
                'dimensions': result.get('dimensions', {}),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Evaluation failed for {file_path}: {e}")
            return None

    def _send_feedback(self, file_path: str, result: Dict):
        """Send evaluation result to meta-learning."""
        try:
            outcome = self.TaskOutcome(
                task_id=f"daemon_eval_{Path(file_path).stem}",
                task_type='daemon_code_eval',
                agent_used='eval_daemon',
                success=result['passed'],
                execution_time_ms=0,
                error_message=None if result['passed'] else f"Score: {result['overall_score']:.2f}",
                quality_score=result['overall_score'],
                timestamp=datetime.now(),
                context={
                    'file': file_path,
                    'dimensions': result.get('dimensions', {})
                }
            )
            self.meta_learning.record_outcome(outcome)
        except Exception as e:
            logger.error(f"Failed to send feedback: {e}")

    def process_queue(self):
        """Process queued evaluations."""
        while self.eval_queue:
            item = self.eval_queue.pop(0)
            result = self.evaluate_file(item['path'])
            if result:
                status = "PASS" if result['passed'] else "FAIL"
                logger.info(f"Evaluated {Path(item['path']).name}: {result['score']:.2f} ({status})")

    def scan_directories(self):
        """Scan watched directories for Python files."""
        logger.info("Running scheduled directory scan...")
        self.stats['last_scan'] = datetime.now().isoformat()

        files_scanned = 0
        for watch_dir in self.watch_dirs:
            if not os.path.exists(watch_dir):
                continue

            for root, dirs, files in os.walk(watch_dir):
                # Skip __pycache__ and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(('.', '__'))]

                for file in files:
                    if file.endswith('.py') and not file.startswith('test_'):
                        file_path = os.path.join(root, file)
                        result = self.evaluate_file(file_path)
                        files_scanned += 1

                        if result and not result['passed']:
                            logger.warning(
                                f"Low score: {file} = {result['score']:.2f}"
                            )

        logger.info(f"Scan complete: {files_scanned} files evaluated")
        return files_scanned

    def start_watching(self):
        """Start file system watcher."""
        self.observer = Observer()
        handler = CodeChangeHandler(self)

        for watch_dir in self.watch_dirs:
            if os.path.exists(watch_dir):
                self.observer.schedule(handler, watch_dir, recursive=True)
                logger.info(f"Watching: {watch_dir}")
                self.stats['files_watched'] += 1

        self.observer.start()

    def stop_watching(self):
        """Stop file system watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

    async def run(self):
        """Main daemon loop."""
        self.running = True
        self.stats['started_at'] = datetime.now().isoformat()

        logger.info("=" * 50)
        logger.info("Evaluation Daemon Starting")
        logger.info(f"Watch directories: {self.watch_dirs}")
        logger.info(f"Scan interval: {self.scan_interval}s")
        logger.info(f"Feedback enabled: {self.enable_feedback}")
        logger.info("=" * 50)

        # Start file watcher
        self.start_watching()

        # Initial scan
        self.scan_directories()

        last_scan = time.time()

        while self.running:
            # Process any queued evaluations
            self.process_queue()

            # Periodic full scan
            if time.time() - last_scan >= self.scan_interval:
                self.scan_directories()
                last_scan = time.time()

            await asyncio.sleep(1)

        self.stop_watching()
        logger.info("Evaluation Daemon stopped")

    def stop(self):
        """Stop the daemon."""
        self.running = False

    def get_stats(self) -> Dict:
        """Get daemon statistics."""
        return {
            **self.stats,
            'queue_size': len(self.eval_queue),
            'running': self.running
        }


def main():
    parser = argparse.ArgumentParser(description='Continuous Evaluation Daemon')
    parser.add_argument('--interval', type=int, default=300,
                       help='Scan interval in seconds (default: 300)')
    parser.add_argument('--watch-dir', type=str, action='append',
                       help='Directory to watch (can specify multiple)')
    parser.add_argument('--no-feedback', action='store_true',
                       help='Disable AGI feedback integration')
    args = parser.parse_args()

    watch_dirs = args.watch_dir if args.watch_dir else None

    daemon = EvalDaemon(
        watch_dirs=watch_dirs,
        scan_interval=args.interval,
        enable_feedback=not args.no_feedback
    )

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        daemon.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run daemon
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
