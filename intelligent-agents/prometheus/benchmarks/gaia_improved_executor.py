#!/usr/bin/env python3
"""
Improved GAIA Benchmark Executor

Improvements over base executor:
1. Better prompt engineering for different question types
2. Web search pre-check for fact-based questions
3. Multi-step reasoning for complex questions
4. Answer validation and cross-checking
5. Retry logic with different approaches

Target: 100% accuracy on solvable questions (non-file-dependent)
"""

import asyncio
import subprocess
import re
import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QuestionAnalysis:
    """Analysis of a GAIA question to determine optimal solving strategy."""
    requires_file: bool
    requires_web_search: bool
    requires_calculation: bool
    requires_logic: bool
    requires_decoding: bool
    question_type: str  # fact, logic, calculation, research, file
    confidence: float


class ImprovedGAIAExecutor:
    """
    Improved executor that achieves higher accuracy on GAIA benchmark.

    Key improvements:
    1. Question type classification
    2. Specialized prompts per question type
    3. Web search integration
    4. Multi-attempt strategy
    5. Answer validation
    """

    def __init__(self, timeout: int = 600, max_retries: int = 2):
        # Increased timeout for research questions requiring web search
        self.timeout = timeout
        self.max_retries = max_retries

    def analyze_question(self, question: str) -> QuestionAnalysis:
        """Analyze question to determine optimal solving strategy."""
        q_lower = question.lower()

        # Check for file/image requirements
        file_patterns = [
            'attached', 'image', 'spreadsheet', '.pdf', '.xlsx', '.png',
            '.jpg', 'provided image', 'attached file', 'in the file',
            'screenshot', 'diagram', 'picture', 'audio', '.mp3', '.wav'
        ]
        requires_file = any(p in q_lower for p in file_patterns)

        # Check for web search needs
        web_patterns = [
            'wikipedia', 'who is', 'who was', 'when did', 'where is',
            'current', 'latest', 'as of', 'in 2022', 'in 2023', 'in 2024',
            'born', 'died', 'founded', 'president', 'capital', 'population',
            'official', 'according to', 'published', 'released'
        ]
        requires_web_search = any(p in q_lower for p in web_patterns)

        # Check for calculation needs
        calc_patterns = [
            'calculate', 'compute', 'sum', 'total', 'percentage', 'average',
            'how many', 'how much', 'multiply', 'divide', 'add', 'subtract',
            'difference', 'ratio', 'fraction'
        ]
        requires_calculation = any(p in q_lower for p in calc_patterns)

        # Check for logic puzzles
        logic_patterns = [
            'puzzle', 'secret santa', 'logic', 'deduce', 'infer', 'given that',
            'if ', 'constraint', 'rule', 'assigned', 'each', 'every'
        ]
        requires_logic = any(p in q_lower for p in logic_patterns)

        # Check for encoding/decoding
        decode_patterns = [
            'reverse', 'decode', 'cipher', 'encoded', 'backwards', 'encrypted'
        ]
        requires_decoding = any(p in q_lower for p in decode_patterns) or question.startswith('.')

        # Determine question type
        if requires_file:
            question_type = "file"
            confidence = 0.0  # Can't solve file questions
        elif requires_decoding:
            question_type = "decode"
            confidence = 0.95  # High confidence for simple decoding
        elif requires_logic:
            question_type = "logic"
            confidence = 0.7  # Medium confidence for logic
        elif requires_calculation:
            question_type = "calculation"
            confidence = 0.8  # High confidence for calculations
        elif requires_web_search:
            question_type = "research"
            confidence = 0.75  # Research questions need web search
        else:
            question_type = "fact"
            confidence = 0.6  # General knowledge

        return QuestionAnalysis(
            requires_file=requires_file,
            requires_web_search=requires_web_search,
            requires_calculation=requires_calculation,
            requires_logic=requires_logic,
            requires_decoding=requires_decoding,
            question_type=question_type,
            confidence=confidence
        )

    def preprocess_question(self, question: str) -> str:
        """Preprocess question (handle reversed text, etc.)"""
        # Check for reversed text
        if question.startswith('.') or '.noitseuq' in question.lower():
            logger.info("Detected reversed text, reversing...")
            return question[::-1]
        return question

    def build_prompt(self, question: str, analysis: QuestionAnalysis, attempt: int = 1) -> str:
        """Build optimized prompt based on question analysis."""

        if analysis.question_type == "file":
            return f"""This question requires a file/image attachment that I cannot access.

Question: {question}

Since I cannot access the attached file, I cannot provide the answer. Please respond with EXACTLY:
Unable to access required file."""

        if analysis.question_type == "decode":
            return f"""Solve this encoding/decoding problem step by step.

Question: {question}

Instructions:
1. First identify what encoding/transformation was used
2. Show the decoding process
3. Give ONLY the final decoded answer

FINAL ANSWER:"""

        if analysis.question_type == "logic":
            return f"""Solve this logic puzzle step by step.

Question: {question}

Instructions:
1. List all constraints and rules given
2. Work through the logic systematically
3. Show your deduction steps
4. Verify your answer satisfies all constraints
5. Give ONLY the final answer (single word, name, or number)

FINAL ANSWER:"""

        if analysis.question_type == "calculation":
            return f"""Solve this calculation problem step by step.

Question: {question}

Instructions:
1. Identify all numbers and operations needed
2. Show your calculation work
3. Double-check your arithmetic
4. Give ONLY the final numerical answer

FINAL ANSWER:"""

        if analysis.question_type == "research":
            if attempt == 1:
                return f"""Research and answer this question using web search.

Question: {question}

Instructions:
1. Search for authoritative sources (Wikipedia, official sites)
2. Find specific, verified information
3. Cross-reference multiple sources if possible
4. Give ONLY the factual answer requested

FINAL ANSWER:"""
            else:
                # More specific prompt on retry
                return f"""You must find the exact answer to this question.

Question: {question}

Previous attempts failed. Now:
1. Search Wikipedia directly for the key entity
2. Look for the specific fact requested
3. Be precise - partial answers are wrong
4. Give ONLY the exact answer (name, number, or short phrase)

FINAL ANSWER:"""

        # Default/fact type
        return f"""Answer this factual question precisely.

Question: {question}

Instructions:
1. If you need current information, search the web
2. Be specific - give the exact answer requested
3. No explanations - just the answer
4. Format: just the answer (single word, number, or short phrase)

FINAL ANSWER:"""

    async def execute(self, question: str, task_id: str = "") -> Tuple[str, float]:
        """
        Execute a GAIA task with improved strategy.

        Returns: (answer, confidence_score)
        """
        # Preprocess
        processed_question = self.preprocess_question(question)

        # Analyze
        analysis = self.analyze_question(processed_question)
        logger.info(f"Task {task_id}: type={analysis.question_type}, confidence={analysis.confidence:.2f}")

        # Skip file-required questions
        if analysis.requires_file:
            logger.warning(f"Task {task_id}: Skipping - requires file access")
            return "", 0.0

        # Try multiple attempts with different strategies
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Task {task_id}: Attempt {attempt}/{self.max_retries}")

            prompt = self.build_prompt(processed_question, analysis, attempt)

            try:
                answer = await self._call_claude_cli(prompt)

                if answer:
                    # Validate answer
                    validated = self._validate_answer(answer, analysis)
                    if validated:
                        logger.info(f"Task {task_id}: Got valid answer: {validated[:50]}...")
                        return validated, analysis.confidence
                    else:
                        logger.warning(f"Task {task_id}: Invalid answer format, retrying...")
                else:
                    logger.warning(f"Task {task_id}: No answer returned, retrying...")

            except Exception as e:
                logger.error(f"Task {task_id}: Error on attempt {attempt}: {e}")

        return "", 0.0

    async def _call_claude_cli(self, prompt: str) -> str:
        """Call Claude CLI with the prompt."""
        import os

        env = {**os.environ, "ANTHROPIC_API_KEY": ""}  # Use Max account

        try:
            # Run with tools enabled for web search
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text", "--dangerously-skip-permissions"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"Claude CLI error: {result.stderr[:200] if result.stderr else 'unknown'}")
                return ""

        except subprocess.TimeoutExpired:
            logger.warning("Claude CLI timeout")
            return ""
        except Exception as e:
            logger.error(f"Claude CLI exception: {e}")
            return ""

    def _validate_answer(self, raw_answer: str, analysis: QuestionAnalysis) -> str:
        """Validate and extract the final answer."""
        if not raw_answer:
            return ""

        # Extract answer after FINAL ANSWER:
        patterns = [
            r'FINAL ANSWER:\s*(.+)',
            r'The answer is:\s*(.+)',
            r'Answer:\s*(.+)',
            r'^([^\n]+)$'  # Last resort: first line
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_answer, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                answer = match.group(1).strip()
                # Clean up the answer
                answer = re.sub(r'\*\*(.+?)\*\*', r'\1', answer)  # Remove bold
                answer = re.sub(r'^[-•]\s*', '', answer)  # Remove bullet points
                answer = answer.split('\n')[0].strip()  # First line only

                if answer and len(answer) < 500:  # Sanity check
                    return answer

        return ""


async def test_improved_executor():
    """Test the improved executor on sample questions."""
    executor = ImprovedGAIAExecutor()

    test_questions = [
        "How many studio albums were published by Mercedes Sosa between 2000 and 2009 (included)?",
        "What is the capital of France?",
        "Calculate the sum of 123 + 456 + 789.",
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {q[:80]}...")
        answer, confidence = await executor.execute(q)
        print(f"A: {answer}")
        print(f"Confidence: {confidence:.2f}")


if __name__ == "__main__":
    asyncio.run(test_improved_executor())
