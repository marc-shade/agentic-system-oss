#!/usr/bin/env python3
"""
Agent Refinement Engine for Deep Learning Cycle
Week 5 Phase 4: Autonomous Agent Improvement

This module analyzes agent performance, optimizes prompts, improves tool selection,
and tracks agent effectiveness improvements.
"""

import json
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
AGENTS_DIR = Path("/Users/marc/.claude/agents")
AGENT_REFINEMENTS_DB = Path("/mnt/agentic-system/databases/agent_refinements.db")

class RefinementType(Enum):
    """Types of agent refinements"""
    TOOL_OPTIMIZATION = "tool_optimization"           # Better tool selection
    PROMPT_IMPROVEMENT = "prompt_improvement"         # Clearer instructions
    MODEL_SELECTION = "model_selection"               # Appropriate model choice
    MEMORY_INTEGRATION = "memory_integration"         # Better memory usage
    ERROR_HANDLING = "error_handling"                 # Improved error recovery
    SPECIALIZATION = "specialization"                 # Focused expertise

class AgentStatus(Enum):
    """Agent refinement status"""
    ANALYZING = "analyzing"
    PENDING_REFINEMENT = "pending_refinement"
    REFINED = "refined"
    TESTING = "testing"
    DEPLOYED = "deployed"
    FAILED = "failed"

@dataclass
class Agent:
    """Represents a Claude agent"""
    agent_id: str
    name: str
    description: str
    tools: List[str]
    model: str
    file_path: Path
    content: str
    use_count: int
    success_rate: Optional[float]
    avg_execution_time: Optional[float]

@dataclass
class AgentRefinement:
    """Represents an agent refinement"""
    refinement_id: str
    agent_id: str
    refinement_type: RefinementType
    description: str
    original_content: str
    refined_content: str
    confidence: float
    status: AgentStatus
    created_at: datetime
    applied_at: Optional[datetime]
    effectiveness: float
    success_rate_before: Optional[float]
    success_rate_after: Optional[float]

@dataclass
class AgentPerformanceMetrics:
    """Agent performance metrics"""
    agent_id: str
    period_start: datetime
    period_end: datetime
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    avg_execution_time: float
    tool_usage: Dict[str, int]
    common_errors: List[str]

class AgentRefinementDatabase:
    """Manages agent refinement storage and tracking"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize refinement database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Agent refinements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_refinements (
                refinement_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                refinement_type TEXT NOT NULL,
                description TEXT NOT NULL,
                original_content TEXT NOT NULL,
                refined_content TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                applied_at TIMESTAMP,
                effectiveness REAL DEFAULT 0.0,
                success_rate_before REAL,
                success_rate_after REAL
            )
        """)

        # Agent performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                invoked_at TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL,
                execution_time_ms INTEGER,
                tools_used TEXT,
                error_message TEXT,
                task_context TEXT
            )
        """)

        # Agent metrics aggregation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_metrics (
                agent_id TEXT PRIMARY KEY,
                total_invocations INTEGER DEFAULT 0,
                successful_invocations INTEGER DEFAULT 0,
                failed_invocations INTEGER DEFAULT 0,
                avg_execution_time REAL DEFAULT 0.0,
                success_rate REAL DEFAULT 0.0,
                last_invoked TIMESTAMP,
                last_updated TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_refinements_agent
            ON agent_refinements(agent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_performance_agent
            ON agent_performance(agent_id)
        """)

        conn.commit()
        conn.close()

    def store_refinement(self, refinement: AgentRefinement):
        """Store an agent refinement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO agent_refinements
            (refinement_id, agent_id, refinement_type, description,
             original_content, refined_content, confidence, status,
             created_at, applied_at, effectiveness, success_rate_before,
             success_rate_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            refinement.refinement_id,
            refinement.agent_id,
            refinement.refinement_type.value,
            refinement.description,
            refinement.original_content,
            refinement.refined_content,
            refinement.confidence,
            refinement.status.value,
            refinement.created_at.isoformat(),
            refinement.applied_at.isoformat() if refinement.applied_at else None,
            refinement.effectiveness,
            refinement.success_rate_before,
            refinement.success_rate_after
        ))

        conn.commit()
        conn.close()

    def get_pending_refinements(self, min_confidence: float = 0.75) -> List[AgentRefinement]:
        """Get pending refinements above confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT refinement_id, agent_id, refinement_type, description,
                   original_content, refined_content, confidence, status,
                   created_at, applied_at, effectiveness, success_rate_before,
                   success_rate_after
            FROM agent_refinements
            WHERE status = ? AND confidence >= ?
            ORDER BY confidence DESC
        """, (AgentStatus.PENDING_REFINEMENT.value, min_confidence))

        rows = cursor.fetchall()
        conn.close()

        refinements = []
        for row in rows:
            refinements.append(AgentRefinement(
                refinement_id=row[0],
                agent_id=row[1],
                refinement_type=RefinementType(row[2]),
                description=row[3],
                original_content=row[4],
                refined_content=row[5],
                confidence=row[6],
                status=AgentStatus(row[7]),
                created_at=datetime.fromisoformat(row[8]),
                applied_at=datetime.fromisoformat(row[9]) if row[9] else None,
                effectiveness=row[10],
                success_rate_before=row[11],
                success_rate_after=row[12]
            ))

        return refinements

    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT total_invocations, successful_invocations, failed_invocations,
                   avg_execution_time, success_rate, last_invoked
            FROM agent_metrics
            WHERE agent_id = ?
        """, (agent_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "total_invocations": row[0],
            "successful_invocations": row[1],
            "failed_invocations": row[2],
            "avg_execution_time": row[3],
            "success_rate": row[4],
            "last_invoked": row[5]
        }

