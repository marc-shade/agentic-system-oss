#!/usr/bin/env python3
"""
Research Daemon - The Curiosity Loop

Based on Free Energy Principle: Epistemic foraging to reduce uncertainty.

This daemon maintains a Markov blanket around knowledge state and triggers
research activities when knowledge gaps exceed threshold.

Key insight from Friston: Curious agents minimize expected free energy
by seeking information that resolves uncertainty about the world.
This is epistemic action - acting to reduce uncertainty.

From Levin: Knowledge gaps are like bioelectric gradients - they create
"morphogenetic fields" that guide information seeking behavior.
"""

import asyncio
import json
import logging
import os
import signal
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

# Configuration
CONFIG = {
    "check_interval_seconds": 300,  # Check every 5 minutes
    "gap_threshold": 0.6,           # Minimum severity to consider
    "max_concurrent_research": 2,   # Don't overwhelm resources
    "research_timeout_minutes": 30,
    "memory_db_path": os.path.expanduser("~/.claude/enhanced_memories/memory.db"),
    "state_file": "/mnt/agentic-system/databases/research_daemon_state.json",
    "log_file": "/var/log/research-daemon.log",
    "arxiv_enabled": True,
    "semantic_scholar_enabled": True,
    "video_learning_enabled": True,
}

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["log_file"], mode='a')
        if os.access(os.path.dirname(CONFIG["log_file"]) or '.', os.W_OK)
        else logging.StreamHandler()
    ]
)
logger = logging.getLogger("ResearchDaemon")


@dataclass
class KnowledgeGap:
    """A gap in knowledge that needs filling"""
    id: int
    domain: str
    description: str
    severity: float
    gap_type: str  # factual, procedural, conceptual, meta
    discovered_at: datetime
    status: str
    learning_progress: float = 0.0


@dataclass
class ResearchPlan:
    """Plan for filling a knowledge gap"""
    gap: KnowledgeGap
    search_queries: List[str]
    sources: List[str]  # arxiv, semantic_scholar, youtube, web
    expected_effort: str  # low, medium, high
    priority: float


