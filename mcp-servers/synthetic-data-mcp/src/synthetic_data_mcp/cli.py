"""
Command-line interface for the Synthetic Data Platform MCP.

This module provides a comprehensive CLI for managing synthetic data generation,
compliance validation, and system administration.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .server import app as mcp_app
from .core.generator import SyntheticDataGenerator
from .compliance.validator import ComplianceValidator
from .privacy.engine import PrivacyEngine
from .validation.statistical import StatisticalValidator
from .utils.audit import AuditTrail
from .schemas.base import DataDomain, PrivacyLevel, ComplianceFramework

# Initialize Typer app
app = typer.Typer(
    name="synthetic-data-mcp",
    help="Synthetic Data Platform MCP - Generate compliant synthetic datasets",
    rich_markup_mode="rich"
)
console = Console()


@app.command()
def serve(
    port: int = typer.Option(3000, help="Port to run MCP server on"),
    host: str = typer.Option("127.0.0.1", help="Host to bind server to"),
    log_level: str = typer.Option("INFO", help="Logging level"),
    config_file: Optional[Path] = typer.Option(None, help="Configuration file path")
):
    """
    Start the MCP server for synthetic data generation.
    """
    rprint(f"[bold green]Starting Synthetic Data MCP Server[/bold green]")
    rprint(f"Server will be available at: [bold blue]http://{host}:{port}[/bold blue]")
    
    # Configure logging
    import logging
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    
    # Start server
    try:
        mcp_app.run(host=host, port=port)
    except KeyboardInterrupt:
        rprint("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        rprint(f"[red]Server error: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    domain: DataDomain = typer.Argument(..., help="Data domain (healthcare, finance, custom)"),
    dataset_type: str = typer.Argument(..., help="Dataset type to generate"),
    count: int = typer.Option(1000, help="Number of records to generate"),
    privacy_level: PrivacyLevel = typer.Option(PrivacyLevel.MEDIUM, help="Privacy protection level"),
    output_file: Optional[Path] = typer.Option(None, help="Output file path"),
    format: str = typer.Option("json", help="Output format (json, csv)"),
    compliance: Optional[str] = typer.Option(None, help="Comma-separated compliance frameworks"),
    seed: Optional[int] = typer.Option(None, help="Random seed for reproducibility")
):
    """
    Generate synthetic dataset with specified parameters.
    """
    async def _generate():
        generator = SyntheticDataGenerator()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Generate data
            task = progress.add_task(f"Generating {count} {dataset_type} records...", total=None)
            
            try:
                dataset = await generator.generate_dataset(
                    domain=domain,
                    dataset_type=dataset_type,
                    record_count=count,
                    privacy_level=privacy_level,
                    seed=seed
                )
                
                progress.update(task, description="[green]Generation completed![/green]")
                
                # Validate compliance if requested
                if compliance:
                    frameworks = [ComplianceFramework(f.strip()) for f in compliance.split(",")]
                    validator = ComplianceValidator()
                    
                    progress.update(task, description="Validating compliance...")
                    
                    compliance_results = await validator.validate_dataset(
                        dataset=dataset,
                        frameworks=frameworks,
                        domain=domain
                    )
                    
                    # Show compliance results
                    table = Table(title="Compliance Validation Results")
                    table.add_column("Framework", style="cyan")
                    table.add_column("Status", style="green")
                    table.add_column("Risk Score", style="yellow")
                    table.add_column("Violations", style="red")
                    
                    for framework, result in compliance_results.items():
                        status = "✅ PASSED" if result.passed else "❌ FAILED"
                        table.add_row(
                            str(framework),
                            status,
                            f"{result.risk_score:.4f}",
                            str(len(result.violations))
                        )
                    
                    console.print(table)
                
                # Save output
                if output_file:
                    output_path = Path(output_file)
                    
                    if format == "json":
                        with open(output_path, 'w') as f:
                            json.dump(dataset, f, indent=2, default=str)
                    elif format == "csv":
                        import pandas as pd
                        df = pd.DataFrame(dataset)
                        df.to_csv(output_path, index=False)
                    else:
                        rprint(f"[red]Unsupported format: {format}[/red]")
                        raise typer.Exit(1)
                    
                    rprint(f"[green]Dataset saved to: {output_path}[/green]")
                else:
                    # Print sample records
                    rprint(f"[bold]Generated {len(dataset)} records[/bold]")
                    rprint("\n[bold]Sample records:[/bold]")
                    
                    for i, record in enumerate(dataset[:3]):
                        rprint(f"[dim]Record {i+1}:[/dim]")
                        rprint(json.dumps(record, indent=2, default=str))
                        if i < 2:
                            rprint()
                
            except Exception as e:
                progress.update(task, description=f"[red]Error: {str(e)}[/red]")
                rprint(f"[red]Generation failed: {str(e)}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_generate())


@app.command()
def validate(
    input_file: Path = typer.Argument(..., help="Input dataset file"),
    compliance_frameworks: str = typer.Option("hipaa,gdpr", help="Comma-separated compliance frameworks"),
    domain: DataDomain = typer.Option(DataDomain.HEALTHCARE, help="Data domain for validation"),
    output_report: Optional[Path] = typer.Option(None, help="Output validation report file"),
    risk_threshold: float = typer.Option(0.01, help="Acceptable risk threshold")
):
    """
    Validate dataset compliance against regulatory frameworks.
    """
    async def _validate():
        if not input_file.exists():
            rprint(f"[red]Input file not found: {input_file}[/red]")
            raise typer.Exit(1)
        
        # Load dataset
        try:
            with open(input_file, 'r') as f:
                dataset = json.load(f)
        except json.JSONDecodeError:
            rprint(f"[red]Invalid JSON file: {input_file}[/red]")
            raise typer.Exit(1)
        
        frameworks = [ComplianceFramework(f.strip()) for f in compliance_frameworks.split(",")]
        validator = ComplianceValidator()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task(f"Validating compliance for {len(frameworks)} frameworks...", total=None)
            
            try:
                results = await validator.validate_dataset(
                    dataset=dataset,
                    frameworks=frameworks,
                    domain=domain,
                    risk_threshold=risk_threshold
                )
                
                progress.update(task, description="[green]Validation completed![/green]")
                
                # Display results
                table = Table(title="Compliance Validation Results")
                table.add_column("Framework", style="cyan")
                table.add_column("Status", style="bold")
                table.add_column("Score", style="yellow")
                table.add_column("Risk Score", style="red")
                table.add_column("Violations", style="red")
                table.add_column("Cert Ready", style="green")
                
                for framework, result in results.items():
                    status = "[green]✅ PASSED[/green]" if result.passed else "[red]❌ FAILED[/red]"
                    cert_status = "✅" if result.certification_ready else "❌"
                    
                    table.add_row(
                        str(framework),
                        status,
                        f"{result.score:.3f}",
                        f"{result.risk_score:.4f}",
                        str(len(result.violations)),
                        cert_status
                    )
                
                console.print(table)
                
                # Show recommendations
                all_recommendations = []
                for result in results.values():
                    all_recommendations.extend(result.recommendations)
                
                if all_recommendations:
                    rprint("\n[bold yellow]Recommendations:[/bold yellow]")
                    for rec in set(all_recommendations):
                        rprint(f"• {rec}")
                
                # Save report
                if output_report:
                    report_data = {
                        "validation_timestamp": datetime.now().isoformat(),
                        "input_file": str(input_file),
                        "frameworks_tested": [str(f) for f in frameworks],
                        "results": {str(k): v.dict() for k, v in results.items()},
                        "summary": {
                            "total_frameworks": len(frameworks),
                            "passed_frameworks": sum(1 for r in results.values() if r.passed),
                            "overall_compliant": all(r.passed for r in results.values()),
                            "max_risk_score": max(r.risk_score for r in results.values()),
                            "certification_ready": all(r.certification_ready for r in results.values())
                        }
                    }
                    
                    with open(output_report, 'w') as f:
                        json.dump(report_data, f, indent=2, default=str)
                    
                    rprint(f"\n[green]Validation report saved: {output_report}[/green]")
                
            except Exception as e:
                progress.update(task, description=f"[red]Validation failed: {str(e)}[/red]")
                rprint(f"[red]Validation error: {str(e)}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_validate())


@app.command()
def analyze_privacy(
    input_file: Path = typer.Argument(..., help="Input dataset file"),
    auxiliary_file: Optional[Path] = typer.Option(None, help="Auxiliary data file for linkage analysis"),
    output_report: Optional[Path] = typer.Option(None, help="Privacy analysis report file")
):
    """
    Analyze privacy risks in a dataset.
    """
    async def _analyze():
        if not input_file.exists():
            rprint(f"[red]Input file not found: {input_file}[/red]")
            raise typer.Exit(1)
        
        # Load dataset
        with open(input_file, 'r') as f:
            dataset = json.load(f)
        
        auxiliary_data = None
        if auxiliary_file and auxiliary_file.exists():
            with open(auxiliary_file, 'r') as f:
                auxiliary_data = json.load(f)
        
        privacy_engine = PrivacyEngine()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Analyzing privacy risks...", total=None)
            
            try:
                analysis = await privacy_engine.analyze_privacy_risk(
                    dataset=dataset,
                    auxiliary_data=auxiliary_data,
                    attack_scenarios=["linkage", "inference", "membership"]
                )
                
                progress.update(task, description="[green]Privacy analysis completed![/green]")
                
                # Display results
                rprint(f"\n[bold]Privacy Risk Analysis Results[/bold]")
                rprint(f"Overall Risk Score: [red]{analysis['overall_risk']:.4f}[/red]")
                
                # Risk level assessment
                risk_level = "LOW" if analysis['overall_risk'] < 0.1 else "MEDIUM" if analysis['overall_risk'] < 0.3 else "HIGH"
                risk_color = "green" if risk_level == "LOW" else "yellow" if risk_level == "MEDIUM" else "red"
                rprint(f"Risk Level: [{risk_color}]{risk_level}[/{risk_color}]")
                
                # Attack scenario results
                if "attack_results" in analysis:
                    table = Table(title="Attack Scenario Results")
                    table.add_column("Attack Type", style="cyan")
                    table.add_column("Risk Score", style="red")
                    table.add_column("Details")
                    
                    for attack_type, result in analysis["attack_results"].items():
                        risk_score = result.get("overall_risk", result.get("risk_score", 0.0))
                        details = f"Unique records: {result.get('unique_records', 'N/A')}"
                        
                        table.add_row(
                            attack_type.replace("_", " ").title(),
                            f"{risk_score:.4f}",
                            details
                        )
                    
                    console.print(table)
                
                # Recommendations
                if analysis.get("recommendations"):
                    rprint("\n[bold yellow]Privacy Recommendations:[/bold yellow]")
                    for rec in analysis["recommendations"]:
                        rprint(f"• {rec}")
                
                # Differential privacy recommendations
                if "dp_recommendations" in analysis:
                    dp_recs = analysis["dp_recommendations"]
                    rprint(f"\n[bold]Differential Privacy Recommendations:[/bold]")
                    rprint(f"Suggested ε (epsilon): [yellow]{dp_recs.get('suggested_epsilon', 'N/A')}[/yellow]")
                
                # Save report
                if output_report:
                    report_data = {
                        "analysis_timestamp": datetime.now().isoformat(),
                        "input_file": str(input_file),
                        "auxiliary_file": str(auxiliary_file) if auxiliary_file else None,
                        "analysis_results": analysis
                    }
                    
                    with open(output_report, 'w') as f:
                        json.dump(report_data, f, indent=2, default=str)
                    
                    rprint(f"\n[green]Privacy analysis report saved: {output_report}[/green]")
                
            except Exception as e:
                progress.update(task, description=f"[red]Analysis failed: {str(e)}[/red]")
                rprint(f"[red]Privacy analysis error: {str(e)}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_analyze())


@app.command()
def benchmark(
    synthetic_file: Path = typer.Argument(..., help="Synthetic dataset file"),
    real_file: Path = typer.Argument(..., help="Real dataset file for comparison"),
    tasks: str = typer.Option("classification,regression", help="ML tasks to benchmark"),
    output_report: Optional[Path] = typer.Option(None, help="Benchmark report file")
):
    """
    Benchmark synthetic data utility against real data.
    """
    async def _benchmark():
        if not synthetic_file.exists():
            rprint(f"[red]Synthetic dataset file not found: {synthetic_file}[/red]")
            raise typer.Exit(1)
        
        if not real_file.exists():
            rprint(f"[red]Real dataset file not found: {real_file}[/red]")
            raise typer.Exit(1)
        
        # Load datasets
        with open(synthetic_file, 'r') as f:
            synthetic_data = json.load(f)
        
        with open(real_file, 'r') as f:
            real_data = json.load(f)
        
        task_list = [t.strip() for t in tasks.split(",")]
        validator = StatisticalValidator()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task_id = progress.add_task("Benchmarking utility preservation...", total=None)
            
            try:
                # Statistical comparison
                comparison = await validator.compare_datasets(synthetic_data, real_data)
                
                # Utility benchmarking
                utility_results = await validator.benchmark_utility(
                    synthetic_data=synthetic_data,
                    real_data=real_data,
                    tasks=task_list
                )
                
                progress.update(task_id, description="[green]Benchmarking completed![/green]")
                
                # Display results
                rprint(f"\n[bold]Dataset Comparison Results[/bold]")
                rprint(f"Overall Similarity: [yellow]{comparison.get('overall_similarity', 0.0):.4f}[/yellow]")
                rprint(f"Common Columns: {len(comparison.get('common_columns', []))}")
                
                # Utility benchmarking results
                if "overall_utility" in utility_results:
                    rprint(f"\n[bold]Utility Preservation Results[/bold]")
                    rprint(f"Overall Utility Score: [yellow]{utility_results['overall_utility']:.4f}[/yellow]")
                    
                    # Task-specific results
                    if "tasks" in utility_results:
                        table = Table(title="Task-Specific Results")
                        table.add_column("Task", style="cyan")
                        table.add_column("Real Performance", style="green")
                        table.add_column("Synthetic Performance", style="yellow")
                        table.add_column("Utility Ratio", style="red")
                        table.add_column("Preserved", style="bold")
                        
                        for task_name, task_result in utility_results["tasks"].items():
                            if "error" not in task_result:
                                real_perf = task_result.get("real_accuracy", task_result.get("real_r2", 0.0))
                                synth_perf = task_result.get("synthetic_accuracy", task_result.get("synthetic_r2", 0.0))
                                utility_ratio = task_result.get("utility_ratio", 0.0)
                                preserved = "✅" if task_result.get("utility_preserved", False) else "❌"
                                
                                table.add_row(
                                    task_name.title(),
                                    f"{real_perf:.3f}",
                                    f"{synth_perf:.3f}",
                                    f"{utility_ratio:.3f}",
                                    preserved
                                )
                        
                        console.print(table)
                
                # Recommendations
                all_recommendations = []
                all_recommendations.extend(comparison.get("recommendations", []))
                all_recommendations.extend(utility_results.get("recommendations", []))
                
                if all_recommendations:
                    rprint("\n[bold yellow]Recommendations:[/bold yellow]")
                    for rec in set(all_recommendations):
                        rprint(f"• {rec}")
                
                # Save report
                if output_report:
                    report_data = {
                        "benchmark_timestamp": datetime.now().isoformat(),
                        "synthetic_file": str(synthetic_file),
                        "real_file": str(real_file),
                        "tasks_benchmarked": task_list,
                        "comparison_results": comparison,
                        "utility_results": utility_results
                    }
                    
                    with open(output_report, 'w') as f:
                        json.dump(report_data, f, indent=2, default=str)
                    
                    rprint(f"\n[green]Benchmark report saved: {output_report}[/green]")
                
            except Exception as e:
                progress.update(task_id, description=f"[red]Benchmarking failed: {str(e)}[/red]")
                rprint(f"[red]Benchmarking error: {str(e)}[/red]")
                raise typer.Exit(1)
    
    asyncio.run(_benchmark())


@app.command()
def audit_report(
    output_file: Optional[Path] = typer.Option(None, help="Output report file"),
    days: int = typer.Option(30, help="Number of days to include in report"),
    format: str = typer.Option("json", help="Report format (json, csv)")
):
    """
    Generate compliance audit report.
    """
    audit_trail = AuditTrail()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Generating audit report...", total=None)
        
        try:
            report = audit_trail.generate_compliance_report(
                start_date=start_date,
                end_date=end_date
            )
            
            progress.update(task, description="[green]Report generated![/green]")
            
            # Display summary
            summary = report["summary"]
            rprint(f"\n[bold]Compliance Audit Report ({days} days)[/bold]")
            rprint(f"Total Validations: {summary['total_validations']}")
            rprint(f"Passed Validations: {summary['total_passed']}")
            rprint(f"Overall Pass Rate: [yellow]{summary['overall_pass_rate']:.2%}[/yellow]")
            rprint(f"Compliance Status: [{'green' if report['compliance_status'] == 'COMPLIANT' else 'red'}]{report['compliance_status']}[/{'green' if report['compliance_status'] == 'COMPLIANT' else 'red'}]")
            
            # Framework statistics
            if report["framework_statistics"]:
                table = Table(title="Framework Statistics")
                table.add_column("Framework", style="cyan")
                table.add_column("Total", style="blue")
                table.add_column("Passed", style="green")
                table.add_column("Pass Rate", style="yellow")
                table.add_column("Avg Risk", style="red")
                
                for framework, stats in report["framework_statistics"].items():
                    table.add_row(
                        framework,
                        str(stats["total_validations"]),
                        str(stats["passed_validations"]),
                        f"{stats['pass_rate']:.2%}",
                        f"{stats['avg_risk_score']:.4f}"
                    )
                
                console.print(table)
            
            # Save report
            if output_file:
                if format == "json":
                    with open(output_file, 'w') as f:
                        json.dump(report, f, indent=2, default=str)
                else:
                    exported_data = audit_trail.export_audit_data(
                        export_format=format,
                        start_date=start_date,
                        end_date=end_date
                    )
                    with open(output_file, 'w') as f:
                        f.write(exported_data)
                
                rprint(f"\n[green]Audit report saved: {output_file}[/green]")
            
        except Exception as e:
            progress.update(task, description=f"[red]Report generation failed: {str(e)}[/red]")
            rprint(f"[red]Audit report error: {str(e)}[/red]")
            raise typer.Exit(1)


@app.command()
def status():
    """
    Show system status and configuration.
    """
    rprint("[bold]Synthetic Data Platform MCP - System Status[/bold]\n")
    
    # Version and configuration
    rprint(f"[cyan]Version:[/cyan] 0.1.0")
    rprint(f"[cyan]Python:[/cyan] {sys.version.split()[0]}")
    
    # Check component availability
    components = [
        ("DSPy Framework", "dspy"),
        ("FastMCP", "fastmcp"),
        ("Pydantic", "pydantic"),
        ("NumPy", "numpy"),
        ("Pandas", "pandas"),
        ("SciPy", "scipy"),
        ("Scikit-learn", "sklearn")
    ]
    
    rprint("\n[bold]Component Status:[/bold]")
    
    for name, module in components:
        try:
            __import__(module)
            rprint(f"✅ {name}")
        except ImportError:
            rprint(f"❌ {name} (not installed)")
    
    # Database status
    audit_trail = AuditTrail()
    try:
        recent_ops = audit_trail.get_operation_history(limit=5)
        rprint(f"\n✅ Audit Database ({len(recent_ops)} recent operations)")
    except Exception:
        rprint(f"\n❌ Audit Database (not accessible)")
    
    # Supported domains and frameworks
    rprint(f"\n[bold]Supported Domains:[/bold]")
    for domain in DataDomain:
        rprint(f"• {domain.value}")
    
    rprint(f"\n[bold]Supported Compliance Frameworks:[/bold]")
    for framework in ComplianceFramework:
        rprint(f"• {framework.value}")
    
    rprint(f"\n[bold]Privacy Levels:[/bold]")
    for level in PrivacyLevel:
        rprint(f"• {level.value}")


if __name__ == "__main__":
    app()