class AgentAnalyzer:
    """Analyzes agent effectiveness and identifies improvement opportunities"""

    def __init__(self, agents_dir: Path, refinements_db: AgentRefinementDatabase):
        self.agents_dir = agents_dir
        self.refinements_db = refinements_db

    def load_agents(self) -> List[Agent]:
        """Load all agents from agents directory"""
        agents = []

        # Get all .md files in agents directory
        agent_files = list(self.agents_dir.glob("*.md"))

        for agent_file in agent_files:
            try:
                agent = self._parse_agent_file(agent_file)
                if agent:
                    agents.append(agent)
            except Exception as e:
                print(f"Warning: Failed to parse {agent_file.name}: {e}")

        return agents

    def _parse_agent_file(self, file_path: Path) -> Optional[Agent]:
        """Parse agent markdown file"""
        content = file_path.read_text()

        # Extract YAML frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)

        # Parse frontmatter fields
        name_match = re.search(r'name:\s*(.+)', frontmatter)
        desc_match = re.search(r'description:\s*(.+)', frontmatter)
        tools_match = re.search(r'tools:\s*(.+)', frontmatter)
        model_match = re.search(r'model:\s*(.+)', frontmatter)

        if not name_match or not desc_match:
            return None

        name = name_match.group(1).strip()
        description = desc_match.group(1).strip()
        tools = tools_match.group(1).strip().split(',') if tools_match else []
        tools = [t.strip() for t in tools]
        model = model_match.group(1).strip() if model_match else "sonnet-4"

        # Generate agent ID
        agent_id = hashlib.sha256(name.encode()).hexdigest()[:16]

        # Get metrics from database
        metrics = self.refinements_db.get_agent_metrics(agent_id)

        return Agent(
            agent_id=agent_id,
            name=name,
            description=description,
            tools=tools,
            model=model,
            file_path=file_path,
            content=content,
            use_count=metrics["total_invocations"] if metrics else 0,
            success_rate=metrics["success_rate"] if metrics else None,
            avg_execution_time=metrics["avg_execution_time"] if metrics else None
        )

    def identify_improvement_opportunities(self, agents: List[Agent]) -> List[Tuple[Agent, RefinementType, str, float]]:
        """Identify agents that could be improved"""
        opportunities = []

        for agent in agents:
            # Check for tool optimization opportunities
            if len(agent.tools) == 0:
                opportunities.append((
                    agent,
                    RefinementType.TOOL_OPTIMIZATION,
                    "No tools specified - agent may need tool access",
                    0.80
                ))
            elif len(agent.tools) > 10:
                opportunities.append((
                    agent,
                    RefinementType.TOOL_OPTIMIZATION,
                    f"Too many tools ({len(agent.tools)}) - should specialize",
                    0.70
                ))

            # Check for model selection
            if "Read" in agent.tools and "Write" in agent.tools and agent.model == "haiku":
                opportunities.append((
                    agent,
                    RefinementType.MODEL_SELECTION,
                    "Complex file operations with haiku - consider sonnet",
                    0.75
                ))

            # Check for memory integration
            if "mcp__enhanced-memory" not in agent.content:
                opportunities.append((
                    agent,
                    RefinementType.MEMORY_INTEGRATION,
                    "No memory integration - agent could benefit from persistent storage",
                    0.65
                ))

            # Check for error handling in content
            error_mentions = agent.content.lower().count("error")
            try_mentions = agent.content.lower().count("try")
            if error_mentions < 2 and try_mentions < 2:
                opportunities.append((
                    agent,
                    RefinementType.ERROR_HANDLING,
                    "Minimal error handling guidance - add error recovery patterns",
                    0.70
                ))

            # Check for prompt clarity
            if len(agent.description) < 50:
                opportunities.append((
                    agent,
                    RefinementType.PROMPT_IMPROVEMENT,
                    "Short description - expand with examples and use cases",
                    0.75
                ))

            # Check performance metrics
            if agent.success_rate is not None and agent.success_rate < 0.7:
                opportunities.append((
                    agent,
                    RefinementType.SPECIALIZATION,
                    f"Low success rate ({agent.success_rate:.0%}) - needs specialization",
                    0.85
                ))

        return opportunities

