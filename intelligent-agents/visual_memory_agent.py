#!/usr/bin/env python3
"""
Visual Memory Processing Agent
==============================
Processes visual captures (screenshots, webcam) into structured memories.

Uses Claude's vision capabilities to:
- Analyze screenshot content (what's on screen)
- Detect environmental context from webcam
- Extract actionable insights
- Store in enhanced-memory for persistent recall

This agent runs alongside the environmental_awareness_daemon.
"""

import asyncio
import json
import sqlite3
import base64
import os
import socket
import anthropic
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Configuration
STORAGE_BASE = Path("/Volumes/SSDRAID0/agentic-system")
SENSORY_DIR = STORAGE_BASE / "databases" / "sensory"
DB_PATH = SENSORY_DIR / f"sensory_memory_{socket.gethostname().lower().replace(' ', '-')}.db"

# Processing settings
BATCH_SIZE = 5
PROCESS_INTERVAL_SECONDS = 30
MAX_IMAGE_SIZE_KB = 500  # Skip images larger than this

# Vision analysis prompts
SCREENSHOT_PROMPT = """Analyze this screenshot and extract:
1. **Active Application**: What app/website is in focus?
2. **User Activity**: What is the user doing? (coding, browsing, writing, etc.)
3. **Key Content**: Any important text, code, or information visible
4. **Context Clues**: Time indicators, notifications, system state

Respond in JSON format:
{
    "active_app": "string",
    "activity_type": "string",
    "key_content": ["list of important items"],
    "context": {"time_visible": "if any", "notifications": "count or none"},
    "summary": "one sentence summary"
}"""

WEBCAM_PROMPT = """Analyze this webcam image for environmental awareness:
1. **Presence**: Is anyone visible? How many people?
2. **Lighting**: Day/night, artificial/natural lighting conditions
3. **Environment**: Office, home, outdoor? Any notable features?
4. **Activity State**: Working, away, meeting, etc.

Respond in JSON format:
{
    "presence_detected": true/false,
    "people_count": 0,
    "lighting": "description",
    "environment_type": "string",
    "activity_state": "string",
    "summary": "one sentence summary"
}"""


