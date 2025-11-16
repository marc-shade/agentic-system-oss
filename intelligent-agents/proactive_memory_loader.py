#!/usr/bin/env python3
"""
Proactive Memory Context Loader

Automatically searches enhanced-memory before complex tasks to load
relevant context from past solutions, patterns, and learnings.

Integrates with:
- Task consumer (before task execution)
- Agent spawning (before agent initialization)
- Claude Code sessions (on complex reasoning)

This fills a major gap: Enhanced-memory has 4,873 entities but they're
only queried reactively. This makes memory proactive.
"""

import json
import logging
import pickle
import sqlite3
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/mnt/agentic-system/logs/proactive_memory.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('proactive-memory')

class ProactiveMemoryLoader:
    """Proactively loads relevant context from enhanced-memory"""

    def __init__(self):
        self.memory_db = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        self.min_relevance_score = 0.6
        self.max_context_items = 5

    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text for search"""
        # Simple keyword extraction (can be enhanced with NLP)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in common_words]
        return keywords[:10]  # Top 10 keywords

    def decompress_data(self, compressed: bytes) -> Any:
        """Decompress and deserialize entity data"""
        try:
            decompressed = zlib.decompress(compressed)
            return pickle.loads(decompressed)
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            return None

    def search_memory(self, query: str, entity_type: Optional[str] = None) -> List[Dict]:
        """Search enhanced-memory for relevant context"""
        try:
            if not self.memory_db.exists():
                logger.warning(f"Memory DB not found at {self.memory_db}")
                return []

            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()

            # Build search query with correct column names
            sql = """
                SELECT name, entity_type, compressed_data, created_at
                FROM entities
                WHERE name LIKE ?
            """
            params = [f"%{query}%"]

            if entity_type:
                sql += " AND entity_type = ?"
                params.append(entity_type)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(self.max_context_items)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                # Decompress the data
                observations = []
                if row[2]:  # compressed_data
                    data = self.decompress_data(row[2])
                    if data and isinstance(data, dict):
                        observations = data.get('observations', [])

                results.append({
                    'name': row[0],
                    'type': row[1],
                    'observations': observations,
                    'created_at': row[3]
                })

            logger.info(f"Found {len(results)} relevant memories for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return []

    def load_context_for_task(self, task_title: str, task_description: str) -> Dict:
        """Load relevant context before executing a task"""
        logger.info(f"Loading context for task: {task_title}")

        # Extract keywords from task
        keywords = self.extract_keywords(f"{task_title} {task_description}")

        context = {
            'task': task_title,
            'loaded_at': datetime.now().isoformat(),
            'relevant_memories': [],
            'similar_solutions': [],
            'patterns': [],
            'recommendations': []
        }

        # Search for similar past tasks
        for keyword in keywords[:3]:  # Top 3 keywords
            memories = self.search_memory(keyword)
            context['relevant_memories'].extend(memories)

        # Search for solution patterns
        if 'implement' in task_title.lower() or 'fix' in task_title.lower():
            solutions = self.search_memory('solution', entity_type='pattern')
            context['similar_solutions'].extend(solutions)

        # Search for known patterns
        patterns = self.search_memory('pattern', entity_type='system_learning')
        context['patterns'].extend(patterns)

        # Deduplicate
        seen_names = set()
        for key in ['relevant_memories', 'similar_solutions', 'patterns']:
            unique = []
            for item in context[key]:
                if item['name'] not in seen_names:
                    seen_names.add(item['name'])
                    unique.append(item)
            context[key] = unique

        # Generate recommendations
        if context['similar_solutions']:
            context['recommendations'].append(
                f"Found {len(context['similar_solutions'])} similar solutions from past work"
            )
        if context['patterns']:
            context['recommendations'].append(
                f"Identified {len(context['patterns'])} relevant patterns"
            )

        logger.info(f"Context loaded: {len(context['relevant_memories'])} memories, "
                   f"{len(context['similar_solutions'])} solutions, "
                   f"{len(context['patterns'])} patterns")

        return context

    def load_context_for_query(self, query: str) -> Dict:
        """Load relevant context for a complex query/reasoning task"""
        logger.info(f"Loading context for query: {query[:100]}...")

        keywords = self.extract_keywords(query)

        context = {
            'query': query[:200],
            'loaded_at': datetime.now().isoformat(),
            'relevant_knowledge': [],
            'past_reasoning': [],
            'recommendations': []
        }

        # Search for relevant knowledge
        for keyword in keywords[:5]:  # Top 5 keywords
            knowledge = self.search_memory(keyword)
            context['relevant_knowledge'].extend(knowledge)

        # Search for past reasoning patterns
        reasoning = self.search_memory('reasoning', entity_type='analysis')
        context['past_reasoning'].extend(reasoning)

        # Deduplicate
        seen_names = set()
        unique_knowledge = []
        for item in context['relevant_knowledge']:
            if item['name'] not in seen_names:
                seen_names.add(item['name'])
                unique_knowledge.append(item)
        context['relevant_knowledge'] = unique_knowledge

        if context['relevant_knowledge']:
            context['recommendations'].append(
                f"Loaded {len(context['relevant_knowledge'])} relevant knowledge items"
            )

        logger.info(f"Context loaded: {len(context['relevant_knowledge'])} items")
        return context

    def format_context_for_prompt(self, context: Dict) -> str:
        """Format context into a string suitable for prompt injection"""
        lines = ["=== RELEVANT CONTEXT FROM MEMORY ===\n"]

        if context.get('relevant_memories'):
            lines.append("📚 Similar Past Work:")
            for mem in context['relevant_memories'][:3]:  # Top 3
                lines.append(f"  - {mem['name']} ({mem['type']})")
                if mem['observations']:
                    lines.append(f"    • {mem['observations'][0][:100]}...")
            lines.append("")

        if context.get('similar_solutions'):
            lines.append("💡 Past Solutions:")
            for sol in context['similar_solutions'][:2]:  # Top 2
                lines.append(f"  - {sol['name']}")
                if sol['observations']:
                    lines.append(f"    • {sol['observations'][0][:100]}...")
            lines.append("")

        if context.get('patterns'):
            lines.append("🔍 Known Patterns:")
            for pat in context['patterns'][:2]:  # Top 2
                lines.append(f"  - {pat['name']}")
            lines.append("")

        if context.get('recommendations'):
            lines.append("⚡ Recommendations:")
            for rec in context['recommendations']:
                lines.append(f"  - {rec}")
            lines.append("")

        lines.append("===================================\n")
        return "\n".join(lines)

def load_context_for_task(task_title: str, task_description: str) -> str:
    """
    Public API: Load context for a task
    Returns formatted context string for prompt injection
    """
    loader = ProactiveMemoryLoader()
    context = loader.load_context_for_task(task_title, task_description)
    return loader.format_context_for_prompt(context)

def load_context_for_query(query: str) -> str:
    """
    Public API: Load context for a complex query
    Returns formatted context string for prompt injection
    """
    loader = ProactiveMemoryLoader()
    context = loader.load_context_for_query(query)
    return loader.format_context_for_prompt(context)

if __name__ == "__main__":
    # Test the loader
    loader = ProactiveMemoryLoader()

    # Test task context loading
    context = loader.load_context_for_task(
        "Implement user authentication",
        "Add OAuth2 authentication with JWT tokens"
    )
    print(loader.format_context_for_prompt(context))
