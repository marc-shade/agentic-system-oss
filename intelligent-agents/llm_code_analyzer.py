#!/usr/bin/env python3
"""
LLM-Based Code Analyzer with Symbolic Execution
Based on SymPrompt (arXiv:2507.05619) - Execution-Path-Guided Code Generation

This module replaces hardcoded improvement detection with AI-powered analysis
that can detect optimization opportunities in ANY code, not just specific functions.

Key Capabilities:
- Symbolic execution to understand code semantics
- LLM-based improvement proposal generation
- Ollama integration (local, free inference)
- Confidence scoring for proposals
- AST parsing for structural analysis
"""

import ast
import json
import logging
import subprocess
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    """Types of code optimizations."""
    LIST_COMPREHENSION = "list_comprehension"
    BUILTIN_FUNCTION = "builtin_function"
    ALGORITHM_IMPROVE = "algorithm_improve"
    DATA_STRUCTURE = "data_structure"
    REDUNDANT_OPERATION = "redundant_operation"
    MEMORY_OPTIMIZATION = "memory_optimization"


@dataclass
class CodeAnalysis:
    """Results from symbolic execution analysis."""
    function_name: str
    complexity_score: float  # 0.0-1.0 (higher = more complex)
    loop_count: int
    nested_loops: int
    builtin_opportunities: List[str]  # Built-in functions that could be used
    algorithm_type: str  # e.g., "linear_search", "bubble_sort", "manual_accumulation"
    bottleneck_lines: List[int]  # Line numbers of bottlenecks
    execution_paths: List[str]  # Simplified execution flow descriptions
    ast_node: ast.FunctionDef  # Original AST node


@dataclass
class ImprovementProposal:
    """LLM-generated improvement proposal."""
    function_name: str
    optimization_type: OptimizationType
    code_before: str
    code_after: str
    description: str
    expected_improvement: float  # Percentage (e.g., 0.25 = 25%)
    confidence_score: float  # 0.0-1.0
    reasoning: str
    safety_score: float  # 0.0-1.0


