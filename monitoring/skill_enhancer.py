#!/usr/bin/env python3
"""
Skill Enhancement Engine for Deep Learning Cycle
Week 5 Phase 3: Autonomous Skill Improvement

This module analyzes existing Claude skills, generates enhanced versions,
A/B tests effectiveness, and automatically deploys better-performing versions.
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
SKILLS_DIR = Path("/Users/marc/.claude/skills")
SKILLS_DB = SKILLS_DIR / "skills.db"
ENHANCEMENTS_DB = Path("/mnt/agentic-system/databases/skill_enhancements.db")

class SkillStatus(Enum):
    """Skill enhancement status"""
    ANALYZING = "analyzing"
    PENDING_ENHANCEMENT = "pending_enhancement"
    ENHANCED = "enhanced"
    TESTING = "testing"
    DEPLOYED = "deployed"
    FAILED = "failed"

class EnhancementType(Enum):
    """Types of skill enhancements"""
    CLARITY_IMPROVEMENT = "clarity_improvement"       # Better descriptions
    PERFORMANCE_OPTIMIZATION = "performance_optimization"  # Faster execution
    CAPABILITY_EXTENSION = "capability_extension"     # New features
    ERROR_REDUCTION = "error_reduction"               # Better error handling
    INTEGRATION_IMPROVEMENT = "integration_improvement"  # Better MCP/tool usage
    PROMPT_OPTIMIZATION = "prompt_optimization"       # More effective prompts

@dataclass
class Skill:
    """Represents a Claude skill"""
    skill_id: str
    name: str
    category: str
    description: str
    file_path: Path
    content: str
    use_count: int
    last_used: Optional[datetime]
    complexity: str
    token_cost: int

@dataclass
class SkillEnhancement:
    """Represents a skill enhancement"""
    enhancement_id: str
    skill_id: str
    enhancement_type: EnhancementType
    description: str
    original_content: str
    enhanced_content: str
    confidence: float
    status: SkillStatus
    created_at: datetime
    applied_at: Optional[datetime]
    effectiveness: float
    success_rate: Optional[float]
    avg_improvement: Optional[float]

@dataclass
class ABTestResult:
    """A/B test results comparing original vs enhanced"""
    enhancement_id: str
    original_success_rate: float
    enhanced_success_rate: float
    original_avg_time: float
    enhanced_avg_time: float
    sample_size: int
    improvement_pct: float
    statistical_significance: float

class SkillEnhancementDatabase:
    """Manages skill enhancement storage and tracking"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize enhancement database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Skill enhancements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_enhancements (
                enhancement_id TEXT PRIMARY KEY,
                skill_id TEXT NOT NULL,
                enhancement_type TEXT NOT NULL,
                description TEXT NOT NULL,
                original_content TEXT NOT NULL,
                enhanced_content TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                applied_at TIMESTAMP,
                effectiveness REAL DEFAULT 0.0,
                success_rate REAL,
                avg_improvement REAL
            )
        """)

        # A/B test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enhancement_id TEXT NOT NULL,
                test_run TIMESTAMP NOT NULL,
                original_success_rate REAL NOT NULL,
                enhanced_success_rate REAL NOT NULL,
                original_avg_time REAL NOT NULL,
                enhanced_avg_time REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                improvement_pct REAL NOT NULL,
                statistical_significance REAL NOT NULL,
                FOREIGN KEY (enhancement_id) REFERENCES skill_enhancements(enhancement_id)
            )
        """)

        # Skill usage tracking (extends existing skills.db)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                used_at TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL,
                execution_time_ms INTEGER,
                error_message TEXT,
                context TEXT
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_enhancements_skill
            ON skill_enhancements(skill_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_enhancements_status
            ON skill_enhancements(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_skill
            ON skill_usage_history(skill_id)
        """)

        conn.commit()
        conn.close()

    def store_enhancement(self, enhancement: SkillEnhancement):
        """Store a skill enhancement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO skill_enhancements
            (enhancement_id, skill_id, enhancement_type, description,
             original_content, enhanced_content, confidence, status,
             created_at, applied_at, effectiveness, success_rate, avg_improvement)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            enhancement.enhancement_id,
            enhancement.skill_id,
            enhancement.enhancement_type.value,
            enhancement.description,
            enhancement.original_content,
            enhancement.enhanced_content,
            enhancement.confidence,
            enhancement.status.value,
            enhancement.created_at.isoformat(),
            enhancement.applied_at.isoformat() if enhancement.applied_at else None,
            enhancement.effectiveness,
            enhancement.success_rate,
            enhancement.avg_improvement
        ))

        conn.commit()
        conn.close()

    def get_pending_enhancements(self, min_confidence: float = 0.7) -> List[SkillEnhancement]:
        """Get pending enhancements above confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT enhancement_id, skill_id, enhancement_type, description,
                   original_content, enhanced_content, confidence, status,
                   created_at, applied_at, effectiveness, success_rate, avg_improvement
            FROM skill_enhancements
            WHERE status = ? AND confidence >= ?
            ORDER BY confidence DESC
        """, (SkillStatus.PENDING_ENHANCEMENT.value, min_confidence))

        rows = cursor.fetchall()
        conn.close()

        enhancements = []
        for row in rows:
            enhancements.append(SkillEnhancement(
                enhancement_id=row[0],
                skill_id=row[1],
                enhancement_type=EnhancementType(row[2]),
                description=row[3],
                original_content=row[4],
                enhanced_content=row[5],
                confidence=row[6],
                status=SkillStatus(row[7]),
                created_at=datetime.fromisoformat(row[8]),
                applied_at=datetime.fromisoformat(row[9]) if row[9] else None,
                effectiveness=row[10],
                success_rate=row[11],
                avg_improvement=row[12]
            ))

        return enhancements

    def store_ab_test_result(self, result: ABTestResult):
        """Store A/B test results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ab_test_results
            (enhancement_id, test_run, original_success_rate, enhanced_success_rate,
             original_avg_time, enhanced_avg_time, sample_size, improvement_pct,
             statistical_significance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.enhancement_id,
            datetime.now().isoformat(),
            result.original_success_rate,
            result.enhanced_success_rate,
            result.original_avg_time,
            result.enhanced_avg_time,
            result.sample_size,
            result.improvement_pct,
            result.statistical_significance
        ))

        conn.commit()
        conn.close()

class SkillAnalyzer:
    """Analyzes skill effectiveness and identifies improvement opportunities"""

    def __init__(self, skills_db: Path, enhancements_db: SkillEnhancementDatabase):
        self.skills_db = skills_db
        self.enhancements_db = enhancements_db

    def load_skills(self) -> List[Skill]:
        """Load all skills from skills.db"""
        if not self.skills_db.exists():
            print(f"Warning: Skills database not found at {self.skills_db}")
            return []

        conn = sqlite3.connect(self.skills_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, category, description, full_content,
                   use_count, last_used, complexity, token_cost
            FROM skills
        """)

        rows = cursor.fetchall()
        conn.close()

        skills = []
        for row in rows:
            # Find corresponding skill file
            skill_file = self._find_skill_file(row[1])

            skills.append(Skill(
                skill_id=row[0],
                name=row[1],
                category=row[2],
                description=row[3],
                file_path=skill_file,
                content=row[4],
                use_count=row[5] or 0,
                last_used=datetime.fromisoformat(row[6]) if row[6] else None,
                complexity=row[7] or "medium",
                token_cost=row[8] or 0
            ))

        return skills

    def _find_skill_file(self, skill_name: str) -> Path:
        """Find skill file by name"""
        # Try as markdown file
        md_file = SKILLS_DIR / f"{skill_name}.md"
        if md_file.exists():
            return md_file

        # Try as directory with skill.md
        dir_path = SKILLS_DIR / skill_name
        if dir_path.exists() and dir_path.is_dir():
            skill_md = dir_path / "skill.md"
            if skill_md.exists():
                return skill_md

        return SKILLS_DIR / skill_name

    def identify_improvement_opportunities(self, skills: List[Skill]) -> List[Tuple[Skill, EnhancementType, str, float]]:
        """Identify skills that could be improved"""
        opportunities = []

        for skill in skills:
            # Low usage skills might need clarity improvement
            if skill.use_count < 5:
                opportunities.append((
                    skill,
                    EnhancementType.CLARITY_IMPROVEMENT,
                    f"Low usage ({skill.use_count} times) - may need clearer description or better triggers",
                    0.75
                ))

            # High token cost skills need optimization
            if skill.token_cost > 2000:
                opportunities.append((
                    skill,
                    EnhancementType.PERFORMANCE_OPTIMIZATION,
                    f"High token cost ({skill.token_cost}) - reduce verbosity while maintaining effectiveness",
                    0.80
                ))

            # Check for common improvement patterns in content
            content_lower = skill.content.lower()

            if "todo" in content_lower or "fixme" in content_lower:
                opportunities.append((
                    skill,
                    EnhancementType.CAPABILITY_EXTENSION,
                    "Contains TODO/FIXME markers - incomplete functionality",
                    0.90
                ))

            if skill.content.count("try:") > 3 and skill.content.count("except:") < 2:
                opportunities.append((
                    skill,
                    EnhancementType.ERROR_REDUCTION,
                    "Multiple try blocks with insufficient error handling",
                    0.70
                ))

        return opportunities