class VisualMemoryAgent:
    """Agent that processes visual captures into memories."""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.node_id = socket.gethostname().lower().replace(" ", "-")
        self.running = False
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database has required tables."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS visual_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    capture_id INTEGER,
                    capture_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    insights_json TEXT,
                    summary TEXT,
                    stored_in_memory BOOLEAN DEFAULT FALSE,
                    memory_entity_id TEXT
                )
            """)
            conn.commit()

    def _image_to_base64(self, filepath: Path) -> Optional[str]:
        """Convert image file to base64."""
        try:
            # Check size
            size_kb = filepath.stat().st_size / 1024
            if size_kb > MAX_IMAGE_SIZE_KB:
                print(f"Skipping large image: {filepath.name} ({size_kb:.1f}KB)")
                return None

            with open(filepath, 'rb') as f:
                return base64.standard_b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading image {filepath}: {e}")
            return None

    def _get_media_type(self, filepath: Path) -> str:
        """Get media type from file extension."""
        ext = filepath.suffix.lower()
        return {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'image/jpeg')

    async def analyze_image(self, filepath: Path, capture_type: str) -> Optional[Dict]:
        """Analyze an image using Claude's vision."""
        image_data = self._image_to_base64(filepath)
        if not image_data:
            return None

        prompt = SCREENSHOT_PROMPT if capture_type == 'screenshot' else WEBCAM_PROMPT

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": self._get_media_type(filepath),
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Extract JSON from response
            response_text = response.content[0].text

            # Try to parse JSON from response
            try:
                # Handle markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0]
                else:
                    json_str = response_text

                insights = json.loads(json_str.strip())
                return insights
            except json.JSONDecodeError:
                # Return raw response if not valid JSON
                return {"raw_response": response_text, "summary": response_text[:200]}

        except Exception as e:
            print(f"Vision API error: {e}")
            return None

    def get_unprocessed_captures(self, limit: int = BATCH_SIZE) -> List[Dict]:
        """Get captures that haven't been analyzed yet."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            # Get captures not yet in visual_insights
            rows = conn.execute("""
                SELECT c.* FROM captures c
                LEFT JOIN visual_insights v ON c.id = v.capture_id
                WHERE c.deleted = FALSE
                  AND v.id IS NULL
                  AND c.capture_type IN ('screenshot', 'webcam')
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    def store_insights(self, capture_id: int, capture_type: str,
                      insights: Dict, summary: str) -> int:
        """Store visual insights in database."""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                INSERT INTO visual_insights
                (capture_id, capture_type, insights_json, summary)
                VALUES (?, ?, ?, ?)
            """, (capture_id, capture_type, json.dumps(insights), summary))
            conn.commit()
            return cursor.lastrowid

    async def store_in_memory(self, insight_id: int, capture_type: str,
                             insights: Dict, summary: str) -> Optional[str]:
        """Store insights in enhanced-memory (would integrate with MCP)."""
        # This would call enhanced-memory MCP to create an entity
        # For now, we'll mark it as stored and return a placeholder

        entity_name = f"visual_{capture_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # In production, this would call:
        # mcp__enhanced-memory__create_entities([{
        #     "name": entity_name,
        #     "entityType": f"visual_{capture_type}",
        #     "observations": [summary, json.dumps(insights)]
        # }])

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                UPDATE visual_insights
                SET stored_in_memory = TRUE, memory_entity_id = ?
                WHERE id = ?
            """, (entity_name, insight_id))
            conn.commit()

        return entity_name

    async def process_batch(self) -> int:
        """Process a batch of unprocessed captures."""
        captures = self.get_unprocessed_captures()
        processed = 0

        for capture in captures:
            filepath = Path(capture['filepath'])
            if not filepath.exists():
                continue

            print(f"Analyzing: {filepath.name}")

            insights = await self.analyze_image(filepath, capture['capture_type'])
            if insights:
                summary = insights.get('summary', str(insights)[:200])
                insight_id = self.store_insights(
                    capture['id'], capture['capture_type'], insights, summary
                )

                # Store in persistent memory
                await self.store_in_memory(
                    insight_id, capture['capture_type'], insights, summary
                )

                processed += 1
                print(f"  → {summary}")

        return processed

    def get_recent_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent visual insights."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM visual_insights
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_status(self) -> Dict:
        """Get agent status."""
        with sqlite3.connect(DB_PATH) as conn:
            total_insights = conn.execute(
                "SELECT COUNT(*) FROM visual_insights"
            ).fetchone()[0]

            pending = len(self.get_unprocessed_captures(limit=100))

            stored = conn.execute(
                "SELECT COUNT(*) FROM visual_insights WHERE stored_in_memory = TRUE"
            ).fetchone()[0]

        return {
            "node_id": self.node_id,
            "running": self.running,
            "total_insights": total_insights,
            "stored_in_memory": stored,
            "pending_captures": pending,
            "batch_size": BATCH_SIZE,
            "process_interval_sec": PROCESS_INTERVAL_SECONDS
        }

    async def run(self):
        """Main processing loop."""
        self.running = True
        print(f"Visual Memory Agent starting on {self.node_id}")
        print(f"Processing every {PROCESS_INTERVAL_SECONDS}s, batch size {BATCH_SIZE}")

        try:
            while self.running:
                processed = await self.process_batch()
                if processed > 0:
                    print(f"Processed {processed} captures")

                await asyncio.sleep(PROCESS_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False

    def stop(self):
        """Stop the agent."""
        self.running = False


async def main():
    """Main entry point."""
    agent = VisualMemoryAgent()

    # Print initial status
    status = agent.get_status()
    print(f"\nInitial Status: {json.dumps(status, indent=2)}")

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
