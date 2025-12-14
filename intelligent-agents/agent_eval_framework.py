#!/usr/bin/env python3
"""
Agent Eval Framework - Eugene Yan's 3-Step Methodology

Based on: https://www.youtube.com/watch?v=mz7mAo4zIC8
Implementation of: Label → Align → Run iterative eval loop

This framework provides:
1. Labeled dataset management (binary pass/fail)
2. LLM-as-judge evaluator with alignment
3. Eval harness for running evals on config changes

Integrates with:
- enhanced-memory MCP for persistent storage
- Ollama on GPU nodes for LLM inference
- Ember MCP for quality conscience integration
"""

import json
import os
import sqlite3
import httpx
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Literal
from pathlib import Path
import hashlib

# Configuration
EVAL_DB_PATH = Path(os.environ.get('EVAL_DB_PATH', '/mnt/agentic-system/databases/agent_evals.db'))
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://192.168.1.186:11434')
DEFAULT_JUDGE_MODEL = os.environ.get('EVAL_JUDGE_MODEL', 'gpt-oss:20b')


@dataclass
class EvalCriteria:
    """Custom evaluation criteria definition"""
    name: str
    description: str
    pass_description: str
    fail_description: str
    examples_pass: list[str]
    examples_fail: list[str]
    weight: float = 1.0

    def to_prompt_section(self) -> str:
        """Generate prompt section for this criteria"""
        return f"""
## Criteria: {self.name}
{self.description}

**PASS** if: {self.pass_description}
**FAIL** if: {self.fail_description}

Examples of PASS:
{chr(10).join(f'- {ex}' for ex in self.examples_pass[:3])}

Examples of FAIL:
{chr(10).join(f'- {ex}' for ex in self.examples_fail[:3])}
"""


@dataclass
class LabeledExample:
    """A single labeled example in the dataset"""
    id: str
    input_text: str
    output_text: str
    label: Literal['pass', 'fail']
    criteria_name: str
    reasoning: str
    labeler: str = 'human'
    timestamp: str = ''

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.id:
            self.id = hashlib.md5(f"{self.input_text}{self.output_text}".encode()).hexdigest()[:12]


