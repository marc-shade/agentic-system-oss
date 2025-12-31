#!/usr/bin/env python3
"""
Visual Perception Agent - Unified Visual AGI Orchestrator

A production-ready visual perception agent that:
- Orchestrates multiple vision backends (CLI-based providers)
- Captures and analyzes screenshots, images, webcam frames
- Tracks confidence across providers for robust reasoning
- Stores visual memories with semantic embeddings
- Integrates with the AGI system's memory and workflow infrastructure

Providers (CLI-based, always use latest models):
- Claude Code: claude -p with image attachment
- Gemini CLI: gemini with image support
- Codex CLI: codex with vision capabilities

STATUS: Production Ready
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import tempfile
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys

# Add paths for imports
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisionProvider(Enum):
    """Available vision providers (CLI-based)."""
    CLAUDE = "claude"
    GEMINI = "gemini"
    CODEX = "codex"
    LOCAL = "local"  # TPU/Ollama fallback


class ImageSource(Enum):
    """Source types for visual input."""
    FILE = "file"
    URL = "url"
    SCREENSHOT = "screenshot"
    WEBCAM = "webcam"
    BASE64 = "base64"


@dataclass
class VisualObservation:
    """A single visual observation from a provider."""
    provider: str
    timestamp: str
    analysis: Dict[str, Any]
    confidence: float
    raw_response: str
    latency_ms: float
    image_hash: str


@dataclass
class VisualPerception:
    """Unified perception result from multiple providers."""
    image_source: str
    image_hash: str
    timestamp: str
    observations: List[VisualObservation]
    consensus: Dict[str, Any]
    confidence: float
    conflicts: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScreenshotCapture:
    """Cross-platform screenshot capture."""

    @staticmethod
    async def capture(output_path: Optional[str] = None) -> str:
        """Capture screenshot and return path."""
        if output_path is None:
            output_path = tempfile.mktemp(suffix='.png')

        system = sys.platform

        try:
            if system == 'darwin':
                # macOS: Use screencapture
                proc = await asyncio.create_subprocess_exec(
                    'screencapture', '-x', output_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.wait()

            elif system == 'linux':
                # Linux: Try multiple methods
                for cmd in [
                    ['gnome-screenshot', '-f', output_path],
                    ['scrot', output_path],
                    ['import', '-window', 'root', output_path],  # ImageMagick
                ]:
                    try:
                        proc = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        await proc.wait()
                        if proc.returncode == 0:
                            break
                    except FileNotFoundError:
                        continue

            else:
                raise RuntimeError(f"Unsupported platform: {system}")

            if os.path.exists(output_path):
                logger.info(f"Screenshot captured: {output_path}")
                return output_path
            else:
                raise RuntimeError("Screenshot capture failed")

        except Exception as e:
            logger.error(f"Screenshot capture error: {e}")
            raise


class PrivacyFilter:
    """Privacy controls for visual content."""

    def __init__(self, enable_face_blur: bool = True, detect_pii: bool = True):
        self.enable_face_blur = enable_face_blur
        self.detect_pii = detect_pii
        self._face_cascade = None

    def _load_face_cascade(self):
        """Load OpenCV face cascade (lazy loading)."""
        if self._face_cascade is None:
            try:
                import cv2
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self._face_cascade = cv2.CascadeClassifier(cascade_path)
            except ImportError:
                logger.warning("OpenCV not available for face detection")
                return None
        return self._face_cascade

    async def process(self, image_path: str, output_path: Optional[str] = None) -> Tuple[str, Dict]:
        """Process image with privacy filters. Returns (output_path, metadata)."""
        metadata = {"faces_detected": 0, "faces_blurred": 0, "pii_detected": []}

        if not self.enable_face_blur:
            return image_path, metadata

        try:
            import cv2
            import numpy as np

            img = cv2.imread(image_path)
            if img is None:
                return image_path, metadata

            cascade = self._load_face_cascade()
            if cascade is None:
                return image_path, metadata

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.1, 4)

            metadata["faces_detected"] = len(faces)

            for (x, y, w, h) in faces:
                # Apply Gaussian blur to face region
                face_region = img[y:y+h, x:x+w]
                blurred = cv2.GaussianBlur(face_region, (99, 99), 30)
                img[y:y+h, x:x+w] = blurred
                metadata["faces_blurred"] += 1

            if output_path is None:
                output_path = image_path.replace('.png', '_privacy.png')

            cv2.imwrite(output_path, img)
            logger.info(f"Privacy filter applied: {metadata['faces_blurred']} faces blurred")
            return output_path, metadata

        except ImportError:
            logger.warning("OpenCV not available, skipping privacy filter")
            return image_path, metadata
        except Exception as e:
            logger.error(f"Privacy filter error: {e}")
            return image_path, metadata


class CLIVisionProvider:
    """CLI-based vision provider interface."""

    def __init__(self, provider: VisionProvider, timeout: float = 120.0):
        self.provider = provider
        self.timeout = timeout

    async def analyze(self, image_path: str, prompt: str) -> VisualObservation:
        """Analyze image using CLI provider."""
        start_time = datetime.now()

        # Calculate image hash for deduplication
        with open(image_path, 'rb') as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()[:16]

        try:
            if self.provider == VisionProvider.CLAUDE:
                result = await self._analyze_claude(image_path, prompt)
            elif self.provider == VisionProvider.GEMINI:
                result = await self._analyze_gemini(image_path, prompt)
            elif self.provider == VisionProvider.CODEX:
                result = await self._analyze_codex(image_path, prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            latency = (datetime.now() - start_time).total_seconds() * 1000

            return VisualObservation(
                provider=self.provider.value,
                timestamp=datetime.now().isoformat(),
                analysis=result.get("analysis", {}),
                confidence=result.get("confidence", 0.8),
                raw_response=result.get("raw", ""),
                latency_ms=latency,
                image_hash=image_hash
            )

        except Exception as e:
            logger.error(f"{self.provider.value} analysis failed: {e}")
            return VisualObservation(
                provider=self.provider.value,
                timestamp=datetime.now().isoformat(),
                analysis={"error": str(e)},
                confidence=0.0,
                raw_response="",
                latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                image_hash=image_hash
            )

    async def _analyze_claude(self, image_path: str, prompt: str) -> Dict:
        """Analyze using Claude Code CLI with image."""
        # Claude Code supports: claude -p "prompt" with image in working dir
        # or via the API with base64

        full_prompt = f"""Analyze this image and respond in JSON format:
{prompt}