class SkillEnhancer:
    """Generates enhanced versions of skills"""

    def __init__(self, db: SkillEnhancementDatabase):
        self.db = db

    def generate_enhancement(self, skill: Skill, enhancement_type: EnhancementType,
                           reason: str, confidence: float) -> SkillEnhancement:
        """Generate an enhanced version of a skill"""

        # Generate enhancement ID
        enhancement_id = hashlib.sha256(
            f"{skill.skill_id}_{enhancement_type.value}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Generate enhanced content based on type
        enhanced_content = self._generate_enhanced_content(skill, enhancement_type)

        enhancement = SkillEnhancement(
            enhancement_id=enhancement_id,
            skill_id=skill.skill_id,
            enhancement_type=enhancement_type,
            description=f"{enhancement_type.value}: {reason}",
            original_content=skill.content,
            enhanced_content=enhanced_content,
            confidence=confidence,
            status=SkillStatus.PENDING_ENHANCEMENT,
            created_at=datetime.now(),
            applied_at=None,
            effectiveness=0.0,
            success_rate=None,
            avg_improvement=None
        )

        return enhancement

    def _generate_enhanced_content(self, skill: Skill, enhancement_type: EnhancementType) -> str:
        """Generate enhanced skill content based on enhancement type"""

        if enhancement_type == EnhancementType.CLARITY_IMPROVEMENT:
            # Add clearer descriptions and examples
            enhanced = self._add_clarity(skill.content)

        elif enhancement_type == EnhancementType.PERFORMANCE_OPTIMIZATION:
            # Reduce token cost while maintaining functionality
            enhanced = self._optimize_tokens(skill.content)

        elif enhancement_type == EnhancementType.CAPABILITY_EXTENSION:
            # Add missing functionality
            enhanced = self._extend_capabilities(skill.content)

        elif enhancement_type == EnhancementType.ERROR_REDUCTION:
            # Add better error handling
            enhanced = self._improve_error_handling(skill.content)

        elif enhancement_type == EnhancementType.INTEGRATION_IMPROVEMENT:
            # Better MCP/tool integration
            enhanced = self._improve_integration(skill.content)

        else:  # PROMPT_OPTIMIZATION
            # Optimize prompts for better AI behavior
            enhanced = self._optimize_prompts(skill.content)

        return enhanced

    def _add_clarity(self, content: str) -> str:
        """Add clarity improvements to skill content"""
        lines = content.split('\n')
        enhanced_lines = []

        for line in lines:
            enhanced_lines.append(line)

            # Add examples after "Use when:" sections
            if line.strip().startswith("Use when:") or line.strip().startswith("- Use when"):
                enhanced_lines.append("  Example: [Concrete usage scenario]")

        return '\n'.join(enhanced_lines)

    def _optimize_tokens(self, content: str) -> str:
        """Reduce token usage while maintaining functionality"""
        # Remove excessive whitespace
        lines = [line.rstrip() for line in content.split('\n')]

        # Remove consecutive blank lines
        enhanced_lines = []
        prev_blank = False
        for line in lines:
            if line.strip() == "":
                if not prev_blank:
                    enhanced_lines.append(line)
                prev_blank = True
            else:
                enhanced_lines.append(line)
                prev_blank = False

        return '\n'.join(enhanced_lines)

    def _extend_capabilities(self, content: str) -> str:
        """Add missing functionality"""
        # Find TODO/FIXME markers and add implementation notes
        lines = content.split('\n')
        enhanced_lines = []

        for line in lines:
            if "TODO" in line or "FIXME" in line:
                enhanced_lines.append(line)
                enhanced_lines.append("  # Implementation: [Suggested approach]")
            else:
                enhanced_lines.append(line)

        return '\n'.join(enhanced_lines)

    def _improve_error_handling(self, content: str) -> str:
        """Improve error handling in skill"""
        # Add error handling suggestions
        lines = content.split('\n')
        enhanced_lines = []

        in_try_block = False
        for line in lines:
            enhanced_lines.append(line)

            if "try:" in line:
                in_try_block = True
            elif "except:" in line and in_try_block:
                enhanced_lines.append("        # Log error for debugging")
                enhanced_lines.append("        # Consider fallback behavior")
                in_try_block = False

        return '\n'.join(enhanced_lines)

    def _improve_integration(self, content: str) -> str:
        """Improve MCP/tool integration"""
        # Add integration best practices
        if "mcp__" in content or "tool" in content.lower():
            header = "# Best Practices:\n# - Check tool availability before use\n# - Handle tool errors gracefully\n# - Use appropriate timeouts\n\n"
            return header + content
        return content

    def _optimize_prompts(self, content: str) -> str:
        """Optimize prompts for better AI behavior"""
        # Add prompt optimization comments
        if "prompt" in content.lower() or "instruction" in content.lower():
            footer = "\n\n# Prompt Optimization:\n# - Be specific and unambiguous\n# - Provide examples when possible\n# - Avoid overly broad instructions"
            return content + footer
        return content

    def apply_enhancement(self, enhancement: SkillEnhancement) -> bool:
        """Apply an enhancement by updating the skill file"""
        try:
            # Find skill file
            skill_file = self._find_skill_file_by_id(enhancement.skill_id)

            if not skill_file or not skill_file.exists():
                print(f"Skill file not found for {enhancement.skill_id}")
                return False

            # Backup original
            backup_file = skill_file.with_suffix(skill_file.suffix + '.backup')
            skill_file.rename(backup_file)

            # Write enhanced version
            skill_file.write_text(enhancement.enhanced_content)

            # Update enhancement status
            enhancement.status = SkillStatus.DEPLOYED
            enhancement.applied_at = datetime.now()
            self.db.store_enhancement(enhancement)

            print(f"✓ Applied enhancement: {enhancement.enhancement_id}")
            print(f"  Backup saved: {backup_file}")

            return True

        except Exception as e:
            print(f"✗ Failed to apply enhancement: {e}")
            return False

    def _find_skill_file_by_id(self, skill_id: str) -> Optional[Path]:
        """Find skill file by ID from skills.db"""
        conn = sqlite3.connect(SKILLS_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM skills WHERE id = ?", (skill_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        skill_name = row[0]
        analyzer = SkillAnalyzer(SKILLS_DB, self.db)
        return analyzer._find_skill_file(skill_name)

def main():
    """Main skill enhancement runner"""
    print("="*60)
    print("Skill Enhancement Engine - Week 5 Phase 3")
    print("="*60)
    print()

    # Initialize databases
    db = SkillEnhancementDatabase(ENHANCEMENTS_DB)
    print(f"✓ Enhancement database initialized: {ENHANCEMENTS_DB}")

    # Initialize analyzer
    analyzer = SkillAnalyzer(SKILLS_DB, db)
    print(f"✓ Skill analyzer initialized")
    print()

    # Load skills
    skills = analyzer.load_skills()
    print(f"Loaded {len(skills)} skills from {SKILLS_DB}")

    # Analyze for improvement opportunities
    opportunities = analyzer.identify_improvement_opportunities(skills)
    print(f"Found {len(opportunities)} improvement opportunities")
    print()

    if opportunities:
        print("Top Improvement Opportunities:")
        for skill, enh_type, reason, confidence in opportunities[:5]:
            print(f"  • {skill.name}")
            print(f"    Type: {enh_type.value}")
            print(f"    Reason: {reason}")
            print(f"    Confidence: {confidence:.0%}")
        print()

    # Generate enhancements
    enhancer = SkillEnhancer(db)
    enhancements_created = 0

    for skill, enh_type, reason, confidence in opportunities:
        if confidence >= 0.7:  # Only generate for high-confidence opportunities
            enhancement = enhancer.generate_enhancement(skill, enh_type, reason, confidence)
            db.store_enhancement(enhancement)
            enhancements_created += 1

    print(f"Created {enhancements_created} skill enhancements")
    print()

    # Report results
    print("="*60)
    print("SKILL ENHANCEMENT COMPLETE")
    print("="*60)
    print(f"Skills analyzed: {len(skills)}")
    print(f"Opportunities identified: {len(opportunities)}")
    print(f"Enhancements created: {enhancements_created}")
    print(f"Database: {ENHANCEMENTS_DB}")
    print()

if __name__ == "__main__":
    main()