class AgentRefiner:
    """Generates refined versions of agents"""

    def __init__(self, db: AgentRefinementDatabase):
        self.db = db

    def generate_refinement(self, agent: Agent, refinement_type: RefinementType,
                          reason: str, confidence: float) -> AgentRefinement:
        """Generate a refined version of an agent"""

        # Generate refinement ID
        refinement_id = hashlib.sha256(
            f"{agent.agent_id}_{refinement_type.value}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Generate refined content based on type
        refined_content = self._generate_refined_content(agent, refinement_type)

        # Get current success rate for comparison
        metrics = self.db.get_agent_metrics(agent.agent_id)
        success_rate_before = metrics["success_rate"] if metrics else None

        refinement = AgentRefinement(
            refinement_id=refinement_id,
            agent_id=agent.agent_id,
            refinement_type=refinement_type,
            description=f"{refinement_type.value}: {reason}",
            original_content=agent.content,
            refined_content=refined_content,
            confidence=confidence,
            status=AgentStatus.PENDING_REFINEMENT,
            created_at=datetime.now(),
            applied_at=None,
            effectiveness=0.0,
            success_rate_before=success_rate_before,
            success_rate_after=None
        )

        return refinement

    def _generate_refined_content(self, agent: Agent, refinement_type: RefinementType) -> str:
        """Generate refined agent content based on refinement type"""

        content = agent.content

        if refinement_type == RefinementType.TOOL_OPTIMIZATION:
            # Add tool usage guidance
            tool_section = "\n\n## Tool Selection Guidelines\n\n"
            tool_section += "- Use Read for file inspection\n"
            tool_section += "- Use Grep for code search\n"
            tool_section += "- Use Bash for system operations\n"
            tool_section += "- Prefer specialized tools over general ones\n"
            content = content + tool_section

        elif refinement_type == RefinementType.PROMPT_IMPROVEMENT:
            # Expand description with examples
            expanded_desc = agent.description + "\n\n**Use Cases**:\n"
            expanded_desc += "- Example scenario 1\n"
            expanded_desc += "- Example scenario 2\n"
            content = content.replace(agent.description, expanded_desc, 1)

        elif refinement_type == RefinementType.MODEL_SELECTION:
            # Update model recommendation
            content = content.replace(f"model: {agent.model}", "model: sonnet-4", 1)

        elif refinement_type == RefinementType.MEMORY_INTEGRATION:
            # Add memory integration section
            memory_section = "\n\n## Memory Integration\n\n"
            memory_section += "```python\n"
            memory_section += "# Store learnings\n"
            memory_section += "mcp__enhanced-memory-mcp__create_entities([{\n"
            memory_section += f"    'name': '{agent.name}_learning',\n"
            memory_section += "    'entityType': 'agent_learning',\n"
            memory_section += "    'observations': ['key_insight']\n"
            memory_section += "}])\n"
            memory_section += "```\n"
            content = content + memory_section

        elif refinement_type == RefinementType.ERROR_HANDLING:
            # Add error handling section
            error_section = "\n\n## Error Handling Protocol\n\n"
            error_section += "1. Catch exceptions explicitly\n"
            error_section += "2. Log errors with context\n"
            error_section += "3. Provide fallback behavior\n"
            error_section += "4. Report errors clearly to user\n"
            content = content + error_section

        elif refinement_type == RefinementType.SPECIALIZATION:
            # Add specialization focus
            spec_section = "\n\n## Specialization Focus\n\n"
            spec_section += "This agent specializes in:\n"
            spec_section += "- Narrow, well-defined task scope\n"
            spec_section += "- Deep expertise in specific domain\n"
            spec_section += "- Consistent approach patterns\n"
            content = content + spec_section

        return content

    def apply_refinement(self, refinement: AgentRefinement) -> bool:
        """Apply a refinement by updating the agent file"""
        try:
            # Find agent file
            agent_file = self._find_agent_file(refinement.agent_id)

            if not agent_file or not agent_file.exists():
                print(f"Agent file not found for {refinement.agent_id}")
                return False

            # Backup original
            backup_file = agent_file.with_suffix(agent_file.suffix + '.backup')
            agent_file.rename(backup_file)

            # Write refined version
            agent_file.write_text(refinement.refined_content)

            # Update refinement status
            refinement.status = AgentStatus.DEPLOYED
            refinement.applied_at = datetime.now()
            self.db.store_refinement(refinement)

            print(f"✓ Applied refinement: {refinement.refinement_id}")
            print(f"  Backup saved: {backup_file}")

            return True

        except Exception as e:
            print(f"✗ Failed to apply refinement: {e}")
            return False

    def _find_agent_file(self, agent_id: str) -> Optional[Path]:
        """Find agent file by ID"""
        # This would need to search through agents and match by ID
        # For now, returning None as we'd need the original agent object
        return None

def main():
    """Main agent refinement runner"""
    print("="*60)
    print("Agent Refinement Engine - Week 5 Phase 4")
    print("="*60)
    print()

    # Initialize databases
    db = AgentRefinementDatabase(AGENT_REFINEMENTS_DB)
    print(f"✓ Refinement database initialized: {AGENT_REFINEMENTS_DB}")

    # Initialize analyzer
    analyzer = AgentAnalyzer(AGENTS_DIR, db)
    print(f"✓ Agent analyzer initialized")
    print()

    # Load agents
    agents = analyzer.load_agents()
    print(f"Loaded {len(agents)} agents from {AGENTS_DIR}")

    # Analyze for improvement opportunities
    opportunities = analyzer.identify_improvement_opportunities(agents)
    print(f"Found {len(opportunities)} improvement opportunities")
    print()

    if opportunities:
        print("Top Improvement Opportunities:")
        for agent, ref_type, reason, confidence in opportunities[:10]:
            print(f"  • {agent.name}")
            print(f"    Type: {ref_type.value}")
            print(f"    Reason: {reason}")
            print(f"    Confidence: {confidence:.0%}")
        print()

    # Generate refinements
    refiner = AgentRefiner(db)
    refinements_created = 0

    for agent, ref_type, reason, confidence in opportunities:
        if confidence >= 0.7:  # Only generate for high-confidence opportunities
            refinement = refiner.generate_refinement(agent, ref_type, reason, confidence)
            db.store_refinement(refinement)
            refinements_created += 1

    print(f"Created {refinements_created} agent refinements")
    print()

    # Report results
    print("="*60)
    print("AGENT REFINEMENT COMPLETE")
    print("="*60)
    print(f"Agents analyzed: {len(agents)}")
    print(f"Opportunities identified: {len(opportunities)}")
    print(f"Refinements created: {refinements_created}")
    print(f"Database: {AGENT_REFINEMENTS_DB}")
    print()

if __name__ == "__main__":
    main()
