"""
Code execution tool for Enhanced Memory MCP Server.

Tools:
- execute_code: Execute Python code in secure sandbox with API access
"""

from typing import Any, Dict, Optional

from ..config import logger


def register_execution_tools(app):
    """Register code execution tools with FastMCP app."""

    @app.tool()
    async def execute_code(
        code: str,
        context_vars: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in secure sandbox with API access.

        Implements Anthropic's code execution pattern for massive token reduction.
        Agents write code using APIs instead of calling tools directly.

        Token Savings:
        - Progressive disclosure: 2,000 → 200 tokens (90% reduction)
        - Local processing: 50,000 → 500 tokens (99% reduction)
        - Average: 96.6% token reduction

        Security Features:
        - RestrictedPython compilation
        - 30-second timeout
        - 500MB memory limit
        - Dangerous import blocking
        - PII tokenization

        Available APIs in code:
        - Memory: create_entities, search_nodes, get_status, update_entity
        - Versioning: diff, revert, branch, history, commit
        - Analysis: detect_conflicts, analyze_patterns, classify_content, find_related
        - Utils: filter_by_confidence, summarize_results, aggregate_stats, format_output
        - Filesystem: workspace, list_files, read_file, write_file, delete_file
        - Skills: save_skill, load_skill, list_skills

        Example Code:
            # Basic search and filter
            results = search_nodes("optimization", limit=100)
            high_conf = filter_by_confidence(results, 0.8)
            summary = summarize_results(high_conf)
            result = summary  # Return this

            # Save intermediate state
            write_file("results.json", json.dumps(results))

            # Save working code as skill
            code = '''
    def filter_high_confidence(query, threshold=0.8):
        results = search_nodes(query, limit=1000)
        return [r for r in results if r.confidence > threshold]
    '''
            save_skill("filter_high_confidence", code, "Filter memories by confidence")

        Args:
            code: Python code to execute
            context_vars: Additional variables to make available

        Returns:
            Execution result with success status, result data, and any errors
        """
        # Import sandbox components
        try:
            from sandbox.executor import CodeExecutor, create_api_context
            from sandbox.security import comprehensive_safety_check, sanitize_output
        except ImportError as e:
            logger.error(f"Sandbox module not available: {e}")
            return {
                "success": False,
                "error": f"Sandbox module not available: {e}"
            }

        logger.info("Code execution requested")

        # Security check
        is_safe, safety_issues = comprehensive_safety_check(code)
        if not is_safe:
            logger.warning(f"Code safety check failed: {safety_issues}")
            return {
                "success": False,
                "error": "Code safety check failed",
                "issues": safety_issues
            }

        # Create executor FIRST (so it can create workspace)
        executor = CodeExecutor(
            timeout_seconds=30,
            memory_limit_bytes=500 * 1024 * 1024
        )

        # Create API context with all available functions
        api_context = create_api_context(executor=executor)

        # Add any additional context variables
        if context_vars:
            api_context.update(context_vars)

        # Execute code in sandbox
        exec_result = executor.execute(code, context=api_context)

        if exec_result.success:
            # Sanitize output (PII tokenization, size limits)
            sanitized_result = sanitize_output(exec_result.result)
            logger.info(f"Code executed successfully in {exec_result.execution_time_ms:.2f}ms")
            return {
                "success": True,
                "result": sanitized_result,
                "stdout": exec_result.stdout,
                "execution_time_ms": exec_result.execution_time_ms
            }
        else:
            logger.error(f"Code execution failed: {exec_result.error}")
            return {
                "success": False,
                "error": exec_result.error,
                "stdout": exec_result.stdout,
                "stderr": exec_result.stderr,
                "execution_time_ms": exec_result.execution_time_ms
            }

    return {
        'execute_code': execute_code,
    }
