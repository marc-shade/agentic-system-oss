"""
Visual Grounding Module - Screenshot-in-Loop for Prometheus.

This is the key differentiator that makes Manus feel "magical".
After each action, we:
1. Capture visual state (screenshot)
2. Analyze with vision model
3. Feed observation into next action decision

Supports multiple vision backends:
- Claude (claude-3-5-sonnet) - Best quality
- Gemini (gemini-pro-vision) - Fast, free tier
- Ollama (llava) - Local, private
"""

import asyncio
import base64
import subprocess
import logging
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class VisualContext(Enum):
    """Types of visual context we can capture."""
    BROWSER = "browser"      # Web page screenshot
    DESKTOP = "desktop"      # Full desktop screenshot
    TERMINAL = "terminal"    # Terminal output
    FILE_CONTENT = "file"    # File content as "visual"


@dataclass
class VisualObservation:
    """Result of visual analysis."""
    context_type: VisualContext
    description: str
    elements_detected: list[str]
    suggested_actions: list[str]
    confidence: float
    raw_image_path: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_prompt_context(self) -> str:
        """Format for inclusion in executor prompt."""
        lines = [
            f"VISUAL STATE ({self.context_type.value}):",
            f"  Description: {self.description}",
        ]
        if self.elements_detected:
            lines.append(f"  Elements: {', '.join(self.elements_detected[:10])}")
        if self.suggested_actions:
            lines.append(f"  Suggested: {', '.join(self.suggested_actions[:3])}")
        return "\n".join(lines)


