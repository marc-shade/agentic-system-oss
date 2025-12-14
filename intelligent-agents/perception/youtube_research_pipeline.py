#!/usr/bin/env python3
"""
YouTube Research Pipeline - Extract and Process Video Transcripts

Converts YouTube video transcripts into actionable research items for
integration into the agentic system's knowledge base.

Features:
- Transcript extraction with timestamps
- Key concept identification
- Research action item generation
- Memory system integration
- Structured output for downstream processing

Usage:
    python3 youtube_research_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
    python3 youtube_research_pipeline.py --video-id "VIDEO_ID" --timestamp 2182
"""

import json
import re
import sys
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("youtube_research_pipeline")

# Add paths for MCP imports
sys.path.insert(0, "/mnt/agentic-system/mcp-servers/enhanced-memory-mcp")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _HAS_TRANSCRIPT_API = True
except ImportError:
    _HAS_TRANSCRIPT_API = False
    logger.warning("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")

# Ollama for AI-powered extraction
try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class OllamaExtractor:
    """AI-powered concept extraction using Ollama on inference node."""

    # Use completeu-server (M4 Max with 128GB) for inference
    OLLAMA_URLS = [
        "http://completeu-server.local:11434",
        "http://192.168.0.186:11434",  # Fallback IP
    ]
    DEFAULT_MODEL = "mistral-nemo:12b-instruct-2407-fp16"  # Fast and capable, loaded on inference node

    def __init__(self, model: str = None, timeout: float = 60.0):
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout
        self.base_url = None
        self._client = None

    def _get_client(self) -> Optional[httpx.Client]:
        """Get or create HTTP client with working Ollama URL."""
        if self._client:
            return self._client

        if not _HAS_HTTPX:
            return None

        for url in self.OLLAMA_URLS:
            try:
                client = httpx.Client(base_url=url, timeout=5.0)
                response = client.get("/api/tags")
                if response.status_code == 200:
                    self.base_url = url
                    self._client = httpx.Client(base_url=url, timeout=self.timeout)
                    logger.info(f"Connected to Ollama at {url}")
                    return self._client
                client.close()
            except Exception:
                continue

        logger.warning("No Ollama server available for AI extraction")
        return None

    def extract_concepts(self, transcript: str, max_concepts: int = 30) -> List[str]:
        """Extract key concepts using LLM."""
        client = self._get_client()
        if not client:
            return []

        # Truncate transcript if too long (keep beginning and end)
        if len(transcript) > 8000:
            transcript = transcript[:4000] + "\n\n[...middle truncated...]\n\n" + transcript[-4000:]

        prompt = f"""Analyze this transcript from a technical video and extract the key concepts, techniques, and technologies mentioned.

TRANSCRIPT:
{transcript}

Extract the most important technical concepts, focusing on:
- AI/ML techniques and algorithms
- Named models or frameworks
- Research papers or publications
- Technical methodologies
- Software tools or libraries

Return ONLY a JSON array of strings with the top {max_concepts} concepts. No explanations.
Example: ["transformer", "GRPO", "visual reasoning", "contrastive learning"]

JSON array:"""

        try:
            response = client.post("/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500}
            })

            if response.status_code == 200:
                result = response.json().get("response", "")
                # Parse JSON from response
                import json as json_module
                # Find JSON array in response
                match = re.search(r'\[.*?\]', result, re.DOTALL)
                if match:
                    concepts = json_module.loads(match.group())
                    return concepts[:max_concepts]
        except Exception as e:
            logger.warning(f"LLM concept extraction failed: {e}")

        return []

    def generate_research_items(
        self,
        transcript: str,
        concepts: List[str],
        context: str = "agentic AI system with memory, perception, and multi-node cluster"
    ) -> List[Dict[str, Any]]:
        """Generate research items using LLM."""
        client = self._get_client()
        if not client:
            return []

        # Truncate transcript
        if len(transcript) > 6000:
            transcript = transcript[:3000] + "\n[...truncated...]\n" + transcript[-3000:]

        prompt = f"""Based on this technical video transcript, generate actionable research items.

TRANSCRIPT EXCERPT:
{transcript[:4000]}

KEY CONCEPTS IDENTIFIED:
{', '.join(concepts[:15])}

TARGET SYSTEM CONTEXT:
{context}

Generate research items that would help integrate insights from this video into the target system.

Return a JSON array of objects with these fields:
- topic: Brief title (string)
- description: What to research/implement (string)
- priority: "high", "medium", or "low" (string)
- category: "concept", "technique", "tool", "reference", or "integration" (string)
- action_type: "research", "implement", "integrate", or "explore" (string)

Focus on actionable items that connect to: visual reasoning, memory systems, embeddings, reinforcement learning, multi-agent coordination.

Return 5-10 high-quality items. JSON array only:"""

        try:
            response = client.post("/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 1500}
            })

            if response.status_code == 200:
                result = response.json().get("response", "")
                import json as json_module
                # Find JSON array
                match = re.search(r'\[.*\]', result, re.DOTALL)
                if match:
                    items = json_module.loads(match.group())
                    return items
        except Exception as e:
            logger.warning(f"LLM research item generation failed: {e}")

        return []

    def generate_summary(self, transcript: str, max_length: int = 500) -> str:
        """Generate summary using LLM."""
        client = self._get_client()
        if not client:
            return ""

        # Truncate transcript
        if len(transcript) > 8000:
            transcript = transcript[:4000] + "\n[...truncated...]\n" + transcript[-4000:]

        prompt = f"""Summarize this technical video transcript in {max_length} characters or less.

TRANSCRIPT:
{transcript}

Focus on:
- Main technical contributions or findings
- Key techniques or methods discussed
- Practical applications or implications

Write a concise, information-dense summary. No preamble:"""

        try:
            response = client.post("/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 300}
            })

            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}")

        return ""

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