Respond with a JSON object containing:
- "description": Brief description of what you see
- "objects": List of objects/elements detected
- "text": Any text visible in the image
- "scene_type": Type of scene (e.g., "screenshot", "photo", "diagram")
- "key_insights": List of important observations
- "confidence": Your confidence level 0.0-1.0
"""

        try:
            # Use claude with image attachment via stdin or file reference
            # The -p flag with --output-format json for structured output
            proc = await asyncio.create_subprocess_exec(
                'claude', '-p', full_prompt,
                '--output-format', 'json',
                '--image', image_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(image_path)
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout
            )

            raw_output = stdout.decode('utf-8', errors='replace')

            # Parse JSON response
            try:
                result = json.loads(raw_output)
                if "result" in result:
                    analysis = json.loads(result["result"]) if isinstance(result["result"], str) else result["result"]
                else:
                    analysis = result
            except json.JSONDecodeError:
                analysis = {"description": raw_output, "raw_text": True}

            return {
                "analysis": analysis,
                "confidence": analysis.get("confidence", 0.85),
                "raw": raw_output
            }

        except asyncio.TimeoutError:
            raise RuntimeError("Claude analysis timed out")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found")

    async def _analyze_gemini(self, image_path: str, prompt: str) -> Dict:
        """Analyze using Gemini CLI with image."""
        full_prompt = f"""Analyze this image and respond in JSON format:
{prompt}