class ResearchDaemon:
    """
    Epistemic foraging daemon.
    Minimizes expected free energy by reducing uncertainty.
    """

    def __init__(self):
        self.running = True
        self.active_research: Dict[int, asyncio.Task] = {}
        self.state = self._load_state()

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGUSR1, self._handle_force_research)

    def _load_state(self) -> Dict:
        state_path = Path(CONFIG["state_file"])
        if state_path.exists():
            try:
                return json.loads(state_path.read_text())
            except:
                pass
        return {
            "total_research_sessions": 0,
            "gaps_filled": 0,
            "papers_processed": 0,
            "videos_processed": 0,
            "last_research": None,
        }

    def _save_state(self):
        state_path = Path(CONFIG["state_file"])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.state, indent=2, default=str))

    def _handle_shutdown(self, signum, frame):
        logger.info("Shutting down research daemon")
        self.running = False

    def _handle_force_research(self, signum, frame):
        logger.info("Forcing research cycle (SIGUSR1)")
        asyncio.create_task(self._research_cycle(force=True))

    # ═══════════════════════════════════════════════════════════════════
    # SENSORY - Observe knowledge gaps
    # ═══════════════════════════════════════════════════════════════════

    async def sense_knowledge_gaps(self) -> List[KnowledgeGap]:
        """Sense open knowledge gaps from memory"""
        gaps = []
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return gaps

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT gap_id, domain, gap_description, severity, gap_type,
                       discovered_at, status, learning_progress
                FROM knowledge_gaps
                WHERE status IN ('open', 'learning')
                AND severity >= ?
                ORDER BY severity DESC, discovered_at ASC
            """, (CONFIG["gap_threshold"],))

            for row in cursor.fetchall():
                gaps.append(KnowledgeGap(
                    id=row[0],
                    domain=row[1],
                    description=row[2],
                    severity=row[3],
                    gap_type=row[4],
                    discovered_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    status=row[6],
                    learning_progress=row[7] or 0.0
                ))

            conn.close()
        except Exception as e:
            logger.warning(f"Failed to sense knowledge gaps: {e}")
        return gaps

    # ═══════════════════════════════════════════════════════════════════
    # PREDICTION - Generate research plans
    # ═══════════════════════════════════════════════════════════════════

    def plan_research(self, gap: KnowledgeGap) -> ResearchPlan:
        """Generate research plan for a knowledge gap"""

        # Determine search queries
        base_queries = [gap.description]
        domain_queries = [f"{gap.domain} {gap.description}"]

        # Add specificity based on gap type
        if gap.gap_type == "procedural":
            queries = domain_queries + [f"how to {gap.description}", f"{gap.description} tutorial implementation"]
        elif gap.gap_type == "conceptual":
            queries = domain_queries + [f"{gap.description} theory principles", f"{gap.description} explained"]
        elif gap.gap_type == "factual":
            queries = domain_queries + [f"{gap.description} research", f"{gap.description} state of the art"]
        else:  # meta
            queries = domain_queries + [f"{gap.description} methodology", f"learning {gap.description}"]

        # Determine sources based on domain
        sources = []
        if gap.domain in ["machine learning", "ai", "neural networks", "optimization", "computer science"]:
            sources.extend(["arxiv", "semantic_scholar"])
        if gap.gap_type == "procedural":
            sources.append("youtube")
        sources.append("web")

        # Effort estimation
        if gap.severity > 0.8:
            effort = "high"
        elif gap.severity > 0.6:
            effort = "medium"
        else:
            effort = "low"

        return ResearchPlan(
            gap=gap,
            search_queries=queries[:5],
            sources=sources,
            expected_effort=effort,
            priority=gap.severity * (1.0 - gap.learning_progress)
        )

    # ═══════════════════════════════════════════════════════════════════
    # ACTIVE - Execute research to reduce uncertainty
    # ═══════════════════════════════════════════════════════════════════

    async def execute_research(self, plan: ResearchPlan) -> Dict[str, Any]:
        """Execute research plan and store findings"""
        logger.info(f"Researching: {plan.gap.description}")
        results = {
            "gap_id": plan.gap.id,
            "papers_found": 0,
            "videos_found": 0,
            "insights_stored": 0,
            "progress_made": 0.0,
        }

        try:
            # Research via arXiv
            if "arxiv" in plan.sources and CONFIG["arxiv_enabled"]:
                arxiv_results = await self._search_arxiv(plan.search_queries[0])
                results["papers_found"] += len(arxiv_results)

                for paper in arxiv_results[:3]:  # Top 3 papers
                    await self._store_paper_knowledge(paper, plan.gap)
                    results["insights_stored"] += 1

            # Research via Semantic Scholar
            if "semantic_scholar" in plan.sources and CONFIG["semantic_scholar_enabled"]:
                ss_results = await self._search_semantic_scholar(plan.search_queries[0])
                results["papers_found"] += len(ss_results)

                for paper in ss_results[:2]:  # Top 2
                    await self._store_paper_knowledge(paper, plan.gap)
                    results["insights_stored"] += 1

            # Calculate progress
            if results["insights_stored"] > 0:
                progress_increment = min(0.3, results["insights_stored"] * 0.1)
                results["progress_made"] = progress_increment

                # Update gap status
                await self._update_gap_progress(
                    plan.gap.id,
                    plan.gap.learning_progress + progress_increment
                )

        except Exception as e:
            logger.error(f"Research failed for gap {plan.gap.id}: {e}")

        return results

    async def _search_arxiv(self, query: str) -> List[Dict]:
        """Search arXiv for papers"""
        try:
            async with httpx.AsyncClient() as client:
                # Using arxiv API
                url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": 5,
                    "sortBy": "relevance",
                }
                response = await client.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    # Parse XML response (simplified)
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(response.text)

                    papers = []
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        papers.append({
                            "title": title.text.strip() if title is not None else "",
                            "abstract": summary.text.strip() if summary is not None else "",
                            "source": "arxiv"
                        })
                    return papers
        except Exception as e:
            logger.debug(f"arXiv search failed: {e}")
        return []

    async def _search_semantic_scholar(self, query: str) -> List[Dict]:
        """Search Semantic Scholar for papers"""
        try:
            async with httpx.AsyncClient() as client:
                url = "https://api.semanticscholar.org/graph/v1/paper/search"
                params = {
                    "query": query,
                    "limit": 5,
                    "fields": "title,abstract,citationCount"
                }
                response = await client.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "title": p.get("title", ""),
                            "abstract": p.get("abstract", ""),
                            "citations": p.get("citationCount", 0),
                            "source": "semantic_scholar"
                        }
                        for p in data.get("data", [])
                    ]
        except Exception as e:
            logger.debug(f"Semantic Scholar search failed: {e}")
        return []

    async def _store_paper_knowledge(self, paper: Dict, gap: KnowledgeGap):
        """Store paper knowledge in memory"""
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Store as semantic memory concept
            cursor.execute("""
                INSERT INTO semantic_concepts
                (concept_name, concept_type, definition, confidence_score, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                paper.get("title", "")[:200],
                "research_finding",
                paper.get("abstract", "")[:2000],
                0.6,
                datetime.now().isoformat()
            ))

            conn.commit()
            conn.close()

            logger.info(f"Stored paper: {paper.get('title', '')[:50]}...")

        except Exception as e:
            logger.warning(f"Failed to store paper knowledge: {e}")

    async def _update_gap_progress(self, gap_id: int, new_progress: float):
        """Update knowledge gap learning progress"""
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            new_status = "resolved" if new_progress >= 1.0 else "learning"
            cursor.execute("""
                UPDATE knowledge_gaps
                SET learning_progress = ?, status = ?, resolved_at = ?
                WHERE id = ?
            """, (
                min(1.0, new_progress),
                new_status,
                datetime.now().isoformat() if new_status == "resolved" else None,
                gap_id
            ))

            conn.commit()
            conn.close()

            if new_status == "resolved":
                logger.info(f"Knowledge gap {gap_id} resolved!")
                self.state["gaps_filled"] += 1

        except Exception as e:
            logger.warning(f"Failed to update gap progress: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # MAIN LOOP - Epistemic foraging cycle
    # ═══════════════════════════════════════════════════════════════════

    async def _research_cycle(self, force: bool = False):
        """Execute one research cycle"""
        # Sense knowledge gaps
        gaps = await self.sense_knowledge_gaps()
        if not gaps:
            logger.debug("No knowledge gaps above threshold")
            return

        logger.info(f"Found {len(gaps)} knowledge gaps to research")

        # Generate research plans
        plans = [self.plan_research(gap) for gap in gaps]
        plans.sort(key=lambda p: p.priority, reverse=True)

        # Execute top priorities (respecting concurrency limit)
        active_count = len([t for t in self.active_research.values() if not t.done()])
        available_slots = CONFIG["max_concurrent_research"] - active_count

        if available_slots <= 0 and not force:
            logger.debug("All research slots occupied")
            return

        for plan in plans[:available_slots]:
            if plan.gap.id not in self.active_research or self.active_research[plan.gap.id].done():
                task = asyncio.create_task(self.execute_research(plan))
                self.active_research[plan.gap.id] = task
                self.state["total_research_sessions"] += 1
                self.state["last_research"] = datetime.now().isoformat()

        self._save_state()

    async def run(self):
        """Main daemon loop"""
        logger.info("═══ RESEARCH DAEMON STARTING ═══")
        logger.info("Epistemic foraging active")
        logger.info(f"Gap threshold: {CONFIG['gap_threshold']}")
        logger.info(f"Check interval: {CONFIG['check_interval_seconds']}s")

        while self.running:
            try:
                await self._research_cycle()
                await asyncio.sleep(CONFIG["check_interval_seconds"])

                # Clean up completed tasks
                completed = [gid for gid, task in self.active_research.items() if task.done()]
                for gid in completed:
                    del self.active_research[gid]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in research cycle: {e}")
                await asyncio.sleep(60)

        logger.info("═══ RESEARCH DAEMON STOPPED ═══")


def main():
    daemon = ResearchDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
