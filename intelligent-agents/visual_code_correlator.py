#!/usr/bin/env python3
"""
Visual-Code Correlator - Automatic Correlation of Code Changes and Visual Outcomes

Tracks correlations between:
- Code file modifications and resulting UI changes
- Git commits and visual state transitions
- Test runs and visual verification
- Build processes and visual feedback

Use cases:
- "When I edited this file, what did the UI look like?"
- "What code changes caused this visual change?"
- "Show me the visual context around this commit"

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrelationType(Enum):
    """Types of visual-code correlations."""
    EDIT_VISUAL = "edit_visual"           # File edit -> visual change
    COMMIT_VISUAL = "commit_visual"       # Git commit -> visual state
    TEST_VISUAL = "test_visual"           # Test run -> visual outcome
    BUILD_VISUAL = "build_visual"         # Build -> visual feedback
    DEPLOY_VISUAL = "deploy_visual"       # Deploy -> visual verification


class CorrelationStrength(Enum):
    """Strength of correlation."""
    WEAK = "weak"           # Time proximity only
    MODERATE = "moderate"   # Time + file type match
    STRONG = "strong"       # Time + file + visual change type match
    CAUSAL = "causal"       # Confirmed causal relationship


@dataclass
class CodeEvent:
    """A code-related event."""
    id: str
    event_type: str  # edit, commit, test, build
    file_path: Optional[str]
    description: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualCodeCorrelation:
    """A correlation between code and visual state."""
    id: str
    correlation_type: CorrelationType
    strength: CorrelationStrength
    code_event: CodeEvent
    visual_before: Optional[Dict[str, Any]]
    visual_after: Dict[str, Any]
    time_delta_seconds: float
    insights: List[str]
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class VisualCodeCorrelator:
    """
    Tracks and discovers correlations between code changes and visual outcomes.

    Enables:
    - Retroactive analysis: "What visual state existed during this commit?"
    - Causal discovery: "What code change caused this UI change?"
    - Pattern learning: "File type X changes usually result in visual type Y"
    """

    def __init__(
        self,
        storage_path: str = "/Volumes/SSDRAID0/agentic-system/databases/visual_code_correlations"
    ):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Correlation database
        self._correlations: List[VisualCodeCorrelation] = []

        # Pattern library
        self._patterns = self._load_patterns()

        # Active tracking
        self._pending_code_events: List[CodeEvent] = []
        self._last_visual_state: Optional[Dict] = None

        logger.info(f"VisualCodeCorrelator initialized at {storage_path}")

    def _load_patterns(self) -> Dict[str, Any]:
        """Load learned correlation patterns."""
        pattern_path = os.path.join(self.storage_path, "patterns.json")

        if os.path.exists(pattern_path):
            try:
                with open(pattern_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "file_type_visual_patterns": {},
            "strong_correlations": [],
            "last_updated": datetime.now().isoformat()
        }

    def _save_patterns(self) -> None:
        """Save pattern library."""
        pattern_path = os.path.join(self.storage_path, "patterns.json")
        self._patterns["last_updated"] = datetime.now().isoformat()

        with open(pattern_path, 'w') as f:
            json.dump(self._patterns, f, indent=2, default=str)

    async def record_code_event(
        self,
        event_type: str,
        description: str,
        file_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> CodeEvent:
        """
        Record a code-related event for correlation tracking.

        Args:
            event_type: Type of event (edit, commit, test, build)
            description: Description of the event
            file_path: Optional file path involved
            metadata: Additional metadata

        Returns:
            The created CodeEvent
        """
        event_id = f"code_{datetime.now().strftime('%Y%m%d%H%M%S')}_{event_type}"

        event = CodeEvent(
            id=event_id,
            event_type=event_type,
            file_path=file_path,
            description=description,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        self._pending_code_events.append(event)

        # Keep only recent events
        self._pending_code_events = self._pending_code_events[-100:]

        # Store event
        self._store_code_event(event)

        # Try to find immediate correlations with current visual state
        if self._last_visual_state:
            await self._check_immediate_correlation(event)

        return event

    def _store_code_event(self, event: CodeEvent) -> None:
        """Store code event to disk."""
        events_path = os.path.join(self.storage_path, "code_events.jsonl")

        record = {
            "id": event.id,
            "event_type": event.event_type,
            "file_path": event.file_path,
            "description": event.description,
            "timestamp": event.timestamp,
            "metadata": event.metadata
        }

        with open(events_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    async def record_visual_state(self, visual_state: Dict) -> List[VisualCodeCorrelation]:
        """
        Record a visual state and find correlations with recent code events.

        Args:
            visual_state: Visual observation dict

        Returns:
            List of discovered correlations
        """
        correlations = []

        # Check for correlations with pending code events
        for event in self._pending_code_events:
            correlation = await self._evaluate_correlation(event, visual_state)
            if correlation:
                correlations.append(correlation)
                self._correlations.append(correlation)
                self._store_correlation(correlation)

        # Update visual state
        previous_state = self._last_visual_state
        self._last_visual_state = visual_state

        # Learn patterns from new correlations
        for corr in correlations:
            self._learn_pattern(corr)

        return correlations

    async def _check_immediate_correlation(self, event: CodeEvent) -> Optional[VisualCodeCorrelation]:
        """Check for immediate correlation between code event and current visual."""
        if not self._last_visual_state:
            return None

        return await self._evaluate_correlation(event, self._last_visual_state)

    async def _evaluate_correlation(
        self,
        event: CodeEvent,
        visual_state: Dict
    ) -> Optional[VisualCodeCorrelation]:
        """Evaluate potential correlation between code event and visual state."""
        # Calculate time delta
        try:
            event_time = datetime.fromisoformat(event.timestamp)
            visual_time = datetime.fromisoformat(visual_state.get("timestamp", datetime.now().isoformat()))
            time_delta = abs((visual_time - event_time).total_seconds())
        except Exception:
            time_delta = 0

        # Only consider events within 5 minutes
        if time_delta > 300:
            return None

        # Determine correlation type
        corr_type = self._determine_correlation_type(event)

        # Evaluate strength
        strength, confidence, insights = self._evaluate_strength(event, visual_state, time_delta)

        # Skip weak correlations with low confidence
        if strength == CorrelationStrength.WEAK and confidence < 0.5:
            return None

        corr_id = f"corr_{datetime.now().strftime('%Y%m%d%H%M%S')}_{event.id[:8]}"

        return VisualCodeCorrelation(
            id=corr_id,
            correlation_type=corr_type,
            strength=strength,
            code_event=event,
            visual_before=self._last_visual_state,
            visual_after=visual_state,
            time_delta_seconds=time_delta,
            insights=insights,
            confidence=confidence
        )

    def _determine_correlation_type(self, event: CodeEvent) -> CorrelationType:
        """Determine correlation type based on event."""
        type_map = {
            "edit": CorrelationType.EDIT_VISUAL,
            "commit": CorrelationType.COMMIT_VISUAL,
            "test": CorrelationType.TEST_VISUAL,
            "build": CorrelationType.BUILD_VISUAL,
            "deploy": CorrelationType.DEPLOY_VISUAL
        }
        return type_map.get(event.event_type, CorrelationType.EDIT_VISUAL)

    def _evaluate_strength(
        self,
        event: CodeEvent,
        visual_state: Dict,
        time_delta: float
    ) -> Tuple[CorrelationStrength, float, List[str]]:
        """Evaluate correlation strength."""
        insights = []
        score = 0.0

        # Time proximity score (closer = higher)
        time_score = max(0, 1 - (time_delta / 300))
        score += time_score * 0.3
        insights.append(f"Time proximity: {time_delta:.0f}s ({time_score:.0%})")

        # File type matching
        if event.file_path:
            file_ext = Path(event.file_path).suffix.lower()
            visual_scene = visual_state.get("scene_type", "")

            # Check if file type typically correlates with this visual
            file_visual_patterns = self._patterns.get("file_type_visual_patterns", {})

            if file_ext in file_visual_patterns:
                expected_scenes = file_visual_patterns[file_ext]
                if visual_scene in expected_scenes:
                    score += 0.3
                    insights.append(f"File type {file_ext} matches visual scene {visual_scene}")

            # Frontend files -> UI changes
            frontend_exts = ['.tsx', '.jsx', '.css', '.scss', '.html', '.vue', '.svelte']
            if file_ext in frontend_exts:
                score += 0.2
                insights.append(f"Frontend file modification ({file_ext})")

        # Visual change detection
        if self._last_visual_state:
            visual_changed = visual_state.get("scene_type") != self._last_visual_state.get("scene_type")
            if visual_changed:
                score += 0.2
                insights.append("Visual scene changed after code event")

        # Determine strength level
        if score >= 0.7:
            strength = CorrelationStrength.STRONG
        elif score >= 0.5:
            strength = CorrelationStrength.MODERATE
        else:
            strength = CorrelationStrength.WEAK

        return strength, score, insights

    def _learn_pattern(self, correlation: VisualCodeCorrelation) -> None:
        """Learn patterns from correlation."""
        if correlation.strength in [CorrelationStrength.STRONG, CorrelationStrength.CAUSAL]:
            event = correlation.code_event

            if event.file_path:
                file_ext = Path(event.file_path).suffix.lower()
                visual_scene = correlation.visual_after.get("scene_type", "")

                if file_ext and visual_scene:
                    patterns = self._patterns.setdefault("file_type_visual_patterns", {})
                    scenes = patterns.setdefault(file_ext, [])

                    if visual_scene not in scenes:
                        scenes.append(visual_scene)

            # Store strong correlation
            self._patterns.setdefault("strong_correlations", []).append({
                "correlation_id": correlation.id,
                "file_path": event.file_path,
                "visual_scene": correlation.visual_after.get("scene_type"),
                "strength": correlation.strength.value,
                "timestamp": correlation.timestamp
            })

            self._save_patterns()

    def _store_correlation(self, correlation: VisualCodeCorrelation) -> None:
        """Store correlation to disk."""
        corr_path = os.path.join(self.storage_path, "correlations.jsonl")

        record = {
            "id": correlation.id,
            "type": correlation.correlation_type.value,
            "strength": correlation.strength.value,
            "code_event_id": correlation.code_event.id,
            "code_event_type": correlation.code_event.event_type,
            "file_path": correlation.code_event.file_path,
            "visual_scene": correlation.visual_after.get("scene_type"),
            "time_delta_seconds": correlation.time_delta_seconds,
            "confidence": correlation.confidence,
            "insights": correlation.insights,
            "timestamp": correlation.timestamp
        }

        with open(corr_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    async def get_visual_context_for_commit(self, commit_hash: str) -> Dict[str, Any]:
        """
        Get visual context around a git commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Visual context dict with before/after states
        """
        try:
            # Get commit timestamp
            result = subprocess.run(
                ["git", "log", "-1", "--format=%cI", commit_hash],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {"error": "Could not get commit info"}

            commit_time = result.stdout.strip()

            # Search for correlations near this time
            correlations = self._find_correlations_near_time(commit_time)

            return {
                "commit_hash": commit_hash,
                "commit_time": commit_time,
                "correlations": [
                    {
                        "id": c.id,
                        "type": c.correlation_type.value,
                        "visual_scene": c.visual_after.get("scene_type"),
                        "time_delta": c.time_delta_seconds
                    }
                    for c in correlations
                ],
                "visual_context_found": len(correlations) > 0
            }

        except Exception as e:
            return {"error": str(e)}

    async def get_code_context_for_visual(self, visual_observation: Dict) -> Dict[str, Any]:
        """
        Get code context that might have caused a visual state.

        Args:
            visual_observation: Visual observation dict

        Returns:
            Code context with potential causes
        """
        # Find correlations that resulted in this visual type
        scene_type = visual_observation.get("scene_type", "")

        matching = [
            c for c in self._correlations
            if c.visual_after.get("scene_type") == scene_type
        ]

        # Group by file path
        files_involved = {}
        for corr in matching:
            file_path = corr.code_event.file_path
            if file_path:
                if file_path not in files_involved:
                    files_involved[file_path] = {
                        "count": 0,
                        "last_change": None
                    }
                files_involved[file_path]["count"] += 1
                files_involved[file_path]["last_change"] = corr.timestamp

        return {
            "visual_scene": scene_type,
            "related_files": files_involved,
            "total_correlations": len(matching),
            "potential_causes": [
                {
                    "file": corr.code_event.file_path,
                    "event_type": corr.code_event.event_type,
                    "description": corr.code_event.description[:100],
                    "confidence": corr.confidence
                }
                for corr in matching[-5:]
            ]
        }

    def _find_correlations_near_time(
        self,
        timestamp: str,
        window_minutes: int = 10
    ) -> List[VisualCodeCorrelation]:
        """Find correlations near a timestamp."""
        try:
            target = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            return []

        window = timedelta(minutes=window_minutes)

        return [
            c for c in self._correlations
            if abs(datetime.fromisoformat(c.timestamp.replace("Z", "+00:00")) - target) <= window
        ]

    def get_correlation_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get correlation summary."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent = [
            c for c in self._correlations
            if datetime.fromisoformat(c.timestamp) > cutoff
        ]

        strength_counts = {}
        for c in recent:
            s = c.strength.value
            strength_counts[s] = strength_counts.get(s, 0) + 1

        type_counts = {}
        for c in recent:
            t = c.correlation_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "hours": hours,
            "total_correlations": len(recent),
            "by_strength": strength_counts,
            "by_type": type_counts,
            "learned_patterns": len(self._patterns.get("file_type_visual_patterns", {})),
            "strong_correlations_total": len(self._patterns.get("strong_correlations", [])),
            "timestamp": datetime.now().isoformat()
        }


# MCP Tool Functions
async def record_code_visual_event(
    event_type: str,
    description: str,
    file_path: str = ""
) -> Dict:
    """MCP Tool: Record code event for visual correlation."""
    correlator = VisualCodeCorrelator()
    event = await correlator.record_code_event(
        event_type=event_type,
        description=description,
        file_path=file_path if file_path else None
    )

    return {
        "event_id": event.id,
        "recorded": True
    }


async def get_visual_for_commit(commit_hash: str) -> Dict:
    """MCP Tool: Get visual context for a commit."""
    correlator = VisualCodeCorrelator()
    return await correlator.get_visual_context_for_commit(commit_hash)


def get_code_visual_summary(hours: int = 24) -> Dict:
    """MCP Tool: Get code-visual correlation summary."""
    correlator = VisualCodeCorrelator()
    return correlator.get_correlation_summary(hours)


# CLI Entry Point
async def main():
    """Demo visual-code correlator."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual-Code Correlator")
    parser.add_argument("--record", action="store_true", help="Record a code event")
    parser.add_argument("--event-type", default="edit", help="Event type")
    parser.add_argument("--description", default="", help="Event description")
    parser.add_argument("--file", default="", help="File path")
    parser.add_argument("--commit", type=str, help="Get visual context for commit")
    parser.add_argument("--summary", action="store_true", help="Show summary")

    args = parser.parse_args()

    correlator = VisualCodeCorrelator()

    if args.record:
        event = await correlator.record_code_event(
            event_type=args.event_type,
            description=args.description or f"{args.event_type} event",
            file_path=args.file if args.file else None
        )
        print(f"Recorded event: {event.id}")

    elif args.commit:
        context = await correlator.get_visual_context_for_commit(args.commit)
        print(json.dumps(context, indent=2))

    elif args.summary:
        summary = correlator.get_correlation_summary()
        print(json.dumps(summary, indent=2))

    else:
        print("Use --record to record event, --commit <hash> to get visual context, or --summary")


if __name__ == "__main__":
    asyncio.run(main())
