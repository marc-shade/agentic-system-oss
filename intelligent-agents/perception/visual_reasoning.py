#!/usr/bin/env python3
"""
Visual Reasoning Module - LLaVA Integration for Intelligent Scene Understanding

This module connects the cluster's visual perception to vision-language models
running on Ollama, enabling intelligent scene understanding and descriptions.

Features:
- Send captured frames to LLaVA/Llama-Vision models
- Generate natural language scene descriptions
- Extract actionable insights from visual observations
- Integrate with cluster memory for enhanced awareness
"""
import platform

import base64
import json
import logging
import sqlite3
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visual_reasoning")

# Configuration - Cloud-first Ollama endpoints (never use local CPU for LLM inference)
OLLAMA_ENDPOINTS = {
    "completeu-server": os.environ.get("OLLAMA_HOST_COMPLETEU", "http://completeu-server.local:11434"),
    "mac-studio": os.environ.get("OLLAMA_HOST_MAC_STUDIO", "http://Marcs-Mac-Studio.local:11434"),
}
# Default to completeu-server (has moondream vision model)
DEFAULT_ENDPOINT = os.environ.get("OLLAMA_HOST", OLLAMA_ENDPOINTS["completeu-server"])

# Vision models in order of preference
VISION_MODELS = [
    "moondream:latest",
    "llama3.2-vision:11b-instruct-fp16",
    "llama3.2-vision:11b-instruct-q8_0",
    "llava-llama3:8b-v1.1-fp16",
    "qwen2.5vl:7b-fp16"
]

# Storage paths
STORAGE_BASE = Path(os.environ.get('STORAGE_BASE', str(_STORAGE_BASE)))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"