class VisualGrounding:
    """
    Visual grounding system for screenshot-in-loop execution.

    This captures visual state after actions and analyzes it
    to provide context for the next action decision.
    """

    SCREENSHOT_DIR = Path("/tmp/prometheus/screenshots")

    # Vision model preferences by quality/speed tradeoff
    VISION_PROVIDERS = {
        "claude": {
            "model": "claude-sonnet-4-20250514",
            "method": "_analyze_with_claude",
            "quality": "best",
            "speed": "medium"
        },
        "gemini": {
            "model": "gemini-2.0-flash",
            "method": "_analyze_with_gemini",
            "quality": "good",
            "speed": "fast"
        },
        "ollama": {
            "model": "llama3.2-vision:11b-instruct-q8_0",  # Available locally
            "method": "_analyze_with_ollama",
            "quality": "good",
            "speed": "medium"
        },
        "ollama_fast": {
            "model": "llava-llama3:8b-v1.1-fp16",  # Faster alternative
            "method": "_analyze_with_ollama",
            "quality": "adequate",
            "speed": "fast"
        }
    }

    def __init__(
        self,
        preferred_provider: str = "gemini",
        browser_tab_id: Optional[int] = None,
        save_screenshots: bool = True
    ):
        self.preferred_provider = preferred_provider
        self.browser_tab_id = browser_tab_id
        self.save_screenshots = save_screenshots
        self.observation_history: list[VisualObservation] = []

        # Ensure screenshot directory exists
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def capture_and_analyze(
        self,
        context_type: VisualContext,
        action_just_taken: str = "",
        expected_outcome: str = ""
    ) -> VisualObservation:
        """
        Main entry point: capture visual state and analyze it.

        Args:
            context_type: What kind of visual to capture
            action_just_taken: Description of action we just executed
            expected_outcome: What we expected to happen

        Returns:
            VisualObservation with analysis results
        """
        logger.info(f"Capturing visual state: {context_type.value}")

        # Step 1: Capture the visual
        image_path, image_data = await self._capture_visual(context_type)

        if not image_data:
            return VisualObservation(
                context_type=context_type,
                description="Failed to capture visual state",
                elements_detected=[],
                suggested_actions=["retry_capture", "check_permissions"],
                confidence=0.0,
                raw_image_path=image_path
            )

        # Step 2: Analyze with vision model
        observation = await self._analyze_visual(
            image_data=image_data,
            context_type=context_type,
            action_just_taken=action_just_taken,
            expected_outcome=expected_outcome
        )

        observation.raw_image_path = image_path

        # Step 3: Store in history
        self.observation_history.append(observation)

        # Keep only last 10 observations
        if len(self.observation_history) > 10:
            self.observation_history = self.observation_history[-10:]

        return observation

    async def _capture_visual(
        self,
        context_type: VisualContext
    ) -> tuple[Optional[str], Optional[bytes]]:
        """Capture visual based on context type."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if context_type == VisualContext.BROWSER:
            return await self._capture_browser_screenshot(timestamp)
        elif context_type == VisualContext.DESKTOP:
            return await self._capture_desktop_screenshot(timestamp)
        elif context_type == VisualContext.TERMINAL:
            return await self._capture_terminal_screenshot(timestamp)
        else:
            return None, None

    async def _capture_browser_screenshot(self, timestamp: str) -> tuple[Optional[str], Optional[bytes]]:
        """Capture browser screenshot via claude-in-chrome MCP."""

        if not self.browser_tab_id:
            logger.warning("No browser tab ID set, cannot capture browser screenshot")
            return None, None

        screenshot_path = self.SCREENSHOT_DIR / f"browser_{timestamp}.png"

        # Use claude-in-chrome computer tool with screenshot action
        # This would be called via MCP in actual integration
        # For now, we'll use a subprocess approach
        try:
            # Attempt screencapture on macOS for the active window
            result = subprocess.run(
                ["screencapture", "-x", "-l", str(self.browser_tab_id), str(screenshot_path)],
                capture_output=True,
                timeout=10
            )

            if screenshot_path.exists():
                image_data = screenshot_path.read_bytes()
                return str(screenshot_path), image_data

        except Exception as e:
            logger.warning(f"Browser screenshot failed: {e}")

        # Fallback: capture entire screen
        return await self._capture_desktop_screenshot(timestamp)

    async def _capture_desktop_screenshot(self, timestamp: str) -> tuple[Optional[str], Optional[bytes]]:
        """Capture full desktop screenshot."""

        screenshot_path = self.SCREENSHOT_DIR / f"desktop_{timestamp}.png"

        try:
            # macOS screencapture
            result = subprocess.run(
                ["screencapture", "-x", str(screenshot_path)],
                capture_output=True,
                timeout=10
            )

            if screenshot_path.exists():
                image_data = screenshot_path.read_bytes()
                logger.info(f"Desktop screenshot saved: {screenshot_path}")
                return str(screenshot_path), image_data

        except FileNotFoundError:
            # Try Linux alternatives
            try:
                # gnome-screenshot or scrot
                result = subprocess.run(
                    ["gnome-screenshot", "-f", str(screenshot_path)],
                    capture_output=True,
                    timeout=10
                )
                if screenshot_path.exists():
                    return str(screenshot_path), screenshot_path.read_bytes()
            except:
                pass

        except Exception as e:
            logger.error(f"Desktop screenshot failed: {e}")

        return None, None

    async def _capture_terminal_screenshot(self, timestamp: str) -> tuple[Optional[str], Optional[bytes]]:
        """Capture terminal/iTerm screenshot."""
        # For terminal, we might capture the active terminal window
        # or just return the last command output as text "visual"
        return await self._capture_desktop_screenshot(timestamp)

    async def _analyze_visual(
        self,
        image_data: bytes,
        context_type: VisualContext,
        action_just_taken: str,
        expected_outcome: str
    ) -> VisualObservation:
        """Analyze visual with vision model."""

        provider_info = self.VISION_PROVIDERS.get(self.preferred_provider)
        if not provider_info:
            provider_info = self.VISION_PROVIDERS["ollama"]

        method = getattr(self, provider_info["method"])

        prompt = self._build_analysis_prompt(
            context_type=context_type,
            action_just_taken=action_just_taken,
            expected_outcome=expected_outcome
        )

        try:
            result = await method(image_data, prompt)
            return self._parse_analysis_result(result, context_type)
        except Exception as e:
            logger.error(f"Vision analysis failed with {self.preferred_provider}: {e}")

            # Try fallback providers - prioritize local Ollama since it's always available
            fallback_order = ["ollama", "ollama_fast", "gemini", "claude"]
            for fallback in fallback_order:
                if fallback != self.preferred_provider and fallback in self.VISION_PROVIDERS:
                    try:
                        logger.info(f"Trying fallback vision provider: {fallback}")
                        fallback_info = self.VISION_PROVIDERS[fallback]
                        method = getattr(self, fallback_info["method"])

                        # Temporarily set preferred provider for model selection
                        old_provider = self.preferred_provider
                        self.preferred_provider = fallback
                        result = await method(image_data, prompt)
                        self.preferred_provider = old_provider

                        return self._parse_analysis_result(result, context_type)
                    except Exception as e2:
                        logger.warning(f"Fallback {fallback} also failed: {e2}")
                        continue

            # All failed
            return VisualObservation(
                context_type=context_type,
                description="Vision analysis failed - all providers unavailable",
                elements_detected=[],
                suggested_actions=["check_vision_providers", "verify_api_keys"],
                confidence=0.0
            )

    def _build_analysis_prompt(
        self,
        context_type: VisualContext,
        action_just_taken: str,
        expected_outcome: str
    ) -> str:
        """Build prompt for vision analysis."""

        return f"""Analyze this screenshot and provide structured observation.

