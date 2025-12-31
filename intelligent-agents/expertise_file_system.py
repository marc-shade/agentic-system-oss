"""
Expertise File System - IndyDevDan Agent Expert Pattern Integration

Based on "Agent Experts" video concepts:
- Expertise files as evolving mental models
- Self-improve prompts that update expertise automatically
- Meta-agentics: meta prompts, meta agents, meta skills
- 3-step workflow: Plan → Build → Self-Improve

Integrates with DGM empirical system for continuous learning.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExpertiseEntry:
    """Single piece of learned expertise."""
    id: str
    domain: str  # e.g., "code_generation", "debugging", "architecture"
    pattern: str  # What was learned
    context: str  # When to apply this
    confidence: float  # 0.0 to 1.0
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[str] = None
    source: str = "experience"  # "experience", "research", "user_feedback"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def record_usage(self, success: bool):
        """Record usage of this expertise."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.last_used = datetime.now().isoformat()
        # Update confidence based on success rate
        self.confidence = 0.3 + (0.7 * self.success_rate)


@dataclass
class MetaPrompt:
    """Template metaprompt that can evolve."""
    id: str
    name: str
    template: str
    variables: List[str]
    domain: str
    version: int = 1
    effectiveness_score: float = 0.5
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    evolution_history: List[Dict] = field(default_factory=list)

    def evolve(self, new_template: str, reason: str) -> 'MetaPrompt':
        """Create evolved version of this metaprompt."""
        evolved = MetaPrompt(
            id=f"{self.id}_v{self.version + 1}",
            name=self.name,
            template=new_template,
            variables=self.variables,
            domain=self.domain,
            version=self.version + 1,
            effectiveness_score=self.effectiveness_score,
            created_at=datetime.now().isoformat(),
            evolution_history=self.evolution_history + [{
                "from_version": self.version,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }]
        )
        return evolved