@dataclass
class VideoMetadata:
    """Video metadata container"""
    video_id: str
    url: str
    extracted_at: str
    transcript_language: str = "en"
    duration_seconds: float = 0.0
    word_count: int = 0


@dataclass
class TranscriptSegment:
    """Single transcript segment with timing"""
    start: float
    duration: float
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def timestamp_str(self) -> str:
        mins = int(self.start // 60)
        secs = int(self.start % 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class ResearchItem:
    """Actionable research item extracted from video"""
    topic: str
    description: str
    priority: str  # high, medium, low
    category: str  # concept, technique, tool, reference, question
    timestamp: Optional[str] = None
    related_concepts: List[str] = None
    action_type: str = "research"  # research, implement, integrate, explore

    def __post_init__(self):
        if self.related_concepts is None:
            self.related_concepts = []


@dataclass
class ResearchReport:
    """Complete research report from video analysis"""
    video: VideoMetadata
    summary: str
    key_concepts: List[str]
    research_items: List[ResearchItem]
    full_transcript: str
    segments: List[Dict]
    generated_at: str


class YouTubeResearchPipeline:
    """
    Pipeline for extracting actionable research from YouTube videos.

    Supports both pattern-based and AI-powered extraction:
    - Pattern-based: Fast, works offline, good for technical content
    - AI-powered: Uses Ollama on inference node for deeper understanding
    """

    def __init__(self, output_dir: Optional[Path] = None, use_ai: bool = False, ai_model: str = None):
        """
        Initialize the research pipeline.

        Args:
            output_dir: Directory for saving research reports
            use_ai: Use AI-powered extraction via Ollama (default: False)
            ai_model: Ollama model to use (default: qwen2.5:7b)
        """
        self.output_dir = output_dir or Path("/mnt/agentic-system/research")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not _HAS_TRANSCRIPT_API:
            raise ImportError("youtube-transcript-api required. Install with: pip install youtube-transcript-api")

        self.ytt = YouTubeTranscriptApi()

        # AI extraction setup
        self.use_ai = use_ai
        self._ai_extractor = None
        self._ai_model = ai_model

        if use_ai:
            self._ai_extractor = OllamaExtractor(model=ai_model)
            logger.info(f"AI extraction enabled using {self._ai_extractor.model}")

    def extract_video_id(self, url_or_id: str) -> str:
        """Extract video ID from URL or return if already an ID."""
        if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]+$', url_or_id):
            return url_or_id

        # Parse URL
        parsed = urlparse(url_or_id)

        if 'youtube.com' in parsed.netloc:
            query = parse_qs(parsed.query)
            if 'v' in query:
                return query['v'][0]
        elif 'youtu.be' in parsed.netloc:
            return parsed.path.lstrip('/')

        raise ValueError(f"Could not extract video ID from: {url_or_id}")

    def fetch_transcript(self, video_id: str, language: str = "en") -> Tuple[List[TranscriptSegment], str]:
        """
        Fetch transcript for a video.

        Args:
            video_id: YouTube video ID
            language: Preferred language code

        Returns:
            Tuple of (segments list, language code used)
        """
        try:
            # Try to get transcript in preferred language
            transcript = self.ytt.fetch(video_id)

            segments = []
            for entry in transcript:
                segments.append(TranscriptSegment(
                    start=entry.start,
                    duration=entry.duration,
                    text=entry.text
                ))

            logger.info(f"Fetched {len(segments)} transcript segments")
            return segments, language

        except Exception as e:
            logger.error(f"Failed to fetch transcript: {e}")
            raise

    def get_transcript_around_timestamp(
        self,
        segments: List[TranscriptSegment],
        timestamp: float,
        context_seconds: float = 300
    ) -> List[TranscriptSegment]:
        """Get transcript segments around a specific timestamp."""
        return [
            s for s in segments
            if timestamp - context_seconds <= s.start <= timestamp + context_seconds
        ]

    def build_full_transcript(self, segments: List[TranscriptSegment]) -> str:
        """Combine segments into full transcript text."""
        return " ".join(s.text for s in segments)

    def extract_key_concepts(self, transcript: str) -> List[str]:
        """
        Extract key concepts/topics from transcript.

        Uses AI extraction when available, falls back to pattern matching.
        """
        # Try AI extraction first if enabled
        if self.use_ai and self._ai_extractor:
            ai_concepts = self._ai_extractor.extract_concepts(transcript)
            if ai_concepts:
                logger.info(f"AI extracted {len(ai_concepts)} concepts")
                return ai_concepts
            logger.info("AI extraction failed, falling back to patterns")

        # Pattern-based extraction
        concepts = set()

        # Technical AI/ML terms
        ai_patterns = [
            r'\b(transformer|attention|embedding|latent space|vector|token)\b',
            r'\b(neural network|deep learning|machine learning|reinforcement learning)\b',
            r'\b(GRPO|VPO|PPO|DPO|RLHF|fine.?tun\w*)\b',
            r'\b(vision.?language|multimodal|visual reasoning|vision encoder)\b',
            r'\b(contrastive loss|manifold|probability density|distribution)\b',
            r'\b(GPT|Claude|Qwen|Gemini|OpenAI|Anthropic)\b',
        ]

        for pattern in ai_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            concepts.update(m.lower() if isinstance(m, str) else m[0].lower() for m in matches)

        # Named models/papers (capitalized terms)
        model_matches = re.findall(r'\b([A-Z][a-z]+(?:\s*[0-9]+)?)\b', transcript)
        for match in model_matches:
            if len(match) > 3 and match.lower() not in ['this', 'that', 'here', 'there', 'what', 'when']:
                concepts.add(match)

        return sorted(list(concepts))[:30]  # Top 30 concepts

    def generate_research_items(
        self,
        transcript: str,
        concepts: List[str],
        focus_timestamp: Optional[float] = None
    ) -> List[ResearchItem]:
        """
        Generate actionable research items from transcript analysis.

        Args:
            transcript: Full transcript text
            concepts: Extracted key concepts
            focus_timestamp: Timestamp to focus on (if provided)

        Returns:
            List of ResearchItem objects
        """
        items = []

        # Try AI extraction first if enabled
        if self.use_ai and self._ai_extractor:
            ai_items = self._ai_extractor.generate_research_items(transcript, concepts)
            if ai_items:
                logger.info(f"AI generated {len(ai_items)} research items")
                for item_dict in ai_items:
                    try:
                        items.append(ResearchItem(
                            topic=item_dict.get("topic", "Unknown"),
                            description=item_dict.get("description", ""),
                            priority=item_dict.get("priority", "medium"),
                            category=item_dict.get("category", "concept"),
                            action_type=item_dict.get("action_type", "research"),
                            related_concepts=[]
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to parse AI research item: {e}")
                if items:
                    return items
            logger.info("AI research items failed, falling back to patterns")

        # Pattern-based extraction of research-worthy items

        # Papers/publications mentioned
        paper_patterns = [
            r'paper\s+(?:called|named|titled)?\s*["\']?([^"\']+)["\']?',
            r'publication\s+(?:of|from)?\s*([A-Z][a-z]+)',
            r'(\w+)\s+paper\s+(?:from|by)',
        ]

        for pattern in paper_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            for match in matches[:5]:  # Limit
                items.append(ResearchItem(
                    topic=f"Paper: {match}",
                    description=f"Research paper mentioned in video",
                    priority="high",
                    category="reference",
                    action_type="research",
                    related_concepts=[c for c in concepts if c.lower() in match.lower()]
                ))

        # Technical concepts to explore
        key_technical = [c for c in concepts if any(
            term in c.lower() for term in
            ['grpo', 'vpo', 'embedding', 'latent', 'contrastive', 'manifold', 'reasoning']
        )]

        for concept in key_technical[:10]:
            items.append(ResearchItem(
                topic=concept,
                description=f"Technical concept requiring deeper understanding",
                priority="medium",
                category="concept",
                action_type="research",
                related_concepts=[c for c in concepts if c != concept][:5]
            ))

        # Implementation opportunities
        impl_patterns = [
            r'you can\s+(?:now\s+)?(\w+\s+\w+)',
            r'we\s+(?:can|could)\s+(?:now\s+)?(\w+\s+\w+)',
            r'this\s+(?:allows|enables)\s+(?:us\s+to\s+)?(\w+)',
        ]

        for pattern in impl_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            for match in matches[:3]:
                if len(match) > 5:
                    items.append(ResearchItem(
                        topic=f"Implementation: {match}",
                        description=f"Potential implementation opportunity identified",
                        priority="medium",
                        category="technique",
                        action_type="implement"
                    ))

        # Integration ideas based on agentic system
        agentic_relevant = [
            ("visual reasoning", "Integrate visual reasoning into perception pipeline"),
            ("latent space", "Explore latent space operations for memory compression"),
            ("reinforcement learning", "Apply RL techniques to agent optimization"),
            ("embedding", "Enhance embedding strategies for memory retrieval"),
            ("contrastive", "Use contrastive learning for similarity detection"),
        ]

        for keyword, description in agentic_relevant:
            if keyword in transcript.lower():
                items.append(ResearchItem(
                    topic=f"Integration: {keyword}",
                    description=description,
                    priority="high",
                    category="technique",
                    action_type="integrate",
                    related_concepts=[c for c in concepts if keyword in c.lower()]
                ))

        # Deduplicate by topic
        seen = set()
        unique_items = []
        for item in items:
            if item.topic not in seen:
                seen.add(item.topic)
                unique_items.append(item)

        return unique_items

    def generate_summary(self, transcript: str, concepts: List[str]) -> str:
        """Generate a brief summary of the video content."""
        # Try AI summary first if enabled
        if self.use_ai and self._ai_extractor:
            ai_summary = self._ai_extractor.generate_summary(transcript)
            if ai_summary:
                logger.info("AI generated summary")
                return ai_summary
            logger.info("AI summary failed, falling back to extractive")

        # Simple extractive summary using key sentences
        sentences = re.split(r'[.!?]+', transcript)

        # Score sentences by concept coverage
        scored = []
        for sent in sentences:
            if len(sent.strip()) < 20:
                continue
            score = sum(1 for c in concepts if c.lower() in sent.lower())
            scored.append((score, sent.strip()))

        # Top sentences
        scored.sort(reverse=True)
        top_sentences = [s for _, s in scored[:5]]

        return ". ".join(top_sentences) + "."

    def process_video(
        self,
        url_or_id: str,
        focus_timestamp: Optional[float] = None,
        save_report: bool = True
    ) -> ResearchReport:
        """
        Process a YouTube video and generate research report.

        Args:
            url_or_id: YouTube URL or video ID
            focus_timestamp: Optional timestamp to focus on (seconds)
            save_report: Whether to save report to file

        Returns:
            ResearchReport with all extracted information
        """
        video_id = self.extract_video_id(url_or_id)
        logger.info(f"Processing video: {video_id}")

        # Fetch transcript
        segments, language = self.fetch_transcript(video_id)

        # Build full transcript
        full_transcript = self.build_full_transcript(segments)

        # Calculate duration
        if segments:
            duration = segments[-1].end
        else:
            duration = 0

        # Create metadata
        metadata = VideoMetadata(
            video_id=video_id,
            url=f"https://www.youtube.com/watch?v={video_id}",
            extracted_at=datetime.now().isoformat(),
            transcript_language=language,
            duration_seconds=duration,
            word_count=len(full_transcript.split())
        )

        # Extract concepts
        concepts = self.extract_key_concepts(full_transcript)
        logger.info(f"Extracted {len(concepts)} key concepts")

        # Generate research items
        research_items = self.generate_research_items(full_transcript, concepts, focus_timestamp)
        logger.info(f"Generated {len(research_items)} research items")

        # Generate summary
        summary = self.generate_summary(full_transcript, concepts)

        # Build report
        report = ResearchReport(
            video=metadata,
            summary=summary,
            key_concepts=concepts,
            research_items=research_items,
            full_transcript=full_transcript,
            segments=[asdict(s) for s in segments],
            generated_at=datetime.now().isoformat()
        )

        if save_report:
            self._save_report(report)

        return report

    def _save_report(self, report: ResearchReport) -> Path:
        """Save research report to file."""
        filename = f"youtube_research_{report.video.video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        # Convert to dict for JSON serialization
        report_dict = {
            "video": asdict(report.video),
            "summary": report.summary,
            "key_concepts": report.key_concepts,
            "research_items": [asdict(item) for item in report.research_items],
            "full_transcript": report.full_transcript,
            "segments": report.segments,
            "generated_at": report.generated_at
        }

        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Saved report to: {filepath}")
        return filepath

    def store_in_memory(self, report: ResearchReport) -> Dict[str, Any]:
        """
        Store research findings in the enhanced memory system.

        Returns:
            Dict with storage results
        """
        try:
            from memory_manager import MemoryManager
            mm = MemoryManager()

            results = {"entities_created": [], "episodes_created": []}

            # Create entity for the video
            video_entity = mm.create_entity(
                name=f"youtube_video_{report.video.video_id}",
                entity_type="research_source",
                observations=[
                    f"URL: {report.video.url}",
                    f"Summary: {report.summary[:500]}",
                    f"Key concepts: {', '.join(report.key_concepts[:10])}",
                    f"Duration: {report.video.duration_seconds:.0f}s",
                    f"Word count: {report.video.word_count}"
                ]
            )
            results["entities_created"].append(video_entity)

            # Create entities for high-priority research items
            for item in report.research_items:
                if item.priority == "high":
                    entity = mm.create_entity(
                        name=f"research_item_{hashlib.md5(item.topic.encode()).hexdigest()[:8]}",
                        entity_type="research_item",
                        observations=[
                            f"Topic: {item.topic}",
                            f"Description: {item.description}",
                            f"Category: {item.category}",
                            f"Action: {item.action_type}",
                            f"Source: youtube_video_{report.video.video_id}"
                        ]
                    )
                    results["entities_created"].append(entity)

            logger.info(f"Stored {len(results['entities_created'])} entities in memory")
            return results

        except ImportError:
            logger.warning("Memory manager not available - skipping memory storage")
            return {"error": "Memory manager not available"}
        except Exception as e:
            logger.error(f"Failed to store in memory: {e}")
            return {"error": str(e)}


def format_research_report(report: ResearchReport) -> str:
    """Format research report for display."""
    lines = [
        "=" * 60,
        "YOUTUBE RESEARCH REPORT",
        "=" * 60,
        f"\nVideo ID: {report.video.video_id}",
        f"URL: {report.video.url}",
        f"Duration: {report.video.duration_seconds / 60:.1f} minutes",
        f"Word Count: {report.video.word_count}",
        f"\n--- SUMMARY ---",
        report.summary[:500] + "..." if len(report.summary) > 500 else report.summary,
        f"\n--- KEY CONCEPTS ({len(report.key_concepts)}) ---",
    ]

    for concept in report.key_concepts[:15]:
        lines.append(f"  - {concept}")

    if len(report.key_concepts) > 15:
        lines.append(f"  ... and {len(report.key_concepts) - 15} more")

    lines.append(f"\n--- RESEARCH ITEMS ({len(report.research_items)}) ---")

    # Group by priority
    for priority in ["high", "medium", "low"]:
        items = [i for i in report.research_items if i.priority == priority]
        if items:
            lines.append(f"\n[{priority.upper()} PRIORITY]")
            for item in items[:10]:
                lines.append(f"  [{item.action_type.upper()}] {item.topic}")
                lines.append(f"    Category: {item.category}")
                lines.append(f"    {item.description}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Research Pipeline")
    parser.add_argument("--url", type=str, help="YouTube video URL")
    parser.add_argument("--video-id", type=str, help="YouTube video ID")
    parser.add_argument("--timestamp", type=int, help="Focus timestamp in seconds")
    parser.add_argument("--output-dir", type=str, help="Output directory for reports")
    parser.add_argument("--store-memory", action="store_true", help="Store in memory system")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--use-ai", action="store_true",
                       help="Use AI-powered extraction via Ollama (default: pattern-based)")
    parser.add_argument("--ai-model", type=str, default=None,
                       help="Ollama model for AI extraction (default: qwen2.5:7b)")

    args = parser.parse_args()

    if not args.url and not args.video_id:
        parser.error("Either --url or --video-id is required")

    video_input = args.url or args.video_id

    output_dir = Path(args.output_dir) if args.output_dir else None
    pipeline = YouTubeResearchPipeline(
        output_dir=output_dir,
        use_ai=args.use_ai,
        ai_model=args.ai_model
    )

    try:
        report = pipeline.process_video(
            video_input,
            focus_timestamp=args.timestamp
        )

        if args.store_memory:
            storage_result = pipeline.store_in_memory(report)
            print(f"\nMemory storage: {storage_result}")

        if args.json:
            print(json.dumps({
                "video": asdict(report.video),
                "summary": report.summary,
                "key_concepts": report.key_concepts,
                "research_items": [asdict(i) for i in report.research_items],
                "generated_at": report.generated_at
            }, indent=2))
        else:
            print(format_research_report(report))

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