@dataclass
class EvalResult:
    """Result from running an evaluation"""
    example_id: str
    predicted_label: Literal['pass', 'fail']
    confidence: float
    reasoning: str
    aligned_with_human: bool
    criteria_name: str
    judge_model: str
    timestamp: str = ''

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class EvalDataset:
    """Manages labeled datasets for evaluation"""

    def __init__(self, db_path: Path = EVAL_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for eval storage"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Criteria definitions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS criteria (
                name TEXT PRIMARY KEY,
                description TEXT,
                pass_description TEXT,
                fail_description TEXT,
                examples_pass TEXT,
                examples_fail TEXT,
                weight REAL DEFAULT 1.0,
                created_at TEXT
            )
        ''')

        # Labeled examples
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS labeled_examples (
                id TEXT PRIMARY KEY,
                input_text TEXT,
                output_text TEXT,
                label TEXT CHECK(label IN ('pass', 'fail')),
                criteria_name TEXT,
                reasoning TEXT,
                labeler TEXT,
                timestamp TEXT,
                FOREIGN KEY (criteria_name) REFERENCES criteria(name)
            )
        ''')

        # Eval results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eval_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                example_id TEXT,
                predicted_label TEXT,
                confidence REAL,
                reasoning TEXT,
                aligned_with_human INTEGER,
                criteria_name TEXT,
                judge_model TEXT,
                timestamp TEXT,
                FOREIGN KEY (example_id) REFERENCES labeled_examples(id)
            )
        ''')

        # Alignment history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alignment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criteria_name TEXT,
                alignment_score REAL,
                prompt_version TEXT,
                judge_model TEXT,
                timestamp TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def add_criteria(self, criteria: EvalCriteria):
        """Add or update evaluation criteria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO criteria
            (name, description, pass_description, fail_description,
             examples_pass, examples_fail, weight, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            criteria.name,
            criteria.description,
            criteria.pass_description,
            criteria.fail_description,
            json.dumps(criteria.examples_pass),
            json.dumps(criteria.examples_fail),
            criteria.weight,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_criteria(self, name: str) -> Optional[EvalCriteria]:
        """Get criteria by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM criteria WHERE name = ?', (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return EvalCriteria(
                name=row[0],
                description=row[1],
                pass_description=row[2],
                fail_description=row[3],
                examples_pass=json.loads(row[4]),
                examples_fail=json.loads(row[5]),
                weight=row[6]
            )
        return None

    def add_example(self, example: LabeledExample):
        """Add a labeled example to the dataset"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO labeled_examples
            (id, input_text, output_text, label, criteria_name, reasoning, labeler, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            example.id,
            example.input_text,
            example.output_text,
            example.label,
            example.criteria_name,
            example.reasoning,
            example.labeler,
            example.timestamp
        ))
        conn.commit()
        conn.close()

    def get_examples(self, criteria_name: str, limit: int = 100) -> list[LabeledExample]:
        """Get labeled examples for a criteria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM labeled_examples
            WHERE criteria_name = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (criteria_name, limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            LabeledExample(
                id=row[0],
                input_text=row[1],
                output_text=row[2],
                label=row[3],
                criteria_name=row[4],
                reasoning=row[5],
                labeler=row[6],
                timestamp=row[7]
            )
            for row in rows
        ]

    def get_alignment_score(self, criteria_name: str) -> float:
        """Get current alignment score for criteria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT alignment_score FROM alignment_history
            WHERE criteria_name = ?
            ORDER BY timestamp DESC LIMIT 1
        ''', (criteria_name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0.0


class LLMJudge:
    """LLM-as-judge evaluator using cluster GPU"""

    def __init__(self, model: str = DEFAULT_JUDGE_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host
        self.client = httpx.Client(timeout=120.0)

    def _generate(self, prompt: str) -> str:
        """Generate response from Ollama"""
        response = self.client.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for consistent judgments
                    "num_predict": 500
                }
            }
        )
        response.raise_for_status()
        return response.json()["response"]

    def build_judge_prompt(self, criteria: EvalCriteria, output_text: str,
                           few_shot_examples: list[LabeledExample] = None) -> str:
        """Build the judge prompt with criteria and few-shot examples"""

        prompt = f"""You are an evaluation judge. Your task is to evaluate the following output based on specific criteria.

{criteria.to_prompt_section()}
"""

        # Add few-shot examples for alignment
        if few_shot_examples:
            prompt += "\n## Reference Examples (Human-Labeled)\n"
            for ex in few_shot_examples[:5]:
                prompt += f"""
---
Output: {ex.output_text[:500]}
Label: {ex.label.upper()}
Reasoning: {ex.reasoning}
---
"""

        prompt += f"""
## Output to Evaluate
{output_text}

## Your Judgment
Respond in this exact format:
LABEL: [PASS or FAIL]
CONFIDENCE: [0.0 to 1.0]
REASONING: [Your explanation]
"""
        return prompt

    def judge(self, criteria: EvalCriteria, output_text: str,
              few_shot_examples: list[LabeledExample] = None) -> tuple[str, float, str]:
        """
        Judge an output against criteria.
        Returns: (label, confidence, reasoning)
        """
        prompt = self.build_judge_prompt(criteria, output_text, few_shot_examples)
        response = self._generate(prompt)

        # Parse response
        label = 'fail'
        confidence = 0.5
        reasoning = response

        lines = response.strip().split('\n')
        for line in lines:
            if line.startswith('LABEL:'):
                label = 'pass' if 'PASS' in line.upper() else 'fail'
            elif line.startswith('CONFIDENCE:'):
                try:
                    confidence = float(line.split(':')[1].strip())
                except:
                    pass
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()

        return label, confidence, reasoning