@dataclass
class ExpertiseFile:
    """
    Mental model as evolving data structure.

    Core concept from IndyDevDan: The expertise file IS the agent's
    accumulated knowledge that improves over time through self-improvement.
    """
    agent_name: str
    version: str
    expertise: Dict[str, List[ExpertiseEntry]] = field(default_factory=dict)
    meta_prompts: Dict[str, MetaPrompt] = field(default_factory=dict)
    learned_patterns: List[Dict] = field(default_factory=list)
    failure_patterns: List[Dict] = field(default_factory=list)  # What NOT to do
    preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    improvement_count: int = 0

    def add_expertise(self, entry: ExpertiseEntry):
        """Add new expertise entry."""
        if entry.domain not in self.expertise:
            self.expertise[entry.domain] = []
        self.expertise[entry.domain].append(entry)
        self._mark_updated()

    def add_meta_prompt(self, prompt: MetaPrompt):
        """Add or update a meta prompt."""
        self.meta_prompts[prompt.name] = prompt
        self._mark_updated()

    def add_learned_pattern(self, pattern: Dict):
        """Record a learned pattern."""
        pattern["learned_at"] = datetime.now().isoformat()
        self.learned_patterns.append(pattern)
        self._mark_updated()

    def add_failure_pattern(self, pattern: Dict):
        """Record what NOT to do."""
        pattern["recorded_at"] = datetime.now().isoformat()
        self.failure_patterns.append(pattern)
        self._mark_updated()

    def get_relevant_expertise(self, domain: str, context: str) -> List[ExpertiseEntry]:
        """Get expertise relevant to current task."""
        if domain not in self.expertise:
            return []
        # Return entries sorted by confidence and success rate
        entries = self.expertise[domain]
        return sorted(entries,
                     key=lambda e: (e.confidence * 0.6 + e.success_rate * 0.4),
                     reverse=True)

    def _mark_updated(self):
        self.last_updated = datetime.now().isoformat()
        self.improvement_count += 1

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "expertise": {
                domain: [asdict(e) for e in entries]
                for domain, entries in self.expertise.items()
            },
            "meta_prompts": {
                name: asdict(p) for name, p in self.meta_prompts.items()
            },
            "learned_patterns": self.learned_patterns,
            "failure_patterns": self.failure_patterns,
            "preferences": self.preferences,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "improvement_count": self.improvement_count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ExpertiseFile':
        """Deserialize from dictionary."""
        ef = cls(
            agent_name=data["agent_name"],
            version=data["version"],
            preferences=data.get("preferences", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            improvement_count=data.get("improvement_count", 0)
        )

        # Restore expertise entries
        for domain, entries in data.get("expertise", {}).items():
            ef.expertise[domain] = [
                ExpertiseEntry(**e) for e in entries
            ]

        # Restore meta prompts
        for name, prompt_data in data.get("meta_prompts", {}).items():
            ef.meta_prompts[name] = MetaPrompt(**prompt_data)

        ef.learned_patterns = data.get("learned_patterns", [])
        ef.failure_patterns = data.get("failure_patterns", [])

        return ef


class AgentExpertSystem:
    """
    Agent Expert System - Self-improving through expertise files.

    Implements the 3-step workflow:
    1. PLAN - Use expertise to plan approach
    2. BUILD - Execute with meta-prompts
    3. SELF-IMPROVE - Update expertise based on outcomes
    """

    def __init__(self, agent_name: str, storage_path: Optional[Path] = None):
        self.agent_name = agent_name
        self.storage_path = storage_path or Path(f"/tmp/expertise_{agent_name}.json")
        self.expertise_file = self._load_or_create()

    def _load_or_create(self) -> ExpertiseFile:
        """Load existing expertise or create new."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded expertise file for {self.agent_name}")
                return ExpertiseFile.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load expertise: {e}")

        return ExpertiseFile(
            agent_name=self.agent_name,
            version="1.0.0"
        )

    def save(self):
        """Persist expertise file."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.expertise_file.to_dict(), f, indent=2)
        logger.info(f"Saved expertise file ({self.expertise_file.improvement_count} improvements)")

    # === STEP 1: PLAN ===
    def plan_approach(self, task: str, domain: str) -> Dict[str, Any]:
        """
        Use accumulated expertise to plan approach.

        Returns relevant expertise, applicable meta-prompts, and warnings.
        """
        plan = {
            "task": task,
            "domain": domain,
            "relevant_expertise": [],
            "applicable_prompts": [],
            "warnings": [],
            "confidence": 0.5
        }

        # Get relevant expertise
        expertise = self.expertise_file.get_relevant_expertise(domain, task)
        plan["relevant_expertise"] = [
            {
                "pattern": e.pattern,
                "context": e.context,
                "confidence": e.confidence,
                "success_rate": e.success_rate
            }
            for e in expertise[:5]  # Top 5
        ]

        # Find applicable meta-prompts
        for name, prompt in self.expertise_file.meta_prompts.items():
            if prompt.domain == domain or prompt.domain == "general":
                plan["applicable_prompts"].append({
                    "name": name,
                    "effectiveness": prompt.effectiveness_score,
                    "template": prompt.template[:100] + "..."
                })

        # Check for failure patterns (warnings)
        for pattern in self.expertise_file.failure_patterns:
            if pattern.get("domain") == domain:
                plan["warnings"].append(pattern.get("description", "Unknown warning"))

        # Calculate overall confidence
        if expertise:
            plan["confidence"] = sum(e.confidence for e in expertise[:5]) / min(len(expertise), 5)

        return plan

    # === STEP 2: BUILD ===
    def get_meta_prompt(self, name: str, variables: Dict[str, str]) -> Optional[str]:
        """
        Get and fill a meta-prompt template.

        Returns the filled template ready for use.
        """
        if name not in self.expertise_file.meta_prompts:
            return None

        prompt = self.expertise_file.meta_prompts[name]
        prompt.usage_count += 1

        result = prompt.template
        for var, value in variables.items():
            result = result.replace(f"{{{var}}}", value)

        return result

    # === STEP 3: SELF-IMPROVE ===
    def self_improve(self, task_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update expertise based on task outcome.

        This is the KEY differentiator of Agent Experts:
        - Automatic learning from every task
        - Expertise file grows smarter over time
        - Failures become warnings for future
        """
        improvements = {
            "expertise_added": 0,
            "patterns_learned": 0,
            "failures_recorded": 0,
            "prompts_evolved": 0
        }

        success = task_result.get("success", False)
        domain = task_result.get("domain", "general")

        if success:
            # Learn from success
            if "learned_pattern" in task_result:
                entry = ExpertiseEntry(
                    id=hashlib.md5(
                        task_result["learned_pattern"].encode()
                    ).hexdigest()[:12],
                    domain=domain,
                    pattern=task_result["learned_pattern"],
                    context=task_result.get("context", ""),
                    confidence=0.6,  # Start moderate, increase with use
                    usage_count=1,
                    success_count=1
                )
                self.expertise_file.add_expertise(entry)
                improvements["expertise_added"] += 1

            # Record general patterns
            self.expertise_file.add_learned_pattern({
                "type": "success",
                "domain": domain,
                "description": task_result.get("description", ""),
                "approach": task_result.get("approach", "")
            })
            improvements["patterns_learned"] += 1

            # Update prompt effectiveness if used
            if "prompt_used" in task_result:
                prompt_name = task_result["prompt_used"]
                if prompt_name in self.expertise_file.meta_prompts:
                    prompt = self.expertise_file.meta_prompts[prompt_name]
                    # Increase effectiveness
                    prompt.effectiveness_score = min(1.0,
                        prompt.effectiveness_score + 0.05)

        else:
            # Learn from failure - what NOT to do
            self.expertise_file.add_failure_pattern({
                "domain": domain,
                "description": task_result.get("error", "Unknown failure"),
                "attempted_approach": task_result.get("approach", ""),
                "severity": task_result.get("severity", "medium")
            })
            improvements["failures_recorded"] += 1

            # Decrease prompt effectiveness if used
            if "prompt_used" in task_result:
                prompt_name = task_result["prompt_used"]
                if prompt_name in self.expertise_file.meta_prompts:
                    prompt = self.expertise_file.meta_prompts[prompt_name]
                    prompt.effectiveness_score = max(0.1,
                        prompt.effectiveness_score - 0.1)

                    # Consider evolving the prompt if effectiveness drops too low
                    if prompt.effectiveness_score < 0.3 and prompt.usage_count > 5:
                        improvements["prompts_need_evolution"] = prompt_name

        # Auto-save after improvements
        self.save()

        return improvements

    def evolve_prompt(self, name: str, new_template: str, reason: str) -> bool:
        """Evolve a meta-prompt to a new version."""
        if name not in self.expertise_file.meta_prompts:
            return False

        current = self.expertise_file.meta_prompts[name]
        evolved = current.evolve(new_template, reason)
        self.expertise_file.add_meta_prompt(evolved)

        logger.info(f"Evolved prompt '{name}' to v{evolved.version}: {reason}")
        self.save()
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get current expertise status."""
        total_expertise = sum(
            len(entries) for entries in self.expertise_file.expertise.values()
        )

        return {
            "agent_name": self.agent_name,
            "version": self.expertise_file.version,
            "total_expertise_entries": total_expertise,
            "domains_covered": list(self.expertise_file.expertise.keys()),
            "meta_prompts_count": len(self.expertise_file.meta_prompts),
            "learned_patterns": len(self.expertise_file.learned_patterns),
            "failure_patterns": len(self.expertise_file.failure_patterns),
            "improvement_count": self.expertise_file.improvement_count,
            "last_updated": self.expertise_file.last_updated
        }


def integrate_with_dgm(expert_system: AgentExpertSystem, dgm_integration) -> Dict[str, Any]:
    """
    Bridge between Agent Expert System and DGM Empirical Integration.

    - DGM handles code/config modifications with fitness validation
    - Agent Expert handles expertise/pattern learning
    - Together they create a complete self-improving system
    """
    from dgm_empirical_integration import DGMEmpiricalIntegration

    # Transfer learned patterns to DGM archive
    patterns_transferred = 0
    for pattern in expert_system.expertise_file.learned_patterns:
        if pattern.get("type") == "success":
            # These successful patterns inform DGM's modification proposals
            patterns_transferred += 1

    # Transfer failure patterns to DGM failure history
    failures_transferred = 0
    for failure in expert_system.expertise_file.failure_patterns:
        dgm_integration.failure_tracker.record_failure(
            modification_type="pattern_application",
            description=failure.get("description", ""),
            attempted_change=failure.get("attempted_approach", ""),
            failure_reason=failure.get("description", ""),
            context={"domain": failure.get("domain", "general")}
        )
        failures_transferred += 1

    return {
        "patterns_transferred": patterns_transferred,
        "failures_transferred": failures_transferred,
        "integration_complete": True
    }


# === Demo / Test ===
if __name__ == "__main__":
    print("=" * 60)
    print("Agent Expert System - IndyDevDan Pattern Demo")
    print("=" * 60)

    # Create expert system
    expert = AgentExpertSystem(
        agent_name="agi_orchestrator",
        storage_path=Path("/tmp/agi_expertise.json")
    )

    # Add some initial meta-prompts
    expert.expertise_file.add_meta_prompt(MetaPrompt(
        id="code_review_1",
        name="code_review",
        template="""Review this {language} code for:
1. Correctness: Does it do what it should?
2. Performance: Any obvious bottlenecks?
3. Security: Any vulnerabilities?
4. Maintainability: Is it clean and readable?

Code to review:
{code}

Provide specific, actionable feedback.""",
        variables=["language", "code"],
        domain="code_generation"
    ))

    expert.expertise_file.add_meta_prompt(MetaPrompt(
        id="debug_1",
        name="debug_approach",
        template="""Debug this {error_type} error:

Error: {error_message}
Context: {context}

Steps:
1. Identify the root cause
2. Propose fix
3. Verify fix doesn't break other things""",
        variables=["error_type", "error_message", "context"],
        domain="debugging"
    ))

    # Simulate 3-step workflow
    print("\n--- STEP 1: PLAN ---")
    plan = expert.plan_approach(
        task="Review Python function for performance issues",
        domain="code_generation"
    )
    print(f"Confidence: {plan['confidence']:.2f}")
    print(f"Applicable prompts: {len(plan['applicable_prompts'])}")
    print(f"Warnings: {len(plan['warnings'])}")

    print("\n--- STEP 2: BUILD ---")
    filled_prompt = expert.get_meta_prompt("code_review", {
        "language": "Python",
        "code": "def slow_func(n): return [i**2 for i in range(n)]"
    })
    print(f"Generated prompt length: {len(filled_prompt)} chars")

    print("\n--- STEP 3: SELF-IMPROVE ---")
    # Simulate successful task
    improvements = expert.self_improve({
        "success": True,
        "domain": "code_generation",
        "learned_pattern": "List comprehensions can be optimized with generators for large n",
        "context": "Python performance optimization",
        "description": "Identified performance improvement opportunity",
        "approach": "Suggested generator expression",
        "prompt_used": "code_review"
    })
    print(f"Improvements made: {improvements}")

    # Simulate a failure
    improvements = expert.self_improve({
        "success": False,
        "domain": "code_generation",
        "error": "Suggested optimization actually made code slower",
        "approach": "Premature optimization without benchmarking",
        "severity": "medium"
    })
    print(f"Failure recorded: {improvements}")

    # Check status
    print("\n--- EXPERTISE STATUS ---")
    status = expert.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("Agent Expert System initialized and tested successfully!")
    print("=" * 60)