class SymbolicExecutionAnalyzer:
    """
    Analyzes code using symbolic execution techniques.

    Based on SymPrompt's execution-path-guided approach. Extracts semantic
    information about code behavior without actually executing it.
    """

    def __init__(self):
        self.builtin_alternatives = {
            'manual_sum': 'sum()',
            'manual_max': 'max()',
            'manual_min': 'min()',
            'manual_count': 'list.count()',
            'manual_reverse': '[::-1]',
            'manual_sort': 'sorted()',
            'manual_filter': 'list comprehension',
            'manual_map': 'list comprehension',
        }

    def analyze_code(self, code: str, target_file: str = "") -> List[CodeAnalysis]:
        """
        Analyze code and extract semantic information.

        Args:
            code: Python source code to analyze
            target_file: Optional file path for context

        Returns:
            List of code analyses for each function found
        """
        try:
            tree = ast.parse(code)
            analyses = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Skip test functions
                    if node.name.startswith('test_'):
                        continue

                    analysis = self._analyze_function(node, code)
                    if analysis:
                        analyses.append(analysis)

            logger.info(f"Analyzed {len(analyses)} functions in {target_file or 'code'}")
            return analyses

        except SyntaxError as e:
            logger.error(f"Syntax error in code: {e}")
            return []
        except Exception as e:
            logger.error(f"Analysis error: {e}\n{traceback.format_exc()}")
            return []

    def _analyze_function(self, node: ast.FunctionDef, full_code: str) -> Optional[CodeAnalysis]:
        """Analyze a single function using symbolic execution."""
        try:
            # Count loops and nesting
            loop_count = 0
            nested_loops = 0
            max_nesting_level = 0
            current_nesting = 0

            for child in ast.walk(node):
                if isinstance(child, (ast.For, ast.While)):
                    loop_count += 1
                    current_nesting += 1
                    max_nesting_level = max(max_nesting_level, current_nesting)
                    if current_nesting > 1:
                        nested_loops += 1

            # Detect builtin opportunities
            builtin_opportunities = self._detect_builtin_opportunities(node)

            # Identify algorithm type
            algorithm_type = self._identify_algorithm_type(node)

            # Extract execution paths
            execution_paths = self._extract_execution_paths(node)

            # Calculate complexity score
            complexity_score = self._calculate_complexity(
                loop_count, nested_loops, len(builtin_opportunities)
            )

            # Find bottleneck lines (loops with complex operations)
            bottleneck_lines = self._find_bottleneck_lines(node)

            return CodeAnalysis(
                function_name=node.name,
                complexity_score=complexity_score,
                loop_count=loop_count,
                nested_loops=nested_loops,
                builtin_opportunities=builtin_opportunities,
                algorithm_type=algorithm_type,
                bottleneck_lines=bottleneck_lines,
                execution_paths=execution_paths,
                ast_node=node
            )

        except Exception as e:
            logger.warning(f"Failed to analyze function {node.name}: {e}")
            return None

    def _detect_builtin_opportunities(self, node: ast.FunctionDef) -> List[str]:
        """Detect opportunities to use built-in functions."""
        opportunities = []

        # Check for manual sum pattern
        if self._has_manual_sum(node):
            opportunities.append("sum()")

        # Check for manual max/min
        if self._has_manual_max_min(node):
            opportunities.append("max()/min()")

        # Check for manual count
        if self._has_manual_count(node):
            opportunities.append("list.count()")

        # Check for manual reverse
        if self._has_manual_reverse(node):
            opportunities.append("[::-1] slicing")

        # Check for manual filter/map patterns
        if self._has_manual_filter_map(node):
            opportunities.append("list comprehension")

        # Check for manual sort
        if self._has_manual_sort(node):
            opportunities.append("sorted()")

        return opportunities

    def _has_manual_sum(self, node: ast.FunctionDef) -> bool:
        """Detect manual sum pattern: total = 0; for x in y: total += x"""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in child.body:
                    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.op, ast.Add):
                        return True
        return False

    def _has_manual_max_min(self, node: ast.FunctionDef) -> bool:
        """Detect manual max/min pattern with comparisons in loop."""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in ast.walk(child):
                    if isinstance(stmt, ast.Compare):
                        if isinstance(stmt.ops[0], (ast.Gt, ast.Lt, ast.GtE, ast.LtE)):
                            return True
        return False

    def _has_manual_count(self, node: ast.FunctionDef) -> bool:
        """Detect manual counting pattern."""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in child.body:
                    if isinstance(stmt, ast.If):
                        # Check for count += 1 or similar
                        for if_stmt in stmt.body:
                            if isinstance(if_stmt, ast.AugAssign):
                                return True
        return False

    def _has_manual_reverse(self, node: ast.FunctionDef) -> bool:
        """Detect manual string/list reversal."""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                for stmt in child.body:
                    # result = char + result pattern
                    if isinstance(stmt, ast.Assign):
                        if isinstance(stmt.value, ast.BinOp):
                            return True
        return False

    def _has_manual_filter_map(self, node: ast.FunctionDef) -> bool:
        """Detect manual filter/map pattern: for x in y: if condition: result.append(transform(x))"""
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                has_append = False
                has_condition = False
                for stmt in child.body:
                    if isinstance(stmt, ast.If):
                        has_condition = True
                    if isinstance(stmt, ast.Expr):
                        if isinstance(stmt.value, ast.Call):
                            if hasattr(stmt.value.func, 'attr') and stmt.value.func.attr == 'append':
                                has_append = True
                if has_append:  # Can be with or without condition (map vs filter+map)
                    return True
        return False

    def _has_manual_sort(self, node: ast.FunctionDef) -> bool:
        """Detect manual sorting (e.g., bubble sort)."""
        nested_loop_count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.For):
                nested_loop_count += 1

        # Nested loops with swapping often indicate manual sort
        if nested_loop_count >= 2:
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    # Check for tuple unpacking (swap pattern)
                    if isinstance(child.targets[0], ast.Tuple):
                        return True
        return False

    def _identify_algorithm_type(self, node: ast.FunctionDef) -> str:
        """Identify the type of algorithm used."""
        if self._has_manual_sort(node):
            return "manual_sort"
        elif self._has_manual_sum(node):
            return "manual_accumulation"
        elif self._has_manual_max_min(node):
            return "linear_search"
        elif self._has_manual_count(node):
            return "linear_count"
        elif self._has_manual_filter_map(node):
            return "manual_filter_map"
        else:
            return "unknown"

    def _extract_execution_paths(self, node: ast.FunctionDef) -> List[str]:
        """Extract simplified execution paths."""
        paths = []

        for child in node.body:
            if isinstance(child, ast.For):
                paths.append(f"Loop over {ast.unparse(child.target)}")
            elif isinstance(child, ast.If):
                paths.append(f"Conditional branch")
            elif isinstance(child, ast.Return):
                paths.append(f"Return {ast.unparse(child.value) if child.value else 'None'}")

        return paths if paths else ["Single execution path"]

    def _calculate_complexity(self, loop_count: int, nested_loops: int,
                             builtin_ops: int) -> float:
        """Calculate complexity score (0.0-1.0, higher = more complex)."""
        score = 0.0
        score += loop_count * 0.2
        score += nested_loops * 0.3
        score += builtin_ops * 0.1
        return min(1.0, score)

    def _find_bottleneck_lines(self, node: ast.FunctionDef) -> List[int]:
        """Find line numbers of potential bottlenecks."""
        bottlenecks = []

        for child in ast.walk(node):
            if isinstance(child, ast.For):
                if hasattr(child, 'lineno'):
                    bottlenecks.append(child.lineno)
            elif isinstance(child, (ast.While, ast.If)):
                if hasattr(child, 'lineno'):
                    bottlenecks.append(child.lineno)

        return bottlenecks