CONTEXT: {context_type.value} screenshot
ACTION JUST TAKEN: {action_just_taken or "None"}
EXPECTED OUTCOME: {expected_outcome or "Unknown"}

Respond in JSON format:
{{
    "description": "Brief description of what you see (1-2 sentences)",
    "elements_detected": ["list", "of", "key", "UI", "elements"],
    "state_assessment": "success|partial|failure|unknown",
    "suggested_next_actions": ["action1", "action2"],
    "confidence": 0.0-1.0
}}

Focus on:
1. Did the expected outcome occur?
2. What interactive elements are visible?
3. Any errors, dialogs, or unexpected states?
4. What should happen next?"""

    async def _analyze_with_claude(self, image_data: bytes, prompt: str) -> str:
        """Analyze image with Claude vision."""
        import anthropic

        client = anthropic.Anthropic()

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        return message.content[0].text

    async def _analyze_with_gemini(self, image_data: bytes, prompt: str) -> str:
        """Analyze image with Gemini vision via CLI."""
        import tempfile

        # Save image temporarily
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_data)
            temp_path = f.name

        # Save prompt to file to avoid stdin issues
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as pf:
            pf.write(prompt)
            prompt_path = pf.name

        try:
            # Use gemini CLI with image - use file-based approach
            result = subprocess.run(
                ["gemini", "--image", temp_path, "--yolo", prompt],
                capture_output=True,
                text=True,
                timeout=90
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            else:
                # Try alternative syntax
                result2 = subprocess.run(
                    ["gemini", "-i", temp_path, prompt],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    input=""  # Empty stdin
                )
                if result2.returncode == 0 and result2.stdout.strip():
                    return result2.stdout
                raise Exception(f"Gemini CLI error: {result.stderr or result2.stderr}")

        finally:
            Path(temp_path).unlink(missing_ok=True)
            Path(prompt_path).unlink(missing_ok=True)

    async def _analyze_with_ollama(self, image_data: bytes, prompt: str) -> str:
        """Analyze image with Ollama vision model."""
        import httpx

        # Get the model name from provider config
        provider_info = self.VISION_PROVIDERS.get(self.preferred_provider, {})
        model = provider_info.get("model", "llama3.2-vision:11b-instruct-q8_0")

        # For fallback calls, use the specified model
        if "ollama" in self.preferred_provider:
            model = self.VISION_PROVIDERS.get(self.preferred_provider, {}).get(
                "model", "llama3.2-vision:11b-instruct-q8_0"
            )

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
            )

            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise Exception(f"Ollama error: {response.text}")

    def _parse_analysis_result(self, result: str, context_type: VisualContext) -> VisualObservation:
        """Parse vision model response into VisualObservation."""

        try:
            # Try to extract JSON from response
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0]
            elif "{" in result:
                # Find JSON object
                start = result.index("{")
                end = result.rindex("}") + 1
                json_str = result[start:end]
            else:
                json_str = result

            data = json.loads(json_str)

            return VisualObservation(
                context_type=context_type,
                description=data.get("description", "No description"),
                elements_detected=data.get("elements_detected", []),
                suggested_actions=data.get("suggested_next_actions", []),
                confidence=float(data.get("confidence", 0.7))
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse vision response as JSON: {e}")

            # Fallback: use raw text as description
            return VisualObservation(
                context_type=context_type,
                description=result[:500] if result else "Analysis failed",
                elements_detected=[],
                suggested_actions=[],
                confidence=0.5
            )

    def get_recent_observations_context(self, count: int = 3) -> str:
        """Get recent observations formatted for prompt context."""

        if not self.observation_history:
            return "No visual observations yet."

        recent = self.observation_history[-count:]
        lines = ["RECENT VISUAL OBSERVATIONS:"]

        for i, obs in enumerate(recent, 1):
            lines.append(f"\n[{i}] {obs.to_prompt_context()}")

        return "\n".join(lines)

    def reset(self):
        """Reset observation history for new task."""
        self.observation_history.clear()


# Convenience function for quick visual analysis
async def analyze_screenshot(
    screenshot_path: str,
    action_context: str = "",
    provider: str = "gemini"
) -> VisualObservation:
    """
    Quick analysis of an existing screenshot.

    Args:
        screenshot_path: Path to screenshot image
        action_context: What action led to this state
        provider: Vision provider to use

    Returns:
        VisualObservation with analysis
    """
    vg = VisualGrounding(preferred_provider=provider)

    image_data = Path(screenshot_path).read_bytes()

    return await vg._analyze_visual(
        image_data=image_data,
        context_type=VisualContext.DESKTOP,
        action_just_taken=action_context,
        expected_outcome=""
    )
