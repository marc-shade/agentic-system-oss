"""
Report Generator for Skill Evaluation

Generates comprehensive evaluation reports in multiple formats.
Following Kai pattern: clear, actionable reporting.
"""

from typing import Dict, List, Any, Optional, Union, TextIO
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import json
import statistics

from .test_cases import TestResult, TestStatus, TestSuite
from .metrics import MetricType, EvalMetrics, calculate_latency_stats
from .benchmarks import BenchmarkResult, BenchmarkSuite, ComparisonResult


class ReportFormat(Enum):
    """Output formats for reports."""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class ReportSection(Enum):
    """Sections of an evaluation report."""
    SUMMARY = "summary"
    TEST_RESULTS = "test_results"
    BENCHMARK_RESULTS = "benchmark_results"
    METRICS = "metrics"
    SKILL_BREAKDOWN = "skill_breakdown"
    RECOMMENDATIONS = "recommendations"
    RAW_DATA = "raw_data"


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    format: ReportFormat = ReportFormat.MARKDOWN
    include_sections: List[ReportSection] = field(default_factory=lambda: list(ReportSection))
    include_raw_data: bool = False
    include_timestamps: bool = True
    max_failures_shown: int = 10
    max_recommendations: int = 5
    title: str = "Skill Evaluation Report"
    author: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """
    A complete evaluation report.

    Contains all results, metrics, and analysis from an evaluation run.
    """
    title: str
    test_results: List[TestResult] = field(default_factory=list)
    benchmark_results: List[BenchmarkResult] = field(default_factory=list)
    metrics: Optional[EvalMetrics] = None
    generated_at: datetime = field(default_factory=datetime.now)
    config: ReportConfig = field(default_factory=ReportConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.test_results)

    @property
    def passed_tests(self) -> int:
        """Number of passed tests."""
        return sum(1 for r in self.test_results if r.passed)

    @property
    def failed_tests(self) -> int:
        """Number of failed tests."""
        return sum(1 for r in self.test_results if not r.passed)

    @property
    def test_pass_rate(self) -> float:
        """Test pass rate (0.0 to 1.0)."""
        if not self.test_results:
            return 0.0
        return self.passed_tests / self.total_tests

    @property
    def total_benchmarks(self) -> int:
        """Total number of benchmarks."""
        return len(self.benchmark_results)

    @property
    def passed_benchmarks(self) -> int:
        """Number of passed benchmarks."""
        return sum(1 for r in self.benchmark_results if r.passed)

    @property
    def benchmark_pass_rate(self) -> float:
        """Benchmark pass rate (0.0 to 1.0)."""
        if not self.benchmark_results:
            return 0.0
        return self.passed_benchmarks / self.total_benchmarks

    @property
    def overall_status(self) -> str:
        """Overall evaluation status."""
        if not self.test_results and not self.benchmark_results:
            return "NO_DATA"

        critical_benchmarks = sum(
            1 for r in self.benchmark_results
            if r.comparison == ComparisonResult.CRITICAL
        )

        if critical_benchmarks > 0:
            return "CRITICAL"

        if self.test_pass_rate >= 1.0 and self.benchmark_pass_rate >= 1.0:
            return "PASSED"
        elif self.test_pass_rate >= 0.8 and self.benchmark_pass_rate >= 0.8:
            return "ACCEPTABLE"
        else:
            return "FAILED"

    def get_skills_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary by skill."""
        by_skill: Dict[str, List[TestResult]] = {}

        for result in self.test_results:
            skill = result.test_case.skill
            if skill not in by_skill:
                by_skill[skill] = []
            by_skill[skill].append(result)

        summary = {}
        for skill, results in by_skill.items():
            passed = sum(1 for r in results if r.passed)
            total = len(results)
            avg_score = statistics.mean(r.score for r in results)
            avg_time = statistics.mean(r.execution_time_ms for r in results)

            summary[skill] = {
                "passed": passed,
                "total": total,
                "pass_rate": passed / total if total > 0 else 0,
                "average_score": avg_score,
                "average_time_ms": avg_time,
            }

        return summary

    def get_failures(self, limit: Optional[int] = None) -> List[TestResult]:
        """Get failed tests."""
        failures = [r for r in self.test_results if not r.passed]
        if limit:
            return failures[:limit]
        return failures

    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        # Check for skill-specific issues
        skills_summary = self.get_skills_summary()
        for skill, data in skills_summary.items():
            if data["pass_rate"] < 0.7:
                recommendations.append(
                    f"Review and improve '{skill}' capability "
                    f"(pass rate: {data['pass_rate']:.0%})"
                )
            if data["average_time_ms"] > 5000:
                recommendations.append(
                    f"Optimize '{skill}' performance "
                    f"(avg time: {data['average_time_ms']:.0f}ms)"
                )

        # Check benchmark results
        for result in self.benchmark_results:
            if result.comparison == ComparisonResult.CRITICAL:
                recommendations.append(
                    f"CRITICAL: Address '{result.benchmark_name}' immediately "
                    f"(deviation: {result.deviation:.1f}%)"
                )
            elif result.comparison == ComparisonResult.BELOW:
                recommendations.append(
                    f"Improve '{result.benchmark_name}' to meet baseline "
                    f"(currently {result.deviation:.1f}% off target)"
                )

        # Check for error patterns
        error_tests = [r for r in self.test_results if r.status == TestStatus.ERROR]
        if len(error_tests) > 0:
            recommendations.append(
                f"Investigate {len(error_tests)} test(s) with errors"
            )

        timeout_tests = [r for r in self.test_results if r.status == TestStatus.TIMEOUT]
        if len(timeout_tests) > 0:
            recommendations.append(
                f"Review {len(timeout_tests)} test(s) with timeouts"
            )

        return recommendations

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "overall_status": self.overall_status,
            "test_summary": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "pass_rate": self.test_pass_rate,
            },
            "benchmark_summary": {
                "total": self.total_benchmarks,
                "passed": self.passed_benchmarks,
                "pass_rate": self.benchmark_pass_rate,
            },
            "skills_summary": self.get_skills_summary(),
            "recommendations": self.get_recommendations(),
            "test_results": [r.to_dict() for r in self.test_results],
            "benchmark_results": [r.to_dict() for r in self.benchmark_results],
            "metadata": self.metadata,
        }


class ReportGenerator:
    """
    Generates evaluation reports in various formats.

    Supports TEXT, MARKDOWN, JSON, and HTML output.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        self.config = config or ReportConfig()

    def generate(
        self,
        report: EvaluationReport,
        format_override: Optional[ReportFormat] = None
    ) -> str:
        """
        Generate report in specified format.

        Args:
            report: EvaluationReport to generate
            format_override: Override config format

        Returns:
            Formatted report string
        """
        fmt = format_override or self.config.format

        if fmt == ReportFormat.TEXT:
            return self._generate_text(report)
        elif fmt == ReportFormat.MARKDOWN:
            return self._generate_markdown(report)
        elif fmt == ReportFormat.JSON:
            return self._generate_json(report)
        elif fmt == ReportFormat.HTML:
            return self._generate_html(report)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def save(
        self,
        report: EvaluationReport,
        path: Union[str, Path],
        format_override: Optional[ReportFormat] = None
    ) -> Path:
        """
        Save report to file.

        Args:
            report: EvaluationReport to save
            path: Output file path
            format_override: Override config format

        Returns:
            Path where report was saved
        """
        path = Path(path)
        content = self.generate(report, format_override)

        with open(path, 'w') as f:
            f.write(content)

        return path

    def _generate_text(self, report: EvaluationReport) -> str:
        """Generate plain text report."""
        lines = []

        # Header
        lines.append("=" * 60)
        lines.append(report.title.upper())
        lines.append("=" * 60)
        lines.append("")

        if self.config.include_timestamps:
            lines.append(f"Generated: {report.generated_at.isoformat()}")
            lines.append("")

        # Summary
        if ReportSection.SUMMARY in self.config.include_sections:
            lines.append("SUMMARY")
            lines.append("-" * 40)
            lines.append(f"Overall Status: {report.overall_status}")
            lines.append("")
            lines.append(f"Tests: {report.passed_tests}/{report.total_tests} passed "
                        f"({report.test_pass_rate:.0%})")
            lines.append(f"Benchmarks: {report.passed_benchmarks}/{report.total_benchmarks} passed "
                        f"({report.benchmark_pass_rate:.0%})")
            lines.append("")

        # Skill Breakdown
        if ReportSection.SKILL_BREAKDOWN in self.config.include_sections:
            skills = report.get_skills_summary()
            if skills:
                lines.append("SKILL BREAKDOWN")
                lines.append("-" * 40)
                for skill, data in skills.items():
                    lines.append(f"  {skill}:")
                    lines.append(f"    Pass rate: {data['pass_rate']:.0%}")
                    lines.append(f"    Avg score: {data['average_score']:.2f}")
                    lines.append(f"    Avg time: {data['average_time_ms']:.0f}ms")
                lines.append("")

        # Test Results
        if ReportSection.TEST_RESULTS in self.config.include_sections:
            failures = report.get_failures(self.config.max_failures_shown)
            if failures:
                lines.append("FAILED TESTS")
                lines.append("-" * 40)
                for result in failures:
                    lines.append(f"  [{result.status.value}] {result.test_case.name}")
                    lines.append(f"    Skill: {result.test_case.skill}")
                    if result.error:
                        lines.append(f"    Error: {result.error}")
                    if result.failed_criteria:
                        lines.append(f"    Failed: {', '.join(result.failed_criteria)}")
                lines.append("")

        # Benchmark Results
        if ReportSection.BENCHMARK_RESULTS in self.config.include_sections:
            if report.benchmark_results:
                lines.append("BENCHMARK RESULTS")
                lines.append("-" * 40)
                for result in report.benchmark_results:
                    status = "PASS" if result.passed else "FAIL"
                    lines.append(f"  [{status}] {result.benchmark_name}")
                    lines.append(f"    Actual: {result.actual_value:.2f} "
                               f"(target: {result.baseline.target_value:.2f})")
                    lines.append(f"    Deviation: {result.deviation:+.1f}%")
                lines.append("")

        # Recommendations
        if ReportSection.RECOMMENDATIONS in self.config.include_sections:
            recommendations = report.get_recommendations()[:self.config.max_recommendations]
            if recommendations:
                lines.append("RECOMMENDATIONS")
                lines.append("-" * 40)
                for i, rec in enumerate(recommendations, 1):
                    lines.append(f"  {i}. {rec}")
                lines.append("")

        return "\n".join(lines)

    def _generate_markdown(self, report: EvaluationReport) -> str:
        """Generate Markdown report."""
        lines = []

        # Header
        lines.append(f"# {report.title}")
        lines.append("")

        if self.config.include_timestamps:
            lines.append(f"*Generated: {report.generated_at.isoformat()}*")
            lines.append("")

        # Summary
        if ReportSection.SUMMARY in self.config.include_sections:
            lines.append("## Summary")
            lines.append("")
            status_emoji = {
                "PASSED": "✅",
                "ACCEPTABLE": "⚠️",
                "FAILED": "❌",
                "CRITICAL": "🚨",
                "NO_DATA": "❓",
            }
            lines.append(f"**Overall Status:** {status_emoji.get(report.overall_status, '❓')} {report.overall_status}")
            lines.append("")
            lines.append("| Metric | Result |")
            lines.append("|--------|--------|")
            lines.append(f"| Tests Passed | {report.passed_tests}/{report.total_tests} ({report.test_pass_rate:.0%}) |")
            lines.append(f"| Benchmarks Passed | {report.passed_benchmarks}/{report.total_benchmarks} ({report.benchmark_pass_rate:.0%}) |")
            lines.append("")

        # Skill Breakdown
        if ReportSection.SKILL_BREAKDOWN in self.config.include_sections:
            skills = report.get_skills_summary()
            if skills:
                lines.append("## Skill Breakdown")
                lines.append("")
                lines.append("| Skill | Pass Rate | Avg Score | Avg Time |")
                lines.append("|-------|-----------|-----------|----------|")
                for skill, data in skills.items():
                    lines.append(f"| {skill} | {data['pass_rate']:.0%} | "
                               f"{data['average_score']:.2f} | {data['average_time_ms']:.0f}ms |")
                lines.append("")

        # Test Results
        if ReportSection.TEST_RESULTS in self.config.include_sections:
            failures = report.get_failures(self.config.max_failures_shown)
            if failures:
                lines.append("## Failed Tests")
                lines.append("")
                for result in failures:
                    lines.append(f"### {result.test_case.name}")
                    lines.append("")
                    lines.append(f"- **Status:** {result.status.value}")
                    lines.append(f"- **Skill:** {result.test_case.skill}")
                    if result.error:
                        lines.append(f"- **Error:** `{result.error}`")
                    if result.failed_criteria:
                        lines.append(f"- **Failed Criteria:** {', '.join(result.failed_criteria)}")
                    lines.append("")

        # Benchmark Results
        if ReportSection.BENCHMARK_RESULTS in self.config.include_sections:
            if report.benchmark_results:
                lines.append("## Benchmark Results")
                lines.append("")
                lines.append("| Benchmark | Status | Actual | Target | Deviation |")
                lines.append("|-----------|--------|--------|--------|-----------|")
                for result in report.benchmark_results:
                    status = "✅" if result.passed else "❌"
                    lines.append(f"| {result.benchmark_name} | {status} | "
                               f"{result.actual_value:.2f} | {result.baseline.target_value:.2f} | "
                               f"{result.deviation:+.1f}% |")
                lines.append("")

        # Recommendations
        if ReportSection.RECOMMENDATIONS in self.config.include_sections:
            recommendations = report.get_recommendations()[:self.config.max_recommendations]
            if recommendations:
                lines.append("## Recommendations")
                lines.append("")
                for rec in recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        # Raw Data
        if self.config.include_raw_data and ReportSection.RAW_DATA in self.config.include_sections:
            lines.append("## Raw Data")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(report.to_dict(), indent=2, default=str))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _generate_json(self, report: EvaluationReport) -> str:
        """Generate JSON report."""
        return json.dumps(report.to_dict(), indent=2, default=str)

    def _generate_html(self, report: EvaluationReport) -> str:
        """Generate HTML report."""
        status_colors = {
            "PASSED": "#28a745",
            "ACCEPTABLE": "#ffc107",
            "FAILED": "#dc3545",
            "CRITICAL": "#dc3545",
            "NO_DATA": "#6c757d",
        }

        skills = report.get_skills_summary()
        recommendations = report.get_recommendations()[:self.config.max_recommendations]

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report.title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .status {{ display: inline-block; padding: 8px 16px; border-radius: 4px; color: white; font-weight: bold; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card .value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .summary-card .label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f8f9fa; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
        .recommendations {{ background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; }}
        .recommendations li {{ margin: 10px 0; }}
        .timestamp {{ color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report.title}</h1>
        <p class="timestamp">Generated: {report.generated_at.isoformat()}</p>

        <h2>Summary</h2>
        <p>
            <span class="status" style="background: {status_colors.get(report.overall_status, '#6c757d')}">
                {report.overall_status}
            </span>
        </p>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="value">{report.passed_tests}/{report.total_tests}</div>
                <div class="label">Tests Passed ({report.test_pass_rate:.0%})</div>
            </div>
            <div class="summary-card">
                <div class="value">{report.passed_benchmarks}/{report.total_benchmarks}</div>
                <div class="label">Benchmarks Passed ({report.benchmark_pass_rate:.0%})</div>
            </div>
        </div>
"""

        if skills:
            html += """
        <h2>Skill Breakdown</h2>
        <table>
            <tr>
                <th>Skill</th>
                <th>Pass Rate</th>
                <th>Avg Score</th>
                <th>Avg Time</th>
            </tr>
"""
            for skill, data in skills.items():
                html += f"""
            <tr>
                <td>{skill}</td>
                <td>{data['pass_rate']:.0%}</td>
                <td>{data['average_score']:.2f}</td>
                <td>{data['average_time_ms']:.0f}ms</td>
            </tr>
"""
            html += "        </table>\n"

        if report.benchmark_results:
            html += """
        <h2>Benchmark Results</h2>
        <table>
            <tr>
                <th>Benchmark</th>
                <th>Status</th>
                <th>Actual</th>
                <th>Target</th>
                <th>Deviation</th>
            </tr>
"""
            for result in report.benchmark_results:
                status_class = "pass" if result.passed else "fail"
                status_text = "✓" if result.passed else "✗"
                html += f"""
            <tr>
                <td>{result.benchmark_name}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{result.actual_value:.2f}</td>
                <td>{result.baseline.target_value:.2f}</td>
                <td>{result.deviation:+.1f}%</td>
            </tr>
"""
            html += "        </table>\n"

        if recommendations:
            html += """
        <h2>Recommendations</h2>
        <div class="recommendations">
            <ul>
"""
            for rec in recommendations:
                html += f"                <li>{rec}</li>\n"
            html += """
            </ul>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""
        return html


if __name__ == '__main__':
    from .test_cases import TestCase, TestInput, SuccessCriterion, ExpectedBehavior
    from .benchmarks import Benchmark, create_accuracy_baseline

    print("Report Generator Module Self-Test")
    print("=" * 50)

    # Create sample test results
    test_case1 = TestCase(
        name="Read Python File",
        skill="file_reading",
        description="Test reading Python files",
        input=TestInput(data={"path": "test.py"}),
        success_criteria=[
            SuccessCriterion(
                name="content_valid",
                behavior_type=ExpectedBehavior.RETURNS_VALUE
            )
        ],
    )

    test_case2 = TestCase(
        name="Write Config",
        skill="file_writing",
        description="Test writing config files",
        input=TestInput(data={"path": "config.json"}),
        success_criteria=[
            SuccessCriterion(
                name="write_success",
                behavior_type=ExpectedBehavior.NO_ERRORS
            )
        ],
    )

    test_results = [
        TestResult(
            test_case=test_case1,
            status=TestStatus.PASSED,
            passed_criteria=["content_valid"],
            failed_criteria=[],
            execution_time_ms=150,
        ),
        TestResult(
            test_case=test_case2,
            status=TestStatus.FAILED,
            passed_criteria=[],
            failed_criteria=["write_success"],
            execution_time_ms=200,
            error="Permission denied",
        ),
    ]

    # Create sample benchmark results
    baseline = create_accuracy_baseline("accuracy", target=0.90)
    benchmark = Benchmark(
        name="skill_accuracy",
        description="Overall skill accuracy",
        baseline=baseline,
    )
    benchmark_result = benchmark.run(value=0.92)

    # Create report
    report = EvaluationReport(
        title="Agent Skill Evaluation",
        test_results=test_results,
        benchmark_results=[benchmark_result],
    )

    print(f"Report created: {report.title}")
    print(f"Overall status: {report.overall_status}")
    print(f"Test pass rate: {report.test_pass_rate:.0%}")
    print(f"Benchmark pass rate: {report.benchmark_pass_rate:.0%}")

    # Generate reports in different formats
    generator = ReportGenerator(ReportConfig(
        include_sections=list(ReportSection),
    ))

    # Text format
    text_report = generator.generate(report, ReportFormat.TEXT)
    print("\n--- TEXT FORMAT ---")
    print(text_report[:500] + "...")

    # Markdown format
    md_report = generator.generate(report, ReportFormat.MARKDOWN)
    print("\n--- MARKDOWN FORMAT ---")
    print(md_report[:500] + "...")

    # JSON format
    json_report = generator.generate(report, ReportFormat.JSON)
    print("\n--- JSON FORMAT ---")
    print(json_report[:500] + "...")

    # HTML format
    html_report = generator.generate(report, ReportFormat.HTML)
    print("\n--- HTML FORMAT ---")
    print(f"HTML report generated ({len(html_report)} characters)")

    # Verify JSON is valid
    parsed = json.loads(json_report)
    assert parsed["overall_status"] == "ACCEPTABLE"
    print("\nJSON validation passed")

    print("\nAll report generator tests passed!")