class LLMCodeDetector:
    """
    Uses LLM to detect improvement opportunities based on symbolic execution.

    Integrates symbolic execution analysis with Ollama LLM to generate
    concrete improvement proposals.
    """

    def __init__(self, model: str = "qwen2.5-coder:latest", use_ollama: bool = True):
        """
        Initialize LLM detector.

        Args:
            model: Model name (gpt-oss:20b for Ollama, or claude-sonnet-4-5 for Anthropic)
            use_ollama: If True, use local Ollama; if False, use Anthropic API
        """
        self.analyzer = SymbolicExecutionAnalyzer()
        self.model = model
        self.use_ollama = use_ollama
        logger.info(f"Initialized LLM detector with model: {model} (ollama={use_ollama})")

    def detect_improvements(self, code: str, target_file: str = "",
                           insights: Optional[List] = None) -> List[ImprovementProposal]:
        """
        Detect improvement opportunities using LLM analysis.

        Args:
            code: Python source code to analyze
            target_file: Optional file path for context
            insights: Optional list of research insights to incorporate

        Returns:
            List of improvement proposals with confidence scores
        """
        # Step 1: Symbolic execution analysis
        analyses = self.analyzer.analyze_code(code, target_file)

        if not analyses:
            logger.info("No functions found to analyze")
            return []

        logger.info(f"Analyzing {len(analyses)} functions with LLM...")

        # Step 2: Generate proposals for each function
        proposals = []
        for analysis in analyses:
            try:
                function_code = ast.unparse(analysis.ast_node)
                proposal = self._generate_proposal_with_llm(
                    analysis, function_code, insights or []
                )
                if proposal and proposal.confidence_score >= 0.6:
                    proposals.append(proposal)
                    logger.info(f"  ✓ {proposal.function_name}: {proposal.optimization_type.value} "
                              f"(confidence: {proposal.confidence_score:.2f})")
            except Exception as e:
                logger.warning(f"Failed to generate proposal for {analysis.function_name}: {e}")
                continue

        return proposals

    def _generate_proposal_with_llm(self, analysis: CodeAnalysis,
                                   function_code: str,
                                   insights: List) -> Optional[ImprovementProposal]:
        """Generate improvement proposal using LLM."""
        # Build analysis context for LLM
        analysis_context = f"""
Function: {analysis.function_name}
Complexity: {analysis.complexity_score:.2f}
Loops: {analysis.loop_count} (nested: {analysis.nested_loops})
Algorithm type: {analysis.algorithm_type}
Builtin opportunities: {', '.join(analysis.builtin_opportunities) if analysis.builtin_opportunities else 'None'}
Execution paths: {len(analysis.execution_paths)}
Bottleneck lines: {analysis.bottleneck_lines}
"""

        # Build prompt - simplified for better JSON output
        prompt = f"""Optimize this Python function. Output ONLY valid JSON, no other text.

FUNCTION:
{function_code}

ANALYSIS:
- Complexity: {analysis.complexity_score:.2f}
- Loops: {analysis.loop_count} (nested: {analysis.nested_loops})
- Opportunities: {', '.join(analysis.builtin_opportunities) if analysis.builtin_opportunities else 'none'}

JSON OUTPUT ONLY:
{{
    "optimization_type": "list_comprehension",
    "code_after": "def {analysis.function_name}(args):\\n    return [optimized code]",
    "description": "Short description",
    "expected_improvement": 0.25,
    "confidence_score": 0.80,
    "reasoning": "Why this works",
    "safety_score": 0.90
}}

CRITICAL: Output ONLY the JSON. No thinking, no markdown, no extra text. Just the JSON object."""

        # Call LLM
        try:
            response_text = self._call_llm(prompt)

            # Parse JSON response
            proposal_data = self._parse_llm_response(response_text)

            if not proposal_data:
                return None

            # Create proposal object
            return ImprovementProposal(
                function_name=analysis.function_name,
                optimization_type=OptimizationType(proposal_data['optimization_type']),
                code_before=function_code,
                code_after=proposal_data['code_after'],
                description=proposal_data['description'],
                expected_improvement=proposal_data['expected_improvement'],
                confidence_score=proposal_data['confidence_score'],
                reasoning=proposal_data['reasoning'],
                safety_score=proposal_data.get('safety_score', 0.8)
            )

        except Exception as e:
            logger.error(f"LLM generation failed: {e}\n{traceback.format_exc()}")
            return None

    def _call_llm(self, prompt: str) -> str:
        """Call LLM (Ollama or Anthropic) with prompt."""
        if self.use_ollama:
            return self._call_ollama(prompt)
        else:
            return self._call_anthropic(prompt)

    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama model."""
        try:
            import os
            env = os.environ.copy()
            result = subprocess.run(
                ["/usr/local/bin/ollama", "run", self.model, prompt],
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )

            if result.returncode != 0:
                logger.error(f"Ollama error: {result.stderr}")
                return ""

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error("Ollama call timed out after 120s")
            return ""
        except Exception as e:
            logger.error(f"Ollama subprocess error: {e}")
            return ""

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API (fallback)."""
        try:
            # Use subprocess to avoid importing anthropic (following existing pattern)
            import os
            result = subprocess.run(
                ["python3", "-c", f"""
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=4096,
    messages=[{{"role": "user", "content": {repr(prompt)}}}]
)
print(response.content[0].text)
"""],
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")}
            )

            if result.returncode != 0:
                logger.error(f"Anthropic API error: {result.stderr}")
                return ""

            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            return ""

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith('```'):
                lines = response.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines[-1].strip() == '```':
                    lines = lines[:-1]
                response = '\n'.join(lines)

            data = json.loads(response)

            # Validate required fields
            required = ['optimization_type', 'code_after', 'description',
                       'expected_improvement', 'confidence_score', 'reasoning']
            for field in required:
                if field not in data:
                    logger.warning(f"Missing required field: {field}")
                    return None

            # Validate types and ranges
            if not isinstance(data['confidence_score'], (int, float)):
                return None
            if not (0.0 <= data['confidence_score'] <= 1.0):
                return None
            if not isinstance(data['expected_improvement'], (int, float)):
                return None

            return data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}\nResponse: {response[:200]}")
            return None
        except Exception as e:
            logger.error(f"Response parsing error: {e}")
            return None

    def _format_insights(self, insights: List) -> str:
        """Format research insights for prompt."""
        if not insights:
            return "No recent research insights available."

        formatted = []
        for i, insight in enumerate(insights[:3], 1):  # Use top 3 insights
            if hasattr(insight, 'title') and hasattr(insight, 'summary'):
                formatted.append(f"{i}. {insight.title}: {insight.summary}")

        return '\n'.join(formatted) if formatted else "No recent research insights available."


