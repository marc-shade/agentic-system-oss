"""Knowledge Gap Researcher - Auto-researches high-severity knowledge gaps."""

import asyncio
import aiosqlite
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..utils.config import get_path, get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class GapResearcher:
    """
    Automatically researches high-severity knowledge gaps.

    Responsibilities:
    - Monitor knowledge gaps with severity > threshold
    - Search arXiv and Semantic Scholar for relevant papers
    - Fetch educational video transcripts
    - Store findings in enhanced-memory
    - Update gap learning_progress
    """

    def __init__(self, config: dict):
        """Initialize Gap Researcher.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.memory_db_path = get_path("memory_db", config)

        # Configuration
        self.severity_threshold = get_config_value(
            "thresholds.gap_severity_auto_research", 0.7, config
        )
        self.max_concurrent = get_config_value(
            "components.gap_researcher.max_concurrent_research", 2, config
        )

        # Research sources
        self.sources = get_config_value(
            "components.gap_researcher.sources",
            ["arxiv", "semantic_scholar"],
            config,
        )

        # Remote inference for processing (never use local CPU)
        self.ollama_host = get_config_value(
            "cluster.ollama_host", "http://192.168.1.186:11434", config
        )

        logger.info(
            "gap_researcher_initialized",
            memory_db=str(self.memory_db_path),
            severity_threshold=self.severity_threshold,
            sources=self.sources,
        )

    async def research_gaps(self) -> Dict[str, Any]:
        """Research all high-severity knowledge gaps.

        Returns:
            Research report
        """
        logger.info("starting_gap_research")

        try:
            # Get high-severity gaps
            gaps = await self._get_high_severity_gaps()

            report = {
                "researched_at": datetime.now().isoformat(),
                "gaps_found": len(gaps),
                "gaps_researched": [],
                "findings": [],
                "errors": [],
            }

            if not gaps:
                logger.info("no_gaps_to_research")
                return report

            # Research gaps (limited concurrency)
            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def research_with_limit(gap):
                async with semaphore:
                    return await self._research_gap(gap)

            tasks = [research_with_limit(gap) for gap in gaps[:5]]  # Max 5 per cycle
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for gap, result in zip(gaps, results):
                if isinstance(result, Exception):
                    report["errors"].append({
                        "gap_id": gap["gap_id"],
                        "error": str(result),
                    })
                else:
                    report["gaps_researched"].append(gap["gap_id"])
                    report["findings"].extend(result.get("findings", []))

            logger.info(
                "gap_research_complete",
                researched=len(report["gaps_researched"]),
                findings=len(report["findings"]),
                errors=len(report["errors"]),
            )

            return report

        except Exception as e:
            logger.error("gap_research_failed", error=str(e))
            return {"error": str(e), "researched_at": datetime.now().isoformat()}

    async def _get_high_severity_gaps(self) -> List[Dict[str, Any]]:
        """Get knowledge gaps above severity threshold.

        Returns:
            List of gap dictionaries
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT gap_id, agent_id, domain, gap_description, gap_type,
                       severity, status, learning_progress
                FROM knowledge_gaps
                WHERE status = 'open'
                  AND severity >= ?
                ORDER BY severity DESC
                """,
                (self.severity_threshold,),
            )

            gaps = [dict(row) for row in await cursor.fetchall()]
            logger.debug("found_high_severity_gaps", count=len(gaps))

            return gaps

    async def _research_gap(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Research a single knowledge gap.

        Args:
            gap: Gap dictionary

        Returns:
            Research results
        """
        gap_id = gap["gap_id"]
        domain = gap["domain"]
        description = gap["gap_description"]

        logger.info("researching_gap", gap_id=gap_id, domain=domain)

        findings = []

        # Search arXiv
        if "arxiv" in self.sources:
            arxiv_results = await self._search_arxiv(description)
            findings.extend(arxiv_results)

        # Search Semantic Scholar
        if "semantic_scholar" in self.sources:
            ss_results = await self._search_semantic_scholar(description)
            findings.extend(ss_results)

        # Store findings in memory
        if findings:
            await self._store_findings(gap, findings)

            # Update gap progress
            progress = min(0.5, gap.get("learning_progress", 0) + 0.1 * len(findings))
            await self._update_gap_progress(gap_id, progress)

        return {
            "gap_id": gap_id,
            "findings": findings,
            "sources_searched": self.sources,
        }

    async def _search_arxiv(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search arXiv for papers.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of paper findings
        """
        try:
            # Use arXiv API
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Clean query for arXiv
                clean_query = query.replace(":", " ").replace("-", " ")[:200]

                response = await client.get(
                    "http://export.arxiv.org/api/query",
                    params={
                        "search_query": f"all:{clean_query}",
                        "max_results": max_results,
                        "sortBy": "relevance",
                    },
                )

                if response.status_code != 200:
                    logger.warning("arxiv_search_failed", status=response.status_code)
                    return []

                # Parse XML response (simple extraction)
                content = response.text
                findings = []

                # Extract entries (basic parsing)
                import re
                entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)

                for entry in entries[:max_results]:
                    title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    id_match = re.search(r'<id>(.*?)</id>', entry)

                    if title_match and summary_match:
                        findings.append({
                            "source": "arxiv",
                            "title": title_match.group(1).strip().replace("\n", " "),
                            "summary": summary_match.group(1).strip()[:500],
                            "url": id_match.group(1) if id_match else None,
                        })

                logger.debug("arxiv_results", count=len(findings))
                return findings

        except Exception as e:
            logger.warning("arxiv_search_error", error=str(e))
            return []

    async def _search_semantic_scholar(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Search Semantic Scholar for papers.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of paper findings
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": query[:200],
                        "limit": max_results,
                        "fields": "title,abstract,citationCount,year",
                    },
                )

                if response.status_code != 200:
                    logger.warning(
                        "semantic_scholar_search_failed",
                        status=response.status_code,
                    )
                    return []

                data = response.json()
                findings = []

                for paper in data.get("data", []):
                    findings.append({
                        "source": "semantic_scholar",
                        "title": paper.get("title", ""),
                        "summary": (paper.get("abstract") or "")[:500],
                        "citations": paper.get("citationCount", 0),
                        "year": paper.get("year"),
                    })

                logger.debug("semantic_scholar_results", count=len(findings))
                return findings

        except Exception as e:
            logger.warning("semantic_scholar_search_error", error=str(e))
            return []

    async def _store_findings(self, gap: Dict[str, Any], findings: List[Dict[str, Any]]) -> None:
        """Store research findings in memory.

        Args:
            gap: Original gap
            findings: Research findings
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            for finding in findings:
                # Store as observation on the gap
                observation = f"[{finding['source']}] {finding['title']}: {finding.get('summary', '')[:200]}"

                # This would typically use the enhanced-memory MCP
                # For now, we'll add to a research_findings table
                await db.execute(
                    """
                    INSERT OR IGNORE INTO research_findings
                    (gap_id, source, title, summary, url, found_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        gap["gap_id"],
                        finding["source"],
                        finding["title"],
                        finding.get("summary", ""),
                        finding.get("url"),
                    ),
                )

            await db.commit()

    async def _update_gap_progress(self, gap_id: int, progress: float) -> None:
        """Update knowledge gap learning progress.

        Args:
            gap_id: Gap ID
            progress: New progress value (0.0-1.0)
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            await db.execute(
                """
                UPDATE knowledge_gaps
                SET learning_progress = ?, updated_at = datetime('now')
                WHERE gap_id = ?
                """,
                (progress, gap_id),
            )
            await db.commit()

            logger.debug("updated_gap_progress", gap_id=gap_id, progress=progress)

    async def ensure_tables(self) -> None:
        """Ensure required tables exist."""
        async with aiosqlite.connect(self.memory_db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS research_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gap_id INTEGER,
                    source TEXT,
                    title TEXT,
                    summary TEXT,
                    url TEXT,
                    found_at TEXT,
                    UNIQUE(gap_id, source, title)
                )
                """
            )
            await db.commit()