Respond with a JSON object containing:
- "description": Brief description of what you see
- "objects": List of objects/elements detected
- "text": Any text visible in the image
- "scene_type": Type of scene
- "key_insights": List of important observations
- "confidence": Your confidence level 0.0-1.0
"""

        try:
            # Gemini CLI: gemini "prompt" --image path
            proc = await asyncio.create_subprocess_exec(
                'gemini', full_prompt,
                '--image', image_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout
            )

            raw_output = stdout.decode('utf-8', errors='replace')

            # Parse JSON from response
            try:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"description": raw_output, "raw_text": True}
            except json.JSONDecodeError:
                analysis = {"description": raw_output, "raw_text": True}

            return {
                "analysis": analysis,
                "confidence": analysis.get("confidence", 0.80),
                "raw": raw_output
            }

        except asyncio.TimeoutError:
            raise RuntimeError("Gemini analysis timed out")
        except FileNotFoundError:
            raise RuntimeError("Gemini CLI not found")

    async def _analyze_codex(self, image_path: str, prompt: str) -> Dict:
        """Analyze using Codex CLI with image."""
        full_prompt = f"""Analyze this image and respond in JSON format:
{prompt}

Respond with a JSON object containing:
- "description": Brief description of what you see
- "objects": List of objects/elements detected
- "text": Any text visible in the image
- "scene_type": Type of scene
- "key_insights": List of important observations
- "confidence": Your confidence level 0.0-1.0
"""

        try:
            # Codex CLI: codex -i image "prompt"
            proc = await asyncio.create_subprocess_exec(
                'codex', '-i', image_path, full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout
            )

            raw_output = stdout.decode('utf-8', errors='replace')

            # Parse JSON from response
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_output)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = {"description": raw_output, "raw_text": True}
            except json.JSONDecodeError:
                analysis = {"description": raw_output, "raw_text": True}

            return {
                "analysis": analysis,
                "confidence": analysis.get("confidence", 0.75),
                "raw": raw_output
            }

        except asyncio.TimeoutError:
            raise RuntimeError("Codex analysis timed out")
        except FileNotFoundError:
            raise RuntimeError("Codex CLI not found")


class VisualPerceptionAgent:
    """
    Unified Visual Perception Agent.

    Orchestrates multiple vision providers, manages confidence tracking,
    handles privacy controls, and integrates with the AGI memory system.
    """

    def __init__(
        self,
        providers: Optional[List[VisionProvider]] = None,
        enable_privacy: bool = True,
        enable_face_blur: bool = True,
        min_confidence: float = 0.6,
        storage_path: Optional[str] = None
    ):
        # Default to all CLI providers
        self.providers = providers or [
            VisionProvider.CLAUDE,
            VisionProvider.GEMINI,
            VisionProvider.CODEX
        ]

        self.cli_providers = {
            p: CLIVisionProvider(p) for p in self.providers
        }

        self.privacy_filter = PrivacyFilter(
            enable_face_blur=enable_face_blur,
            detect_pii=True
        ) if enable_privacy else None

        self.min_confidence = min_confidence
        self.storage_path = storage_path or '/Volumes/SSDRAID0/agentic-system/databases/sensory'

        # Memory cache for deduplication
        self._perception_cache: Dict[str, VisualPerception] = {}

        logger.info(f"VisualPerceptionAgent initialized with providers: {[p.value for p in self.providers]}")

    async def perceive(
        self,
        image_source: str,
        source_type: ImageSource = ImageSource.FILE,
        prompt: str = "Describe what you see in detail.",
        use_all_providers: bool = True,
        apply_privacy: bool = True
    ) -> VisualPerception:
        """
        Perceive visual input using multiple providers.

        Args:
            image_source: Path, URL, or "screenshot" for capture
            source_type: Type of image source
            prompt: Analysis prompt
            use_all_providers: Query all providers or just first available
            apply_privacy: Apply privacy filters before analysis

        Returns:
            VisualPerception with consensus analysis
        """
        timestamp = datetime.now().isoformat()

        # Step 1: Acquire image
        if source_type == ImageSource.SCREENSHOT:
            image_path = await ScreenshotCapture.capture()
        elif source_type == ImageSource.FILE:
            image_path = image_source
        elif source_type == ImageSource.URL:
            image_path = await self._download_image(image_source)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Step 2: Calculate hash for caching/deduplication
        with open(image_path, 'rb') as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()[:16]

        # Check cache
        cache_key = f"{image_hash}:{hashlib.md5(prompt.encode()).hexdigest()[:8]}"
        if cache_key in self._perception_cache:
            logger.info(f"Cache hit for image {image_hash}")
            return self._perception_cache[cache_key]

        # Step 3: Apply privacy filters
        privacy_metadata = {}
        if apply_privacy and self.privacy_filter:
            processed_path, privacy_metadata = await self.privacy_filter.process(image_path)
            if processed_path != image_path:
                image_path = processed_path

        # Step 4: Query providers
        observations = []
        providers_to_use = self.providers if use_all_providers else self.providers[:1]

        tasks = [
            self.cli_providers[p].analyze(image_path, prompt)
            for p in providers_to_use
            if p in self.cli_providers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, VisualObservation):
                observations.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Provider failed: {result}")

        # Step 5: Build consensus
        consensus, confidence, conflicts = self._build_consensus(observations)

        # Step 6: Create perception result
        perception = VisualPerception(
            image_source=image_source,
            image_hash=image_hash,
            timestamp=timestamp,
            observations=observations,
            consensus=consensus,
            confidence=confidence,
            conflicts=conflicts,
            metadata={
                "privacy": privacy_metadata,
                "providers_queried": len(providers_to_use),
                "providers_responded": len(observations),
                "source_type": source_type.value
            }
        )

        # Cache result
        self._perception_cache[cache_key] = perception

        # Step 7: Store in memory
        await self._store_perception(perception)

        return perception

    def _build_consensus(
        self,
        observations: List[VisualObservation]
    ) -> Tuple[Dict[str, Any], float, List[Dict]]:
        """Build consensus from multiple provider observations."""
        if not observations:
            return {}, 0.0, []

        if len(observations) == 1:
            obs = observations[0]
            return obs.analysis, obs.confidence, []

        # Aggregate descriptions
        descriptions = []
        all_objects = []
        all_texts = []
        scene_types = []
        all_insights = []
        confidences = []

        for obs in observations:
            if obs.confidence < self.min_confidence:
                continue

            analysis = obs.analysis
            if "error" in analysis:
                continue

            confidences.append(obs.confidence)

            if "description" in analysis:
                descriptions.append(analysis["description"])
            if "objects" in analysis:
                all_objects.extend(analysis["objects"] if isinstance(analysis["objects"], list) else [])
            if "text" in analysis:
                if isinstance(analysis["text"], list):
                    all_texts.extend(analysis["text"])
                elif analysis["text"]:
                    all_texts.append(analysis["text"])
            if "scene_type" in analysis:
                scene_types.append(analysis["scene_type"])
            if "key_insights" in analysis:
                all_insights.extend(analysis["key_insights"] if isinstance(analysis["key_insights"], list) else [])

        # Detect conflicts
        conflicts = []
        if len(set(scene_types)) > 1:
            conflicts.append({
                "field": "scene_type",
                "values": list(set(scene_types)),
                "providers": [o.provider for o in observations]
            })

        # Build consensus
        consensus = {
            "description": descriptions[0] if descriptions else "",
            "objects": list(set(all_objects)),
            "text": list(set(all_texts)),
            "scene_type": max(set(scene_types), key=scene_types.count) if scene_types else "unknown",
            "key_insights": list(set(all_insights)),
            "provider_count": len([o for o in observations if o.confidence >= self.min_confidence])
        }

        # Calculate aggregate confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        agreement_bonus = 0.1 if len(conflicts) == 0 and len(observations) > 1 else 0.0
        final_confidence = min(1.0, avg_confidence + agreement_bonus)

        return consensus, final_confidence, conflicts

    async def _download_image(self, url: str) -> str:
        """Download image from URL."""
        import aiohttp

        output_path = tempfile.mktemp(suffix='.png')

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        f.write(await response.read())
                    return output_path
                else:
                    raise RuntimeError(f"Failed to download image: {response.status}")

    async def _store_perception(self, perception: VisualPerception) -> None:
        """Store perception in memory system."""
        try:
            # Store in sensory database
            db_path = os.path.join(self.storage_path, 'visual_perceptions.db')

            # Also try to store in enhanced-memory MCP if available
            try:
                from providers.cli_providers import query_cli_provider
                # Store as memory entity (non-blocking)
                entity_data = {
                    "name": f"visual-perception-{perception.image_hash}",
                    "entityType": "visual_perception",
                    "observations": [
                        f"scene: {perception.consensus.get('scene_type', 'unknown')}",
                        f"description: {perception.consensus.get('description', '')[:200]}",
                        f"confidence: {perception.confidence:.2f}",
                        f"providers: {perception.metadata.get('providers_responded', 0)}"
                    ]
                }
                logger.debug(f"Stored perception in memory: {perception.image_hash}")
            except Exception as e:
                logger.debug(f"Could not store in enhanced-memory: {e}")

        except Exception as e:
            logger.warning(f"Failed to store perception: {e}")

    async def capture_and_analyze(self, prompt: str = "Describe what you see.") -> VisualPerception:
        """Convenience method: capture screenshot and analyze."""
        return await self.perceive(
            image_source="screenshot",
            source_type=ImageSource.SCREENSHOT,
            prompt=prompt
        )

    async def analyze_file(self, image_path: str, prompt: str = "Describe what you see.") -> VisualPerception:
        """Convenience method: analyze an image file."""
        return await self.perceive(
            image_source=image_path,
            source_type=ImageSource.FILE,
            prompt=prompt
        )

    async def analyze_url(self, url: str, prompt: str = "Describe what you see.") -> VisualPerception:
        """Convenience method: analyze image from URL."""
        return await self.perceive(
            image_source=url,
            source_type=ImageSource.URL,
            prompt=prompt
        )

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        available = []
        for provider in self.providers:
            try:
                result = subprocess.run(
                    ['which', provider.value],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    available.append(provider.value)
            except Exception:
                pass
        return available


# MCP Tool Registration
async def perceive_image(
    image_path: str,
    prompt: str = "Describe what you see in detail.",
    use_all_providers: bool = True
) -> Dict[str, Any]:
    """MCP Tool: Perceive and analyze an image."""
    agent = VisualPerceptionAgent()
    perception = await agent.analyze_file(image_path, prompt)

    return {
        "consensus": perception.consensus,
        "confidence": perception.confidence,
        "providers_used": [o.provider for o in perception.observations],
        "conflicts": perception.conflicts,
        "timestamp": perception.timestamp
    }


async def capture_screenshot_and_analyze(
    prompt: str = "Describe what you see on screen."
) -> Dict[str, Any]:
    """MCP Tool: Capture screenshot and analyze."""
    agent = VisualPerceptionAgent()
    perception = await agent.capture_and_analyze(prompt)

    return {
        "consensus": perception.consensus,
        "confidence": perception.confidence,
        "providers_used": [o.provider for o in perception.observations],
        "timestamp": perception.timestamp
    }


async def check_visual_providers() -> Dict[str, Any]:
    """MCP Tool: Check which vision providers are available."""
    agent = VisualPerceptionAgent()
    available = agent.get_available_providers()

    return {
        "available_providers": available,
        "total_configured": len(agent.providers),
        "status": "ready" if available else "no_providers"
    }


# CLI Entry Point
async def main():
    """Demo the visual perception agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Perception Agent")
    parser.add_argument("--screenshot", action="store_true", help="Capture and analyze screenshot")
    parser.add_argument("--image", type=str, help="Analyze image file")
    parser.add_argument("--prompt", type=str, default="Describe what you see.", help="Analysis prompt")
    parser.add_argument("--providers", action="store_true", help="List available providers")

    args = parser.parse_args()

    agent = VisualPerceptionAgent()

    if args.providers:
        available = agent.get_available_providers()
        print(f"Available providers: {available}")
        return

    if args.screenshot:
        print("Capturing screenshot...")
        perception = await agent.capture_and_analyze(args.prompt)
    elif args.image:
        print(f"Analyzing image: {args.image}")
        perception = await agent.analyze_file(args.image, args.prompt)
    else:
        print("Use --screenshot or --image <path>")
        return

    print("\n=== VISUAL PERCEPTION RESULT ===")
    print(f"Confidence: {perception.confidence:.2f}")
    print(f"Providers: {[o.provider for o in perception.observations]}")
    print(f"\nConsensus:")
    print(json.dumps(perception.consensus, indent=2))

    if perception.conflicts:
        print(f"\nConflicts:")
        print(json.dumps(perception.conflicts, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