# Integration function for autonomous_recursive_agi_loop.py
def create_llm_detector(use_ollama: bool = True) -> LLMCodeDetector:
    """
    Factory function to create LLM detector.

    Args:
        use_ollama: If True, use local Ollama (free); if False, use Anthropic API

    Returns:
        Configured LLMCodeDetector instance
    """
    model = "qwen2.5-coder:latest" if use_ollama else "claude-sonnet-4-5-20250929"
    return LLMCodeDetector(model=model, use_ollama=use_ollama)


# Testing interface
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test with sample_module.py
    sample_file = Path(__file__).parent / "sample_module.py"

    if len(sys.argv) > 1:
        sample_file = Path(sys.argv[1])

    if not sample_file.exists():
        print(f"Error: {sample_file} not found")
        sys.exit(1)

    print(f"Testing LLM code analyzer on: {sample_file}")
    print("=" * 60)

    with open(sample_file, 'r') as f:
        code = f.read()

    detector = create_llm_detector(use_ollama=True)
    proposals = detector.detect_improvements(code, str(sample_file))

    print(f"\n{'='*60}")
    print(f"DETECTED {len(proposals)} IMPROVEMENTS")
    print(f"{'='*60}\n")

    for i, proposal in enumerate(proposals, 1):
        print(f"{i}. {proposal.function_name}")
        print(f"   Type: {proposal.optimization_type.value}")
        print(f"   Expected gain: {proposal.expected_improvement:.1%}")
        print(f"   Confidence: {proposal.confidence_score:.2f}")
        print(f"   Safety: {proposal.safety_score:.2f}")
        print(f"   Description: {proposal.description}")
        print(f"\n   Reasoning: {proposal.reasoning}")
        print(f"\n   Code after:")
        print("   " + "\n   ".join(proposal.code_after.split('\n')))
        print()