class VisualReasoner:
    """
    Integrates vision-language models for intelligent scene understanding
    """

    def __init__(self, preferred_endpoint: str = "mac-studio"):
        self.endpoint = OLLAMA_ENDPOINTS.get(preferred_endpoint, DEFAULT_ENDPOINT)
        self.available_model = None
        self.client = httpx.Client(timeout=180.0)  # 3 minute timeout for vision models
        self._detect_available_model()

    def _detect_available_model(self):
        """Detect which vision model is available"""
        try:
            response = self.client.get(f"{self.endpoint}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]

                for model in VISION_MODELS:
                    if model in model_names:
                        self.available_model = model
                        logger.info(f"Using vision model: {model} on {self.endpoint}")
                        return

                logger.warning(f"No vision model found on {self.endpoint}")
        except Exception as e:
            logger.error(f"Failed to detect models: {e}")

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """Convert image file to base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read image {image_path}: {e}")
            return None

    def analyze_image(self, image_path: str, context: str = "") -> Dict[str, Any]:
        """
        Analyze an image using vision-language model

        Args:
            image_path: Path to image file
            context: Optional context about the image (e.g., "webcam from office")

        Returns:
            Analysis result with description, entities, and insights
        """
        if not self.available_model:
            return {"error": "No vision model available", "success": False}

        image_b64 = self._image_to_base64(image_path)
        if not image_b64:
            return {"error": f"Failed to read image: {image_path}", "success": False}

        # Build prompt for scene analysis
        prompt = self._build_analysis_prompt(context)

        try:
            response = self.client.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.available_model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 500
                    }
                },
                timeout=180.0
            )

            if response.status_code == 200:
                result = response.json()
                analysis = self._parse_analysis(result.get("response", ""))
                analysis["model"] = self.available_model
                analysis["image_path"] = image_path
                analysis["timestamp"] = datetime.now().isoformat()
                analysis["success"] = True
                return analysis
            else:
                return {"error": f"API error: {response.status_code}", "success": False}

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {"error": str(e), "success": False}

    def _build_analysis_prompt(self, context: str = "") -> str:
        """Build prompt for scene analysis"""
        base_prompt = """Analyze this image and provide a structured observation. Be concise and factual.

Describe:
1. SCENE: What type of environment/room is this? (one line)
2. PEOPLE: Are there people present? What are they doing? (one line)
3. ACTIVITY: What activity or state is visible? (one line)
4. NOTABLE: Any notable objects, text, or details? (one line)
5. MOOD: Overall mood/atmosphere? (one word)

Keep each response to one line. Be specific about what you actually see."""

        if context:
            return f"{base_prompt}\n\nContext: {context}"
        return base_prompt

    def _parse_analysis(self, response: str) -> Dict[str, Any]:
        """Parse the model's response into structured data"""
        analysis = {
            "raw_response": response,
            "scene": "",
            "people": "",
            "activity": "",
            "notable": "",
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
            elif "notable:" in line_lower:
                analysis["notable"] = line.split(":", 1)[-1].strip()
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

        return analysis

    def analyze_cluster_observations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Analyze recent cluster observations with vision model

        Fetches recent frames from cluster database and analyzes them
        """
        results = []

        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Get recent observations with frame paths
            cursor.execute('''
                SELECT node_id, timestamp, data
                FROM cluster_visual_observations
                WHERE data LIKE '%frame_path%'
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))

            for row in cursor.fetchall():
                node_id, timestamp, data_json = row
                try:
                    data = json.loads(data_json)
                    frame_path = data.get("frame_path")

                    if frame_path and Path(frame_path).exists():
                        logger.info(f"Analyzing frame from {node_id}: {frame_path}")
                        analysis = self.analyze_image(
                            frame_path,
                            context=f"Webcam capture from {node_id} at {timestamp}"
                        )
                        analysis["node_id"] = node_id
                        analysis["original_timestamp"] = timestamp
                        results.append(analysis)
                except json.JSONDecodeError:
                    continue

            conn.close()

        except Exception as e:
            logger.error(f"Failed to analyze cluster observations: {e}")

        return results

    def get_current_scene_description(self) -> str:
        """
        Get a natural language description of the current visual state
        """
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Get latest observation with frame
            cursor.execute('''
                SELECT node_id, timestamp, data
                FROM cluster_visual_observations
                WHERE data LIKE '%frame_path%'
                ORDER BY timestamp DESC
                LIMIT 1
            ''')

            row = cursor.fetchone()
            conn.close()

            if row:
                node_id, timestamp, data_json = row
                data = json.loads(data_json)
                frame_path = data.get("frame_path")

                if frame_path and Path(frame_path).exists():
                    analysis = self.analyze_image(
                        frame_path,
                        context=f"Current view from {node_id}"
                    )
                    if analysis.get("success"):
                        return analysis.get("summary", "Unable to describe scene")

            return "No recent visual observations available"

        except Exception as e:
            logger.error(f"Failed to get scene description: {e}")
            return f"Error getting scene description: {e}"

    def store_enhanced_observation(self, observation: Dict[str, Any]) -> bool:
        """
        Store enhanced visual observation in cluster database
        """
        try:
            conn = sqlite3.connect(str(CLUSTER_DB))
            cursor = conn.cursor()

            # Create enhanced observations table if needed
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_visual_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model_used TEXT,
                    scene_description TEXT,
                    people_description TEXT,
                    activity_description TEXT,
                    mood TEXT,
                    summary TEXT,
                    raw_analysis TEXT,
                    image_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO enhanced_visual_observations
                (node_id, timestamp, model_used, scene_description, people_description,
                 activity_description, mood, summary, raw_analysis, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                observation.get("node_id", "unknown"),
                observation.get("timestamp", datetime.now().isoformat()),
                observation.get("model"),
                observation.get("scene"),
                observation.get("people"),
                observation.get("activity"),
                observation.get("mood"),
                observation.get("summary"),
                observation.get("raw_response"),
                observation.get("image_path")
            ))

            conn.commit()
            conn.close()
            logger.info(f"Stored enhanced observation for {observation.get('node_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to store enhanced observation: {e}")
            return False

    def continuous_analysis(self, interval_seconds: int = 30):
        """
        Continuously analyze cluster visual observations
        """
        import time

        logger.info(f"Starting continuous visual analysis (interval: {interval_seconds}s)")

        while True:
            try:
                description = self.get_current_scene_description()
                logger.info(f"Current scene: {description}")

                # Get and store enhanced analysis
                analyses = self.analyze_cluster_observations(limit=1)
                for analysis in analyses:
                    if analysis.get("success"):
                        self.store_enhanced_observation(analysis)

            except Exception as e:
                logger.error(f"Analysis cycle failed: {e}")

            time.sleep(interval_seconds)


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


    parser = argparse.ArgumentParser(description="Visual Reasoning Module")
    parser.add_argument("--endpoint", default="mac-studio",
                       choices=["mac-studio", "completeu-server", "local"],
                       help="Ollama endpoint to use")
    parser.add_argument("--image", help="Analyze specific image file")
    parser.add_argument("--context", default="", help="Context for image analysis")
    parser.add_argument("--current", action="store_true", help="Describe current scene")
    parser.add_argument("--analyze-recent", type=int, default=0,
                       help="Analyze N recent cluster observations")
    parser.add_argument("--continuous", action="store_true",
                       help="Run continuous analysis")
    parser.add_argument("--interval", type=int, default=30,
                       help="Interval for continuous analysis")

    args = parser.parse_args()

    reasoner = VisualReasoner(preferred_endpoint=args.endpoint)

    if not reasoner.available_model:
        print("ERROR: No vision model available")
        return 1

    print(f"Using model: {reasoner.available_model}")
    print(f"Endpoint: {reasoner.endpoint}")
    print()

    if args.image:
        print(f"Analyzing: {args.image}")
        result = reasoner.analyze_image(args.image, args.context)
        print(json.dumps(result, indent=2))

    elif args.current:
        description = reasoner.get_current_scene_description()
        print(f"Current Scene: {description}")

    elif args.analyze_recent > 0:
        print(f"Analyzing {args.analyze_recent} recent observations...")
        results = reasoner.analyze_cluster_observations(args.analyze_recent)
        for r in results:
            print(f"\n--- {r.get('node_id')} ({r.get('original_timestamp')}) ---")
            print(f"Scene: {r.get('scene')}")
            print(f"People: {r.get('people')}")
            print(f"Activity: {r.get('activity')}")
            print(f"Summary: {r.get('summary')}")

    elif args.continuous:
        reasoner.continuous_analysis(args.interval)

    else:
        # Default: show current scene
        description = reasoner.get_current_scene_description()
        print(f"Current Scene: {description}")


if __name__ == "__main__":
    main()