class EvalHarness:
    """
    Eval harness for running evaluations with each config change.
    Implements the Label → Align → Run loop.
    """

    def __init__(self, db_path: Path = EVAL_DB_PATH):
        self.dataset = EvalDataset(db_path)
        self.judge = LLMJudge()

    def run_alignment_check(self, criteria_name: str) -> dict:
        """
        Step 2: Check alignment between LLM judge and human labels.
        Returns alignment metrics.
        """
        criteria = self.dataset.get_criteria(criteria_name)
        if not criteria:
            raise ValueError(f"Criteria '{criteria_name}' not found")

        examples = self.dataset.get_examples(criteria_name)
        if len(examples) < 3:
            return {
                "error": f"Need at least 3 labeled examples, have {len(examples)}",
                "alignment_score": 0.0
            }

        # Use some examples for few-shot, test on rest
        few_shot = examples[:3]
        test_examples = examples[3:] if len(examples) > 3 else examples

        results = []
        aligned_count = 0

        for ex in test_examples:
            predicted_label, confidence, reasoning = self.judge.judge(
                criteria, ex.output_text, few_shot
            )

            aligned = predicted_label == ex.label
            if aligned:
                aligned_count += 1

            result = EvalResult(
                example_id=ex.id,
                predicted_label=predicted_label,
                confidence=confidence,
                reasoning=reasoning,
                aligned_with_human=aligned,
                criteria_name=criteria_name,
                judge_model=self.judge.model
            )
            results.append(result)

            # Store result
            self._store_result(result)

        alignment_score = aligned_count / len(test_examples) if test_examples else 0.0

        # Store alignment history
        self._store_alignment(criteria_name, alignment_score)

        return {
            "criteria_name": criteria_name,
            "alignment_score": alignment_score,
            "total_tested": len(test_examples),
            "aligned_count": aligned_count,
            "misaligned": [r for r in results if not r.aligned_with_human],
            "judge_model": self.judge.model
        }

    def evaluate_output(self, criteria_name: str, output_text: str,
                       input_text: str = "") -> EvalResult:
        """
        Step 3: Evaluate a new output using the aligned judge.
        """
        criteria = self.dataset.get_criteria(criteria_name)
        if not criteria:
            raise ValueError(f"Criteria '{criteria_name}' not found")

        # Get few-shot examples for alignment
        examples = self.dataset.get_examples(criteria_name, limit=5)

        predicted_label, confidence, reasoning = self.judge.judge(
            criteria, output_text, examples
        )

        result = EvalResult(
            example_id=hashlib.md5(output_text.encode()).hexdigest()[:12],
            predicted_label=predicted_label,
            confidence=confidence,
            reasoning=reasoning,
            aligned_with_human=True,  # No human label to compare
            criteria_name=criteria_name,
            judge_model=self.judge.model
        )

        self._store_result(result)
        return result

    def _store_result(self, result: EvalResult):
        """Store eval result in database"""
        conn = sqlite3.connect(self.dataset.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO eval_results
            (example_id, predicted_label, confidence, reasoning,
             aligned_with_human, criteria_name, judge_model, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.example_id,
            result.predicted_label,
            result.confidence,
            result.reasoning,
            1 if result.aligned_with_human else 0,
            result.criteria_name,
            result.judge_model,
            result.timestamp
        ))
        conn.commit()
        conn.close()

    def _store_alignment(self, criteria_name: str, score: float):
        """Store alignment history"""
        conn = sqlite3.connect(self.dataset.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alignment_history
            (criteria_name, alignment_score, judge_model, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (
            criteria_name,
            score,
            self.judge.model,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def get_stats(self, criteria_name: str = None) -> dict:
        """Get evaluation statistics"""
        conn = sqlite3.connect(self.dataset.db_path)
        cursor = conn.cursor()

        if criteria_name:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN aligned_with_human = 1 THEN 1 ELSE 0 END) as aligned,
                    AVG(confidence) as avg_confidence
                FROM eval_results WHERE criteria_name = ?
            ''', (criteria_name,))
        else:
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN aligned_with_human = 1 THEN 1 ELSE 0 END) as aligned,
                    AVG(confidence) as avg_confidence
                FROM eval_results
            ''')

        row = cursor.fetchone()
        conn.close()

        return {
            "total_evals": row[0] or 0,
            "aligned": row[1] or 0,
            "alignment_rate": (row[1] / row[0]) if row[0] else 0,
            "avg_confidence": row[2] or 0
        }


# Pre-defined criteria for agentic system evaluation
AGENTIC_CRITERIA = {
    "not_ai_sounding": EvalCriteria(
        name="not_ai_sounding",
        description="Evaluate whether output sounds natural vs AI-generated",
        pass_description="Output sounds natural, authentic, and human-like",
        fail_description="Output sounds formulaic, uses AI markers like em-dashes, or is overly polished",
        examples_pass=[
            "Just pushed a fix for the auth bug. Let me know if you see issues.",
            "The config file needs updating - missing the new API endpoint."
        ],
        examples_fail=[
            "I've successfully implemented the solution—leveraging cutting-edge techniques to supercharge your workflow.",
            "This comprehensive update revolutionizes the user experience—transforming how you interact with the system."
        ]
    ),
    "code_quality": EvalCriteria(
        name="code_quality",
        description="Evaluate whether generated code follows best practices",
        pass_description="Code is clean, readable, handles errors, and follows conventions",
        fail_description="Code has bugs, missing error handling, or poor style",
        examples_pass=[
            "def get_user(id: int) -> Optional[User]:\n    try:\n        return db.query(User).get(id)\n    except DatabaseError as e:\n        logger.error(f'Failed to get user {id}: {e}')\n        return None"
        ],
        examples_fail=[
            "def get_user(id):\n    return db.query(User).get(id)  # no error handling, no types"
        ]
    ),
    "memory_summary_quality": EvalCriteria(
        name="memory_summary_quality",
        description="Evaluate memory consolidation summary quality",
        pass_description="Summary captures key information, is concise, and preserves important context",
        fail_description="Summary loses important information, is too verbose, or misrepresents content",
        examples_pass=[
            "Session focused on implementing OAuth2 auth flow. Key decisions: using JWT tokens, 1-hour expiry. Unfinished: refresh token logic."
        ],
        examples_fail=[
            "We did some stuff with authentication and things were implemented and there were tokens involved."
        ]
    ),
    "agent_response_helpful": EvalCriteria(
        name="agent_response_helpful",
        description="Evaluate whether agent response is helpful and actionable",
        pass_description="Response directly addresses the question with actionable information",
        fail_description="Response is vague, off-topic, or doesn't help solve the problem",
        examples_pass=[
            "The error is caused by a missing import. Add 'from typing import Optional' at line 1."
        ],
        examples_fail=[
            "There might be an issue with your code. You could try various things to fix it."
        ]
    )
}


def setup_default_criteria():
    """Initialize database with default agentic criteria"""
    dataset = EvalDataset()
    for criteria in AGENTIC_CRITERIA.values():
        dataset.add_criteria(criteria)
    print(f"Initialized {len(AGENTIC_CRITERIA)} default criteria")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "init":
        setup_default_criteria()
    else:
        print("Agent Eval Framework")
        print("Usage: python agent_eval_framework.py init  # Initialize default criteria")
        print("\nPython API:")
        print("  from agent_eval_framework import EvalHarness, AGENTIC_CRITERIA")
        print("  harness = EvalHarness()")
        print("  result = harness.evaluate_output('not_ai_sounding', 'your output text')")
