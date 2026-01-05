import os
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from loguru import logger

class DevelopmentAssistantManager:
    """
    Manages development assistance for the Software Planning MCP.
    Provides code generation, code analysis, refactoring support, and testing assistance.
    """
    
    def __init__(self):
        self.templates_dir = Path(os.path.expanduser("~/.mcp/templates"))
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.code_analysis_tools = self._discover_code_analysis_tools()
    
    def _discover_code_analysis_tools(self) -> Dict[str, Dict[str, Any]]:
        """Discover available code analysis tools."""
        tools = {}
        
        # Check for common static analysis tools
        analysis_tools = [
            {
                "name": "pylint",
                "command": "pylint",
                "languages": ["python"],
                "description": "Python static code analysis tool"
            },
            {
                "name": "eslint",
                "command": "eslint",
                "languages": ["javascript", "typescript"],
                "description": "JavaScript/TypeScript linter"
            },
            {
                "name": "flake8",
                "command": "flake8",
                "languages": ["python"],
                "description": "Python style guide enforcement"
            },
            {
                "name": "mypy",
                "command": "mypy",
                "languages": ["python"],
                "description": "Python static type checker"
            },
            {
                "name": "black",
                "command": "black",
                "languages": ["python"],
                "description": "Python code formatter"
            },
            {
                "name": "prettier",
                "command": "prettier",
                "languages": ["javascript", "typescript", "html", "css", "json", "yaml"],
                "description": "Code formatter for multiple languages"
            },
        ]
        
        for tool in analysis_tools:
            if self._is_executable_available(tool["command"]):
                tools[tool["name"]] = {
                    "command": tool["command"],
                    "languages": tool["languages"],
                    "description": tool["description"],
                    "available": True
                }
                logger.debug(f"Discovered code analysis tool: {tool['name']}")
        
        return tools
    
    def _is_executable_available(self, name: str) -> bool:
        """Check if an executable is available in the system PATH."""
        from shutil import which
        return which(name) is not None
    
    async def generate_code(
        self,
        language: str,
        description: str,
        template: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate code based on a description and optional template.
        
        Args:
            language: The programming language to generate code for
            description: A description of the code to generate
            template: Optional template name to use for code generation
            context: Optional context variables for the template
            
        Returns:
            Generated code and metadata
        """
        # For now, we'll use a simple template-based approach
        # In a real implementation, this would likely call an LLM API
        
        template_content = ""
        if template:
            template_path = self.templates_dir / f"{template}.{language}"
            if template_path.exists():
                with open(template_path, "r") as f:
                    template_content = f.read()
        
        # Generate code based on the description and template
        # This is a placeholder implementation
        if language == "python":
            code = self._generate_python_code(description, template_content, context)
        elif language in ["javascript", "typescript"]:
            code = self._generate_js_code(description, template_content, context)
        else:
            code = f"// Generated code for {language}\n// Based on: {description}\n\n// TODO: Implement this"
        
        return {
            "code": code,
            "language": language,
            "template": template,
            "description": description
        }
    
    def _generate_python_code(
        self, description: str, template: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate Python code based on description and template."""
        if template:
            # Use the template if provided
            # nosec B701 - autoescape disabled for code generation (would break code output)
            import jinja2
            env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False  # nosec B701 - code templates, not HTML
            )
            template = env.from_string(template)
            return template.render(**(context or {}))

        # Simple code generation based on description
        lines = [
            f"# {description}",
            "",
            "def main():",
            "    # TODO: Implement the functionality described above",
            "    pass",
            "",
            "if __name__ == \"__main__\":",
            "    main()",
            ""
        ]
        return "\n".join(lines)
    
    def _generate_js_code(
        self, description: str, template: str, context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate JavaScript/TypeScript code based on description and template."""
        if template:
            # Use the template if provided
            # nosec B701 - autoescape disabled for code generation (would break code output)
            import jinja2
            env = jinja2.Environment(
                loader=jinja2.BaseLoader(),
                trim_blocks=True,
                lstrip_blocks=True,
                autoescape=False  # nosec B701 - code templates, not HTML
            )
            template = env.from_string(template)
            return template.render(**(context or {}))

        # Simple code generation based on description
        lines = [
            f"// {description}",
            "",
            "function main() {",
            "  // TODO: Implement the functionality described above",
            "}",
            "",
            "main();",
            ""
        ]
        return "\n".join(lines)
    
    async def analyze_code(
        self,
        code: str,
        language: str,
        analysis_type: str = "lint",
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze code for quality, performance, and security issues.
        
        Args:
            code: The code to analyze
            language: The programming language of the code
            analysis_type: The type of analysis to perform (e.g., "lint", "security", "performance")
            options: Optional options for the analysis
            
        Returns:
            Analysis results
        """
        options = options or {}
        
        # Create a temporary file for the code
        import tempfile
        with tempfile.NamedTemporaryFile(
            suffix=f".{language}", mode="w", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Perform the requested analysis
            if analysis_type == "lint":
                results = await self._lint_code(temp_file_path, language, options)
            elif analysis_type == "security":
                results = await self._security_scan_code(temp_file_path, language, options)
            elif analysis_type == "performance":
                results = await self._performance_analyze_code(temp_file_path, language, options)
            else:
                results = {"error": f"Unsupported analysis type: {analysis_type}"}
            
            return results
        finally:
            # Clean up the temporary file
            os.unlink(temp_file_path)
    
    async def _lint_code(
        self, file_path: str, language: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lint code for style and quality issues."""
        results = {"issues": [], "summary": {}}
        
        if language == "python":
            # Use pylint if available
            if "pylint" in self.code_analysis_tools:
                cmd = ["pylint", "--output-format=json", file_path]
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0 and stdout:
                        # Pylint found issues
                        issues = json.loads(stdout.decode())
                        results["issues"] = issues
                        results["summary"] = {
                            "error_count": sum(1 for issue in issues if issue["type"] == "error"),
                            "warning_count": sum(1 for issue in issues if issue["type"] == "warning"),
                            "convention_count": sum(1 for issue in issues if issue["type"] == "convention"),
                            "refactor_count": sum(1 for issue in issues if issue["type"] == "refactor"),
                        }
                except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                    results["error"] = f"Error running pylint: {e}"
        
        elif language in ["javascript", "typescript"]:
            # Use eslint if available
            if "eslint" in self.code_analysis_tools:
                cmd = ["eslint", "--format=json", file_path]
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0 and stdout:
                        # ESLint found issues
                        issues = json.loads(stdout.decode())
                        results["issues"] = issues
                        results["summary"] = {
                            "error_count": sum(len(file_result["errorCount"]) for file_result in issues),
                            "warning_count": sum(len(file_result["warningCount"]) for file_result in issues),
                        }
                except (subprocess.SubprocessError, json.JSONDecodeError) as e:
                    results["error"] = f"Error running eslint: {e}"
        
        return results
    
    async def _security_scan_code(
        self, file_path: str, language: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Scan code for security vulnerabilities."""
        # This is a placeholder implementation
        # In a real implementation, this would use security scanning tools like bandit for Python
        return {
            "issues": [],
            "summary": {
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0
            },
            "message": "Security scanning not fully implemented yet"
        }
    
    async def _performance_analyze_code(
        self, file_path: str, language: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze code for performance issues."""
        # This is a placeholder implementation
        # In a real implementation, this would use performance analysis tools
        return {
            "issues": [],
            "summary": {
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "bottlenecks": []
            },
            "message": "Performance analysis not fully implemented yet"
        }
    
    async def suggest_refactoring(
        self,
        code: str,
        language: str,
        refactoring_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest refactoring opportunities for the given code.
        
        Args:
            code: The code to analyze for refactoring
            language: The programming language of the code
            refactoring_type: Optional specific type of refactoring to suggest
            
        Returns:
            Refactoring suggestions
        """
        # This is a placeholder implementation
        # In a real implementation, this would use more sophisticated analysis
        
        # Analyze the code first
        analysis_results = await self.analyze_code(code, language, "lint")
        
        # Generate refactoring suggestions based on the analysis
        suggestions = []
        
        if "issues" in analysis_results:
            for issue in analysis_results["issues"]:
                if language == "python" and issue.get("symbol") == "too-many-locals":
                    suggestions.append({
                        "type": "extract_function",
                        "description": "Extract part of this function into smaller functions to reduce the number of local variables",
                        "location": {"line": issue.get("line", 0)},
                        "priority": "medium"
                    })
                elif language == "python" and issue.get("symbol") == "duplicate-code":
                    suggestions.append({
                        "type": "extract_common_code",
                        "description": "Extract duplicated code into a shared function",
                        "location": {"line": issue.get("line", 0)},
                        "priority": "high"
                    })
        
        return {
            "suggestions": suggestions,
            "analysis": analysis_results
        }
    
    async def generate_test(
        self,
        code: str,
        language: str,
        test_framework: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate tests for the given code.
        
        Args:
            code: The code to generate tests for
            language: The programming language of the code
            test_framework: Optional test framework to use
            
        Returns:
            Generated test code
        """
        # This is a placeholder implementation
        # In a real implementation, this would use more sophisticated analysis and generation
        
        if language == "python":
            test_framework = test_framework or "pytest"
            
            if test_framework == "pytest":
                test_code = self._generate_pytest_test(code)
            elif test_framework == "unittest":
                test_code = self._generate_unittest_test(code)
            else:
                test_code = f"# Tests for the provided code using {test_framework}\n# TODO: Implement tests"
        
        elif language in ["javascript", "typescript"]:
            test_framework = test_framework or "jest"
            
            if test_framework == "jest":
                test_code = self._generate_jest_test(code)
            else:
                test_code = f"// Tests for the provided code using {test_framework}\n// TODO: Implement tests"
        
        else:
            test_code = f"# Tests for the provided {language} code\n# TODO: Implement tests"
        
        return {
            "test_code": test_code,
            "language": language,
            "test_framework": test_framework
        }
    
    def _generate_pytest_test(self, code: str) -> str:
        """Generate pytest tests for Python code."""
        # Extract function and class names from the code
        import re
        function_matches = re.finditer(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        class_matches = re.finditer(r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]", code)
        
        functions = [match.group(1) for match in function_matches]
        classes = [match.group(1) for match in class_matches]
        
        # Generate test code
        lines = [
            "# Generated pytest tests",
            "import pytest",
            "",
        ]
        
        # Import the module (assuming it's in a file)
        if functions or classes:
            lines.append("# TODO: Import the module containing the code to test")
            lines.append("# from module import *")
            lines.append("")
        
        # Generate test functions for each function
        for func_name in functions:
            if func_name.startswith("_") or func_name == "main":
                continue  # Skip private functions and main
                
            lines.extend([
                f"def test_{func_name}():",
                f"    # TODO: Test the {func_name} function",
                "    # Setup test data",
                "    # expected = ...",
                f"    # result = {func_name}(...)",
                "    # assert result == expected",
                "",
            ])
        
        # Generate test classes for each class
        for class_name in classes:
            if class_name.startswith("_"):
                continue  # Skip private classes
                
            lines.extend([
                f"class Test{class_name}:",
                "    def setup_method(self):",
                f"        # TODO: Set up a {class_name} instance for testing",
                f"        # self.instance = {class_name}(...)",
                "        pass",
                "",
                "    def test_initialization(self):",
                f"        # TODO: Test {class_name} initialization",
                "        # assert self.instance is not None",
                "        pass",
                "",
                "    # TODO: Add more test methods for class methods",
                "",
            ])
        
        return "\n".join(lines)
    
    def _generate_unittest_test(self, code: str) -> str:
        """Generate unittest tests for Python code."""
        # Similar to pytest but with unittest syntax
        import re
        function_matches = re.finditer(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        class_matches = re.finditer(r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]", code)
        
        functions = [match.group(1) for match in function_matches]
        classes = [match.group(1) for match in class_matches]
        
        # Generate test code
        lines = [
            "# Generated unittest tests",
            "import unittest",
            "",
        ]
        
        # Import the module
        if functions or classes:
            lines.append("# TODO: Import the module containing the code to test")
            lines.append("# from module import *")
            lines.append("")
        
        # Generate test class
        lines.append("class TestFunctions(unittest.TestCase):")
        
        # Generate test methods for each function
        if functions:
            for func_name in functions:
                if func_name.startswith("_") or func_name == "main":
                    continue  # Skip private functions and main
                    
                lines.extend([
                    f"    def test_{func_name}(self):",
                    f"        # TODO: Test the {func_name} function",
                    "        # Setup test data",
                    "        # expected = ...",
                    f"        # result = {func_name}(...)",
                    "        # self.assertEqual(result, expected)",
                    "        pass",
                    "",
                ])
        else:
            lines.extend([
                "    def test_placeholder(self):",
                "        # TODO: Add actual tests",
                "        pass",
                "",
            ])
        
        # Generate test classes for each class
        for class_name in classes:
            if class_name.startswith("_"):
                continue  # Skip private classes
                
            lines.extend([
                f"class Test{class_name}(unittest.TestCase):",
                "    def setUp(self):",
                f"        # TODO: Set up a {class_name} instance for testing",
                f"        # self.instance = {class_name}(...)",
                "        pass",
                "",
                "    def test_initialization(self):",
                f"        # TODO: Test {class_name} initialization",
                "        # self.assertIsNotNone(self.instance)",
                "        pass",
                "",
                "    # TODO: Add more test methods for class methods",
                "",
            ])
        
        # Add main block
        lines.extend([
            "if __name__ == '__main__':",
            "    unittest.main()",
            ""
        ])
        
        return "\n".join(lines)
    
    def _generate_jest_test(self, code: str) -> str:
        """Generate Jest tests for JavaScript/TypeScript code."""
        # Extract function and class names from the code
        import re
        function_matches = re.finditer(r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        class_matches = re.finditer(r"class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\{]", code)
        
        functions = [match.group(1) for match in function_matches]
        classes = [match.group(1) for match in class_matches]
        
        # Generate test code
        lines = [
            "// Generated Jest tests",
            "",
        ]
        
        # Import the module
        if functions or classes:
            lines.append("// TODO: Import the module containing the code to test")
            lines.append("// import { ... } from './module';")
            lines.append("")
        
        # Generate test suite
        lines.append("describe('Code Tests', () => {")
        
        # Generate test cases for each function
        for func_name in functions:
            if func_name.startswith("_"):
                continue  # Skip private functions
                
            lines.extend([
                f"  describe('{func_name}', () => {{",
                f"    test('should work correctly', () => {{",
                "      // TODO: Setup test data",
                "      // const expected = ...;",
                f"      // const result = {func_name}(...);",
                "      // expect(result).toEqual(expected);",
                "    });",
                "  });",
                "",
            ])
        
        # Generate test cases for each class
        for class_name in classes:
            if class_name.startswith("_"):
                continue  # Skip private classes
                
            lines.extend([
                f"  describe('{class_name}', () => {{",
                "    let instance;",
                "",
                "    beforeEach(() => {",
                f"      // TODO: Set up a {class_name} instance for testing",
                f"      // instance = new {class_name}(...);",
                "    });",
                "",
                "    test('should initialize correctly', () => {",
                "      // TODO: Test initialization",
                "      // expect(instance).toBeDefined();",
                "    });",
                "",
                "    // TODO: Add more test cases for class methods",
                "  });",
                "",
            ])
        
        lines.append("});")
        lines.append("")
        
        return "\n".join(lines)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for development assistance."""
        return [
            {
                "name": "generate_code",
                "description": "Generate code based on a description",
                "parameters": [
                    {
                        "name": "language",
                        "description": "The programming language to generate code for",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "A description of the code to generate",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "template",
                        "description": "Optional template name to use for code generation",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_generate_code,
            },
            {
                "name": "analyze_code",
                "description": "Analyze code for quality, performance, and security issues",
                "parameters": [
                    {
                        "name": "code",
                        "description": "The code to analyze",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "language",
                        "description": "The programming language of the code",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "analysis_type",
                        "description": "The type of analysis to perform (e.g., 'lint', 'security', 'performance')",
                        "type": "string",
                        "required": False,
                        "default": "lint",
                    }
                ],
                "handler": self.tool_analyze_code,
            },
            {
                "name": "generate_test",
                "description": "Generate tests for the given code",
                "parameters": [
                    {
                        "name": "code",
                        "description": "The code to generate tests for",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "language",
                        "description": "The programming language of the code",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "test_framework",
                        "description": "Optional test framework to use",
                        "type": "string",
                        "required": False,
                    }
                ],
                "handler": self.tool_generate_test,
            },
        ]
    
    async def tool_generate_code(
        self, language: str, description: str, template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for generating code."""
        result = await self.generate_code(language, description, template)
        return {"code": result["code"]}
    
    async def tool_analyze_code(
        self, code: str, language: str, analysis_type: str = "lint"
    ) -> Dict[str, Any]:
        """Tool handler for analyzing code."""
        result = await self.analyze_code(code, language, analysis_type)
        return result
    
    async def tool_generate_test(
        self, code: str, language: str, test_framework: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tool handler for generating tests."""
        result = await self.generate_test(code, language, test_framework)
        return {"test_code": result["test_code"]}
