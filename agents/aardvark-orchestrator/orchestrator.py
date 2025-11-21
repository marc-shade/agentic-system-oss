#!/usr/bin/env python3
"""
Aardvark Orchestrator - Autonomous Security Research System
Coordinates threat modeling, vulnerability scanning, exploit validation, and patch generation

Part of the 2 Acre Studios Agentic Security Framework
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse


@dataclass
class SecurityScanResult:
    """Result from a security scan operation"""
    scan_id: str
    scan_type: str  # threat_model, vulnerability_scan, exploit_validation, patch_generation
    timestamp: str
    repository_path: str
    status: str  # success, failure, partial
    findings_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    output_path: str
    error_message: Optional[str] = None


class AardvarkOrchestrator:
    """
    Main orchestrator for the Aardvark autonomous security research system
    Coordinates multiple specialized agents to provide comprehensive security analysis
    """

    def __init__(self, repo_path: str, config: Optional[Dict] = None):
        self.repo_path = Path(repo_path).resolve()
        self.config = self._merge_config(config)
        self.scan_id = f"aardvark-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Agent paths
        self.agents_dir = Path(__file__).parent.parent
        self.threat_modeler = self.agents_dir / "threat-modeler" / "threat_modeler.py"
        self.vuln_scanner = self.agents_dir / "vulnerability-scanner" / "scanner.py"
        self.exploit_validator = self.agents_dir / "exploit-validator" / "validator.py"
        self.patch_generator = self.agents_dir / "patch-generator" / "generator.py"

        # Output directory
        self.output_dir = Path(self.config.get('output_dir', '/tmp/aardvark-scans'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.scan_output_dir = self.output_dir / self.scan_id
        self.scan_output_dir.mkdir(parents=True, exist_ok=True)

    def _merge_config(self, user_config: Optional[Dict] = None) -> Dict:
        """Merge user config with defaults"""
        default = self._default_config()
        if user_config:
            default.update(user_config)
        return default

    def _default_config(self) -> Dict:
        """Default configuration for Aardvark"""
        return {
            'output_dir': '/tmp/aardvark-scans',
            'modes': {
                'full': ['threat_model', 'vulnerability_scan', 'exploit_validation', 'patch_generation'],
                'quick': ['threat_model', 'vulnerability_scan'],
                'ci': ['vulnerability_scan'],  # Fast scan for CI/CD
                'audit': ['threat_model', 'vulnerability_scan']  # Comprehensive audit
            },
            'parallel': True,  # Run stages in parallel when possible
            'store_in_memory': True,  # Store results in enhanced-memory
            'severity_threshold': 'medium',  # Minimum severity to report
            'auto_patch': False  # Don't auto-apply patches (require human review)
        }

    def run_full_analysis(self) -> List[SecurityScanResult]:
        """
        Run complete Aardvark analysis pipeline
        Returns list of scan results for each stage
        """
        mode = self.config.get('mode', 'full')
        stages = self.config['modes'].get(mode, self.config['modes']['full'])

        print("="*80)
        print("AARDVARK AUTONOMOUS SECURITY RESEARCH SYSTEM")
        print("2 Acre Studios Agentic Framework")
        print("="*80)
        print(f"Scan ID: {self.scan_id}")
        print(f"Repository: {self.repo_path}")
        print(f"Mode: {mode}")
        print(f"Stages: {', '.join(stages)}")
        print("="*80)
        print()

        results = []

        # Stage 1: Threat Modeling
        if 'threat_model' in stages:
            print("[Stage 1/4] THREAT MODELING")
            print("-" * 80)
            threat_result = self._run_threat_modeling()
            results.append(threat_result)
            print()

        # Stage 2: Vulnerability Scanning
        if 'vulnerability_scan' in stages:
            print("[Stage 2/4] VULNERABILITY SCANNING")
            print("-" * 80)
            vuln_result = self._run_vulnerability_scanning()
            results.append(vuln_result)
            print()

        # Stage 3: Exploit Validation (only if critical vulnerabilities found)
        if 'exploit_validation' in stages:
            critical_vulns = sum(r.critical_count for r in results if r.scan_type == 'vulnerability_scan')
            if critical_vulns > 0:
                print("[Stage 3/4] EXPLOIT VALIDATION")
                print("-" * 80)
                print(f"Validating {critical_vulns} critical vulnerabilities...")
                exploit_result = self._run_exploit_validation()
                results.append(exploit_result)
                print()
            else:
                print("[Stage 3/4] EXPLOIT VALIDATION - SKIPPED")
                print("-" * 80)
                print("No critical vulnerabilities found - skipping validation")
                print()

        # Stage 4: Patch Generation
        if 'patch_generation' in stages:
            confirmed_vulns = sum(r.findings_count for r in results if r.scan_type == 'exploit_validation')
            if confirmed_vulns > 0:
                print("[Stage 4/4] PATCH GENERATION")
                print("-" * 80)
                print(f"Generating patches for {confirmed_vulns} confirmed vulnerabilities...")
                patch_result = self._run_patch_generation()
                results.append(patch_result)
                print()
            else:
                print("[Stage 4/4] PATCH GENERATION - SKIPPED")
                print("-" * 80)
                print("No confirmed vulnerabilities - skipping patch generation")
                print()

        # Generate final report
        self._generate_final_report(results)

        return results

    def _run_threat_modeling(self) -> SecurityScanResult:
        """Execute threat modeling agent"""
        output_path = self.scan_output_dir / "threat-model.json"

        try:
            # Run threat modeler
            cmd = [
                'python3',
                str(self.threat_modeler),
                str(self.repo_path),
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                # Parse output to get stats
                with open(output_path) as f:
                    threat_model = json.load(f)

                # Count findings by severity
                risk_counts = threat_model['risk_priorities']

                scan_result = SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='threat_model',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='success',
                    findings_count=len(threat_model['attack_surface']),
                    critical_count=len(risk_counts.get('critical', [])),
                    high_count=len(risk_counts.get('high', [])),
                    medium_count=len(risk_counts.get('medium', [])),
                    low_count=len(risk_counts.get('low', [])),
                    output_path=str(output_path)
                )

                print(f"✓ Threat model generated: {scan_result.findings_count} attack surface components")
                print(f"  Critical: {scan_result.critical_count}")
                print(f"  High: {scan_result.high_count}")
                print(f"  Medium: {scan_result.medium_count}")
                print(f"  Low: {scan_result.low_count}")

                # Store in enhanced-memory if configured
                if self.config.get('store_in_memory'):
                    self._store_threat_model_in_memory(output_path)

                return scan_result

            else:
                return SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='threat_model',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='failure',
                    findings_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    output_path=str(output_path),
                    error_message=result.stderr
                )

        except Exception as e:
            print(f"✗ Threat modeling failed: {e}")
            return SecurityScanResult(
                scan_id=self.scan_id,
                scan_type='threat_model',
                timestamp=datetime.now().isoformat(),
                repository_path=str(self.repo_path),
                status='failure',
                findings_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                output_path=str(output_path),
                error_message=str(e)
            )

    def _run_vulnerability_scanning(self) -> SecurityScanResult:
        """Execute vulnerability scanning using Nuclei and Checkov"""
        output_path = self.scan_output_dir / "vulnerabilities.json"
        threat_model_path = self.scan_output_dir / "threat-model.json"

        try:
            # Run vulnerability scanner
            cmd = [
                'python3',
                str(self.vuln_scanner),
                str(self.repo_path),
                '--output', str(output_path)
            ]

            # Add threat model if available
            if threat_model_path.exists():
                cmd.extend(['--threat-model', str(threat_model_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 minute timeout
            )

            if result.returncode == 0 and output_path.exists():
                # Parse results
                with open(output_path) as f:
                    vuln_data = json.load(f)

                scan_result = SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='vulnerability_scan',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='success',
                    findings_count=vuln_data['stats']['total'],
                    critical_count=vuln_data['stats']['critical'],
                    high_count=vuln_data['stats']['high'],
                    medium_count=vuln_data['stats']['medium'],
                    low_count=vuln_data['stats']['low'],
                    output_path=str(output_path)
                )

                print(f"✓ Vulnerability scan complete: {scan_result.findings_count} vulnerabilities found")
                print(f"  Critical: {scan_result.critical_count}")
                print(f"  High: {scan_result.high_count}")
                print(f"  Medium: {scan_result.medium_count}")

                return scan_result

            else:
                return SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='vulnerability_scan',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='failure',
                    findings_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    output_path=str(output_path),
                    error_message=result.stderr
                )

        except Exception as e:
            print(f"✗ Vulnerability scanning failed: {e}")
            return SecurityScanResult(
                scan_id=self.scan_id,
                scan_type='vulnerability_scan',
                timestamp=datetime.now().isoformat(),
                repository_path=str(self.repo_path),
                status='failure',
                findings_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                output_path=str(output_path),
                error_message=str(e)
            )

    def _run_exploit_validation(self) -> SecurityScanResult:
        """Execute exploit validation in sandbox"""
        output_path = self.scan_output_dir / "exploits.json"
        vuln_path = self.scan_output_dir / "vulnerabilities.json"

        try:
            # Run exploit validator
            cmd = [
                'python3',
                str(self.exploit_validator),
                str(vuln_path),
                '--output', str(output_path)
            ]

            # Add cluster flag if configured
            if not self.config.get('use_cluster', True):
                cmd.append('--no-cluster')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0 and output_path.exists():
                # Parse results
                with open(output_path) as f:
                    validation_data = json.load(f)

                # Count by impact level
                impact_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
                for result_item in validation_data.get('results', []):
                    if result_item.get('exploitable'):
                        impact = result_item.get('impact', 'medium')
                        impact_counts[impact] = impact_counts.get(impact, 0) + 1

                scan_result = SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='exploit_validation',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='success',
                    findings_count=validation_data.get('exploits_confirmed', 0),
                    critical_count=impact_counts['critical'],
                    high_count=impact_counts['high'],
                    medium_count=impact_counts['medium'],
                    low_count=impact_counts['low'],
                    output_path=str(output_path)
                )

                print(f"✓ Exploit validation complete: {scan_result.findings_count} exploits confirmed")
                print(f"  Critical: {scan_result.critical_count}")
                print(f"  High: {scan_result.high_count}")
                print(f"  Medium: {scan_result.medium_count}")

                return scan_result

            else:
                return SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='exploit_validation',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='failure',
                    findings_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    output_path=str(output_path),
                    error_message=result.stderr
                )

        except Exception as e:
            print(f"✗ Exploit validation failed: {e}")
            return SecurityScanResult(
                scan_id=self.scan_id,
                scan_type='exploit_validation',
                timestamp=datetime.now().isoformat(),
                repository_path=str(self.repo_path),
                status='failure',
                findings_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                output_path=str(output_path),
                error_message=str(e)
            )

    def _run_patch_generation(self) -> SecurityScanResult:
        """Execute patch generation for confirmed vulnerabilities"""
        output_path = self.scan_output_dir / "patches.json"
        exploits_path = self.scan_output_dir / "exploits.json"
        patches_dir = self.scan_output_dir / "patches"

        try:
            # Run patch generator
            cmd = [
                'python3',
                str(self.patch_generator),
                str(exploits_path),
                str(self.repo_path),
                '--output', str(output_path),
                '--patch-dir', str(patches_dir)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1200  # 20 minute timeout
            )

            if result.returncode == 0 and output_path.exists():
                # Parse results
                with open(output_path) as f:
                    patch_data = json.load(f)

                scan_result = SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='patch_generation',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='success',
                    findings_count=patch_data.get('patches_generated', 0),
                    critical_count=0,  # Patches don't have severity
                    high_count=0,
                    medium_count=patch_data.get('patches_passed', 0),
                    low_count=patch_data.get('patches_generated', 0) - patch_data.get('patches_passed', 0),
                    output_path=str(output_path)
                )

                print(f"✓ Patch generation complete: {scan_result.findings_count} patches generated")
                print(f"  Tested: {patch_data.get('patches_tested', 0)}")
                print(f"  Passed: {patch_data.get('patches_passed', 0)}")

                return scan_result

            else:
                return SecurityScanResult(
                    scan_id=self.scan_id,
                    scan_type='patch_generation',
                    timestamp=datetime.now().isoformat(),
                    repository_path=str(self.repo_path),
                    status='failure',
                    findings_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    output_path=str(output_path),
                    error_message=result.stderr
                )

        except Exception as e:
            print(f"✗ Patch generation failed: {e}")
            return SecurityScanResult(
                scan_id=self.scan_id,
                scan_type='patch_generation',
                timestamp=datetime.now().isoformat(),
                repository_path=str(self.repo_path),
                status='failure',
                findings_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                output_path=str(output_path),
                error_message=str(e)
            )

    def _store_threat_model_in_memory(self, threat_model_path: str):
        """Store threat model in enhanced-memory-mcp"""
        print("  → Storing threat model in enhanced-memory...")

        # Use the MCP integration script
        integration_script = self.agents_dir / "threat-modeler" / "mcp_integration.py"

        cmd = [
            'python3',
            str(integration_script),
            threat_model_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("  ✓ Stored in enhanced-memory")
        except Exception as e:
            print(f"  ✗ Failed to store in memory: {e}")

    def _generate_final_report(self, results: List[SecurityScanResult]):
        """Generate comprehensive final report"""
        report_path = self.scan_output_dir / "aardvark-report.json"

        report = {
            'scan_id': self.scan_id,
            'repository': str(self.repo_path),
            'timestamp': datetime.now().isoformat(),
            'stages_completed': len(results),
            'overall_status': 'success' if all(r.status == 'success' for r in results) else 'partial',
            'total_findings': sum(r.findings_count for r in results),
            'severity_distribution': {
                'critical': sum(r.critical_count for r in results),
                'high': sum(r.high_count for r in results),
                'medium': sum(r.medium_count for r in results),
                'low': sum(r.low_count for r in results)
            },
            'stage_results': [asdict(r) for r in results],
            'output_directory': str(self.scan_output_dir)
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print("="*80)
        print("AARDVARK SCAN COMPLETE")
        print("="*80)
        print(f"Scan ID: {self.scan_id}")
        print(f"Total Findings: {report['total_findings']}")
        print()
        print("Severity Distribution:")
        print(f"  Critical: {report['severity_distribution']['critical']}")
        print(f"  High: {report['severity_distribution']['high']}")
        print(f"  Medium: {report['severity_distribution']['medium']}")
        print(f"  Low: {report['severity_distribution']['low']}")
        print()
        print(f"Full Report: {report_path}")
        print("="*80)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Aardvark Autonomous Security Research System'
    )
    parser.add_argument('repository', help='Path to repository to analyze')
    parser.add_argument(
        '--mode',
        choices=['full', 'quick', 'ci', 'audit'],
        default='full',
        help='Scan mode (default: full)'
    )
    parser.add_argument(
        '--output',
        default='/tmp/aardvark-scans',
        help='Output directory (default: /tmp/aardvark-scans)'
    )
    parser.add_argument(
        '--no-memory',
        action='store_true',
        help='Do not store results in enhanced-memory'
    )

    args = parser.parse_args()

    config = {
        'mode': args.mode,
        'output_dir': args.output,
        'store_in_memory': not args.no_memory
    }

    orchestrator = AardvarkOrchestrator(args.repository, config)
    results = orchestrator.run_full_analysis()

    # Exit with error code if any stage failed
    if any(r.status == 'failure' for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
