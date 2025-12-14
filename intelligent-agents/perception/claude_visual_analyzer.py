#!/usr/bin/env python3
"""
Claude Visual Analyzer - Native Vision Analysis via Claude API

This module provides visual scene understanding using Claude's native
multimodal capabilities, serving as a reliable fallback when local
Ollama vision models are unavailable.

Features:
- Analyze images using Claude API with vision
- Store enhanced observations in cluster database
- Integrate with existing visual perception pipeline
- Provide scene descriptions for cluster awareness
"""
import platform

import base64
import json
import sqlite3
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("claude_visual_analyzer")

# Configuration
STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
SCREENSHOTS_DIR = STORAGE_BASE / "databases" / "sensory" / "screenshots"

# Claude API config
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


class ClaudeVisualAnalyzer:
    """
    Analyzes images using Claude's native vision capabilities
    """

    def __init__(self):
        self.api_key = ANTHROPIC_API_KEY
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set - Claude analysis unavailable")
        self.client = httpx.Client(timeout=60.0)

    def _image_to_base64(self, image_path: str) -> Optional[tuple]:
        """Convert image file to base64 with media type detection"""
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            # Detect media type
            suffix = path.suffix.lower()
            media_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            media_type = media_types.get(suffix, 'image/jpeg')

            with open(image_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            return (data, media_type)
        except Exception as e:
            logger.error(f"Failed to read image {image_path}: {e}")
            return None

    def analyze_image(self, image_path: str, context: str = "") -> Dict[str, Any]:
        """
        Analyze an image using Claude's vision capabilities

        Args:
            image_path: Path to image file
            context: Optional context about the image

        Returns:
            Analysis result with scene description and insights
        """
        if not self.api_key:
            return {"error": "ANTHROPIC_API_KEY not configured", "success": False}

        image_data = self._image_to_base64(image_path)
        if not image_data:
            return {"error": f"Failed to read image: {image_path}", "success": False}

        b64_data, media_type = image_data

        # Build analysis prompt
        prompt = self._build_analysis_prompt(context)

        try:
            response = self.client.post(
                CLAUDE_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": b64_data
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", [{}])[0].get("text", "")
                analysis = self._parse_analysis(content)
                analysis["model"] = "claude-sonnet-4"
                analysis["image_path"] = image_path
                analysis["timestamp"] = datetime.now().isoformat()
                analysis["success"] = True
                return analysis
            else:
                error_msg = response.json().get("error", {}).get("message", response.text)
                return {"error": f"API error: {error_msg}", "success": False}

        except Exception as e:
            logger.error(f"Claude analysis failed: {e}")
            return {"error": str(e), "success": False}

    def _build_analysis_prompt(self, context: str = "") -> str:
        """Build prompt for scene analysis"""
        base_prompt = """Analyze this webcam image and provide a structured observation. Be concise and factual.

Describe:
1. SCENE: What type of environment/room is this? (one line)
2. PEOPLE: Are there people present? What are they doing? (one line)
3. ACTIVITY: What activity or state is visible? (one line)
4. LIGHTING: What are the lighting conditions? (one word: bright/normal/dim/dark)
5. MOOD: Overall mood/atmosphere? (one word)

Keep each response to one line. Be specific about what you actually see."""

        if context:
            return f"{base_prompt}\n\nContext: {context}"
        return base_prompt

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into structured data"""
        analysis = {
            "raw_response": response,
            "scene": "",
            "people": "",
            "activity": "",
            "lighting": "",
            "mood": "",
            "summary": ""
        }

        lines = response.strip().split("\n")
        for line in lines:
            line_lower = line.lower()
            if "scene:" in line_lower:
                analysis["scene"] = line.split(":", 1)[-1].strip()
            elif "people:" in line_lower:
                analysis["people"] = line.split(":", 1)[-1].strip()
            elif "activity:" in line_lower:
                analysis["activity"] = line.split(":", 1)[-1].strip()
            elif "lighting:" in line_lower:
                analysis["lighting"] = line.split(":", 1)[-1].strip()
            elif "mood:" in line_lower:
                analysis["mood"] = line.split(":", 1)[-1].strip()

        # Generate summary
        parts = []
        if analysis["scene"]:
            parts.append(analysis["scene"])
        if analysis["people"]:
            parts.append(analysis["people"])
        if analysis["activity"]:
            parts.append(analysis["activity"])
        analysis["summary"] = ". ".join(parts[:2]) if parts else response[:200]

        # Determine person presence
        people_text = analysis["people"].lower()
        analysis["person_present"] = not any(word in people_text for word in
            ["no", "none", "empty", "absent", "nobody", "not visible", "no one"])

        return analysis

    def analyze_recent_captures(self, node_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Analyze recent captures from a node or all nodes

        Args:
            node_id: Specific node to analyze, or None for all
            limit: Maximum captures to analyze

        Returns:
            List of analysis results
        """
        results = []

        # Find screenshot directories
        if node_id:
            dirs = [SCREENSHOTS_DIR / node_id]
        else:
            dirs = [d for d in SCREENSHOTS_DIR.iterdir() if d.is_dir()]

        for dir_path in dirs:
            if not dir_path.exists():
                continue

            # Get recent images
            images = sorted(dir_path.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

            for image_path in images:
                node = dir_path.name
                logger.info(f"Analyzing {image_path.name} from {node}")

                analysis = self.analyze_image(
                    str(image_path),
                    context=f"Webcam capture from {node}"
                )
                analysis["node_id"] = node
                results.append(analysis)

        return results

    def store_analysis(self, analysis: Dict[str, Any]) -> bool:
        """Store enhanced analysis in cluster database"""
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Create table if needed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS claude_visual_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model TEXT,
                    scene_description TEXT,
                    people_description TEXT,
                    activity_description TEXT,
                    lighting TEXT,
                    mood TEXT,
                    person_present INTEGER,
                    summary TEXT,
                    raw_response TEXT,
                    image_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO claude_visual_analyses
                (node_id, timestamp, model, scene_description, people_description,
                 activity_description, lighting, mood, person_present, summary,
                 raw_response, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.get("node_id", "unknown"),
                analysis.get("timestamp", datetime.now().isoformat()),
                analysis.get("model"),
                analysis.get("scene"),
                analysis.get("people"),
                analysis.get("activity"),
                analysis.get("lighting"),
                analysis.get("mood"),
                1 if analysis.get("person_present") else 0,
                analysis.get("summary"),
                analysis.get("raw_response"),
                analysis.get("image_path")
            ))

            conn.commit()
            conn.close()
            logger.info(f"Stored Claude analysis for {analysis.get('node_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
            return False

    def get_current_awareness(self) -> Dict[str, Any]:
        """
        Get current visual awareness across all nodes

        Returns summary of what's happening visually in the cluster
        """
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Get most recent analysis per node
            cursor.execute('''
                SELECT node_id, timestamp, scene_description, people_description,
                       lighting, mood, person_present, summary
                FROM claude_visual_analyses
                WHERE id IN (
                    SELECT MAX(id) FROM claude_visual_analyses GROUP BY node_id
                )
                ORDER BY timestamp DESC
            ''')

            nodes = {}
            for row in cursor.fetchall():
                nodes[row[0]] = {
                    "timestamp": row[1],
                    "scene": row[2],
                    "people": row[3],
                    "lighting": row[4],
                    "mood": row[5],
                    "person_present": bool(row[6]),
                    "summary": row[7]
                }

            conn.close()

            # Build awareness summary
            person_locations = [n for n, d in nodes.items() if d.get("person_present")]

            return {
                "timestamp": datetime.now().isoformat(),
                "nodes_analyzed": len(nodes),
                "person_detected_at": person_locations,
                "user_status": "present" if person_locations else "absent",
                "node_summaries": nodes,
                "overall_summary": self._generate_overall_summary(nodes)
            }

        except Exception as e:
            logger.error(f"Failed to get awareness: {e}")
            return {"error": str(e)}

    def _generate_overall_summary(self, nodes: Dict[str, Dict]) -> str:
        """Generate human-readable summary of cluster visual state"""
        if not nodes:
            return "No visual data available"

        person_locations = [n for n, d in nodes.items() if d.get("person_present")]

        if not person_locations:
            return "User not detected at any monitored location"
        elif len(person_locations) == 1:
            loc = person_locations[0]
            summary = nodes[loc].get("summary", "")
            return f"User at {loc}: {summary}"
        else:
            return f"User detected at multiple locations: {', '.join(person_locations)}"


def main():
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Claude Visual Analyzer")
    parser.add_argument("--image", help="Analyze specific image")
    parser.add_argument("--context", default="", help="Context for analysis")
    parser.add_argument("--recent", type=int, default=0, help="Analyze N recent captures")
    parser.add_argument("--node", help="Specific node to analyze")
    parser.add_argument("--awareness", action="store_true", help="Show current awareness")
    parser.add_argument("--store", action="store_true", help="Store analysis to database")

    args = parser.parse_args()

    analyzer = ClaudeVisualAnalyzer()

    if args.awareness:
        awareness = analyzer.get_current_awareness()
        print(json.dumps(awareness, indent=2))

    elif args.image:
        print(f"Analyzing: {args.image}")
        result = analyzer.analyze_image(args.image, args.context)
        print(json.dumps(result, indent=2))

        if args.store and result.get("success"):
            analyzer.store_analysis(result)

    elif args.recent > 0:
        print(f"Analyzing {args.recent} recent captures...")
        results = analyzer.analyze_recent_captures(args.node, args.recent)

        for r in results:
            print(f"\n--- {r.get('node_id')} ---")
            print(f"Scene: {r.get('scene')}")
            print(f"People: {r.get('people')}")
            print(f"Lighting: {r.get('lighting')}")
            print(f"Summary: {r.get('summary')}")

            if args.store and r.get("success"):
                analyzer.store_analysis(r)
    else:
        print("Use --image, --recent, or --awareness to analyze visual data")
        print("Example: python claude_visual_analyzer.py --image capture.jpg")


if __name__ == "__main__":
    main()
