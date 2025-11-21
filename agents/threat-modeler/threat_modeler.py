#!/usr/bin/env python3
"""
Threat Modeling Agent - Aardvark Security System
Analyzes codebases to generate comprehensive threat models

Part of the 2 Acre Studios Autonomous Security Research System
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict


@dataclass
class SecurityObjective:
    """Represents a security objective for the system"""
    id: str
    description: str
    priority: str  # critical, high, medium, low
    category: str  # authentication, authorization, data_protection, etc.


@dataclass
class AttackSurfaceComponent:
    """Represents a component in the attack surface"""
    type: str  # web_endpoint, database, external_api, file_system, etc.
    location: str  # file path or endpoint
    description: str
    risk_level: str  # critical, high, medium, low
    entry_points: List[str]
    data_flows: List[str]


@dataclass
class ThreatModel:
    """Complete threat model for a repository"""
    model_id: str
    repository_path: str
    timestamp: str
    security_objectives: List[SecurityObjective]
    attack_surface: List[AttackSurfaceComponent]
    risk_priorities: Dict[str, List[str]]
    metadata: Dict[str, any]


class ThreatModeler:
    """
    Analyzes code repositories to generate threat models
    Identifies security objectives, attack surfaces, and risk priorities
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()
        self.model_id = f"threat-model-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Supported file extensions for analysis
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java', '.rb',
            '.php', '.c', '.cpp', '.h', '.hpp', '.rs', '.swift', '.kt'
        }

        self.config_extensions = {
            '.yml', '.yaml', '.json', '.xml', '.toml', '.ini', '.conf', '.env'
        }

        # Security-critical patterns to identify
        self.security_patterns = {
            'authentication': [
                'login', 'auth', 'signin', 'authenticate', 'password',
                'token', 'jwt', 'oauth', 'session', 'cookie'
            ],
            'authorization': [
                'permission', 'role', 'access', 'authorize', 'rbac',
                'acl', 'admin', 'privilege'
            ],
            'data_protection': [
                'encrypt', 'decrypt', 'hash', 'crypto', 'secret',
                'sensitive', 'pii', 'personal', 'private'
            ],
            'input_validation': [
                'validate', 'sanitize', 'escape', 'filter', 'clean',
                'input', 'param', 'query', 'request'
            ],
            'database': [
                'sql', 'query', 'database', 'db', 'mongodb', 'postgres',
                'mysql', 'redis', 'orm', 'execute'
            ],
            'api_endpoints': [
                'api', 'endpoint', 'route', 'handler', 'controller',
                '@app.', '@router.', 'app.get', 'app.post'
            ],
            'file_operations': [
                'file', 'read', 'write', 'upload', 'download',
                'fs.', 'open(', 'path', 'directory'
            ],
            'network': [
                'http', 'https', 'request', 'fetch', 'axios',
                'socket', 'websocket', 'cors', 'proxy'
            ]
        }

    def analyze_repository(self) -> ThreatModel:
        """
        Main entry point: Analyze repository and generate threat model
        """
        print(f"[+] Analyzing repository: {self.repo_path}")

        # Stage 1: Repository structure analysis
        repo_structure = self._analyze_structure()

        # Stage 2: Identify security objectives
        security_objectives = self._identify_security_objectives(repo_structure)

        # Stage 3: Map attack surface
        attack_surface = self._map_attack_surface(repo_structure)

        # Stage 4: Prioritize risks
        risk_priorities = self._prioritize_risks(attack_surface)

        # Stage 5: Generate metadata
        metadata = self._generate_metadata(repo_structure)

        # Assemble threat model
        threat_model = ThreatModel(
            model_id=self.model_id,
            repository_path=str(self.repo_path),
            timestamp=datetime.now().isoformat(),
            security_objectives=security_objectives,
            attack_surface=attack_surface,
            risk_priorities=risk_priorities,
            metadata=metadata
        )

        print(f"[+] Threat model generated: {self.model_id}")
        return threat_model

    def _analyze_structure(self) -> Dict:
        """Analyze repository structure and identify key components"""
        structure = {
            'total_files': 0,
            'code_files': [],
            'config_files': [],
            'directories': [],
            'languages': set(),
            'frameworks': set(),
            'dependencies': []
        }

        print("[+] Scanning repository structure...")

        # Walk through repository
        for root, dirs, files in os.walk(self.repo_path):
            # Skip common ignore directories
            dirs[:] = [d for d in dirs if d not in {
                '.git', 'node_modules', '__pycache__', 'venv', '.venv',
                'dist', 'build', 'target', '.next', '.cache'
            }]

            rel_root = Path(root).relative_to(self.repo_path)
            structure['directories'].append(str(rel_root))

            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                ext = file_path.suffix.lower()

                structure['total_files'] += 1

                if ext in self.code_extensions:
                    structure['code_files'].append(str(rel_path))
                    structure['languages'].add(ext)

                if ext in self.config_extensions:
                    structure['config_files'].append(str(rel_path))

        # Detect frameworks and dependencies
        structure['frameworks'] = self._detect_frameworks()
        structure['dependencies'] = self._extract_dependencies()

        # Convert sets to lists for JSON serialization
        structure['languages'] = list(structure['languages'])
        structure['frameworks'] = list(structure['frameworks'])

        print(f"    Files: {structure['total_files']}")
        print(f"    Code files: {len(structure['code_files'])}")
        print(f"    Languages: {', '.join(structure['languages'])}")
        print(f"    Frameworks: {', '.join(structure['frameworks'])}")

        return structure

    def _detect_frameworks(self) -> Set[str]:
        """Detect frameworks and technologies used"""
        frameworks = set()

        # Check for common framework indicators
        indicators = {
            'package.json': ['react', 'vue', 'angular', 'express', 'next'],
            'requirements.txt': ['django', 'flask', 'fastapi'],
            'Gemfile': ['rails', 'sinatra'],
            'go.mod': ['gin', 'echo', 'fiber'],
            'pom.xml': ['spring'],
            'Cargo.toml': ['actix', 'rocket']
        }

        for indicator_file, framework_patterns in indicators.items():
            file_path = self.repo_path / indicator_file
            if file_path.exists():
                try:
                    content = file_path.read_text().lower()
                    for pattern in framework_patterns:
                        if pattern in content:
                            frameworks.add(pattern)
                except Exception as e:
                    print(f"    Warning: Could not read {indicator_file}: {e}")

        return frameworks

    def _extract_dependencies(self) -> List[str]:
        """Extract dependencies from dependency files"""
        dependencies = []

        dependency_files = {
            'package.json': self._parse_package_json,
            'requirements.txt': self._parse_requirements_txt,
            'go.mod': self._parse_go_mod
        }

        for dep_file, parser in dependency_files.items():
            file_path = self.repo_path / dep_file
            if file_path.exists():
                try:
                    deps = parser(file_path)
                    dependencies.extend(deps)
                except Exception as e:
                    print(f"    Warning: Could not parse {dep_file}: {e}")

        return dependencies[:50]  # Limit to top 50

    def _parse_package_json(self, file_path: Path) -> List[str]:
        """Parse package.json dependencies"""
        data = json.loads(file_path.read_text())
        deps = []
        for dep_type in ['dependencies', 'devDependencies']:
            if dep_type in data:
                deps.extend(data[dep_type].keys())
        return deps

    def _parse_requirements_txt(self, file_path: Path) -> List[str]:
        """Parse requirements.txt dependencies"""
        lines = file_path.read_text().splitlines()
        return [
            line.split('==')[0].split('>=')[0].split('<')[0].strip()
            for line in lines
            if line.strip() and not line.startswith('#')
        ]

    def _parse_go_mod(self, file_path: Path) -> List[str]:
        """Parse go.mod dependencies"""
        lines = file_path.read_text().splitlines()
        deps = []
        in_require = False
        for line in lines:
            if line.strip().startswith('require'):
                in_require = True
                continue
            if in_require:
                if line.strip() == ')':
                    break
                parts = line.strip().split()
                if parts:
                    deps.append(parts[0])
        return deps

    def _identify_security_objectives(self, repo_structure: Dict) -> List[SecurityObjective]:
        """Identify security objectives based on repository characteristics"""
        objectives = []

        print("[+] Identifying security objectives...")

        # Common objectives for all applications
        objectives.append(SecurityObjective(
            id="obj-001",
            description="Prevent unauthorized access to system resources",
            priority="critical",
            category="authentication"
        ))

        objectives.append(SecurityObjective(
            id="obj-002",
            description="Protect sensitive data in transit and at rest",
            priority="critical",
            category="data_protection"
        ))

        objectives.append(SecurityObjective(
            id="obj-003",
            description="Validate and sanitize all user inputs",
            priority="high",
            category="input_validation"
        ))

        # Framework-specific objectives
        if 'express' in repo_structure['frameworks'] or 'flask' in repo_structure['frameworks']:
            objectives.append(SecurityObjective(
                id="obj-004",
                description="Secure API endpoints against injection attacks",
                priority="critical",
                category="api_security"
            ))

        if 'react' in repo_structure['frameworks'] or 'vue' in repo_structure['frameworks']:
            objectives.append(SecurityObjective(
                id="obj-005",
                description="Prevent XSS attacks in client-side code",
                priority="high",
                category="xss_prevention"
            ))

        # Database-related objectives
        if any(db in str(repo_structure['dependencies']).lower()
               for db in ['pg', 'mysql', 'mongodb', 'sqlite']):
            objectives.append(SecurityObjective(
                id="obj-006",
                description="Prevent SQL/NoSQL injection vulnerabilities",
                priority="critical",
                category="database_security"
            ))

        print(f"    Identified {len(objectives)} security objectives")
        return objectives

    def _map_attack_surface(self, repo_structure: Dict) -> List[AttackSurfaceComponent]:
        """Map the attack surface by identifying entry points and data flows"""
        attack_surface = []

        print("[+] Mapping attack surface...")

        # Analyze code files for security-critical patterns
        for code_file in repo_structure['code_files'][:100]:  # Limit for performance
            file_path = self.repo_path / code_file
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                self._analyze_file_for_attack_surface(
                    code_file, content, attack_surface
                )
            except Exception as e:
                print(f"    Warning: Could not analyze {code_file}: {e}")

        print(f"    Identified {len(attack_surface)} attack surface components")
        return attack_surface

    def _analyze_file_for_attack_surface(
        self,
        file_path: str,
        content: str,
        attack_surface: List[AttackSurfaceComponent]
    ):
        """Analyze a single file for attack surface components"""
        content_lower = content.lower()

        # Check for API endpoints
        if any(pattern in content_lower for pattern in self.security_patterns['api_endpoints']):
            # Extract actual endpoints (simplified)
            entry_points = self._extract_endpoints(content)
            if entry_points:
                attack_surface.append(AttackSurfaceComponent(
                    type="web_endpoint",
                    location=file_path,
                    description=f"API endpoints defined in {file_path}",
                    risk_level="high",
                    entry_points=entry_points,
                    data_flows=["HTTP requests", "Response data"]
                ))

        # Check for database operations
        if any(pattern in content_lower for pattern in self.security_patterns['database']):
            attack_surface.append(AttackSurfaceComponent(
                type="database",
                location=file_path,
                description=f"Database operations in {file_path}",
                risk_level="critical",
                entry_points=["SQL queries", "ORM operations"],
                data_flows=["Database reads", "Database writes"]
            ))

        # Check for file operations
        if any(pattern in content_lower for pattern in self.security_patterns['file_operations']):
            attack_surface.append(AttackSurfaceComponent(
                type="file_system",
                location=file_path,
                description=f"File system operations in {file_path}",
                risk_level="medium",
                entry_points=["File paths", "File contents"],
                data_flows=["File reads", "File writes"]
            ))

    def _extract_endpoints(self, content: str) -> List[str]:
        """Extract API endpoints from code (simplified)"""
        endpoints = []

        # Common endpoint patterns
        patterns = [
            r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)',
            r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)',
            r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)',
            r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)'
        ]

        import re
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                endpoint = match[1] if len(match) > 1 else match[0]
                endpoints.append(endpoint)

        return endpoints[:10]  # Limit to avoid noise

    def _prioritize_risks(self, attack_surface: List[AttackSurfaceComponent]) -> Dict[str, List[str]]:
        """Prioritize risks based on attack surface analysis"""
        priorities = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for component in attack_surface:
            priorities[component.risk_level].append(component.location)

        print("[+] Risk prioritization:")
        for level, components in priorities.items():
            print(f"    {level.upper()}: {len(components)} components")

        return priorities

    def _generate_metadata(self, repo_structure: Dict) -> Dict:
        """Generate metadata about the threat model"""
        return {
            'total_files_analyzed': repo_structure['total_files'],
            'code_files_analyzed': len(repo_structure['code_files']),
            'languages_detected': repo_structure['languages'],
            'frameworks_detected': repo_structure['frameworks'],
            'generation_timestamp': datetime.now().isoformat(),
            'threat_modeler_version': '1.0.0'
        }

    def save_threat_model(self, threat_model: ThreatModel, output_path: Optional[str] = None):
        """Save threat model to JSON file"""
        if output_path is None:
            output_path = self.repo_path / f"threat-model-{self.model_id}.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dict
        model_dict = {
            'model_id': threat_model.model_id,
            'repository_path': threat_model.repository_path,
            'timestamp': threat_model.timestamp,
            'security_objectives': [asdict(obj) for obj in threat_model.security_objectives],
            'attack_surface': [asdict(comp) for comp in threat_model.attack_surface],
            'risk_priorities': threat_model.risk_priorities,
            'metadata': threat_model.metadata
        }

        with open(output_path, 'w') as f:
            json.dump(model_dict, f, indent=2)

        print(f"\n[+] Threat model saved: {output_path}")
        return output_path

    def store_in_enhanced_memory(self, threat_model: ThreatModel):
        """
        Store threat model in enhanced-memory-mcp for future reference
        This will be called via MCP integration
        """
        # This is a placeholder - actual MCP integration will be handled by the orchestrator
        print("[+] Threat model ready for enhanced-memory storage")
        print(f"    Model ID: {threat_model.model_id}")
        print(f"    Security Objectives: {len(threat_model.security_objectives)}")
        print(f"    Attack Surface Components: {len(threat_model.attack_surface)}")


def main():
    """CLI entry point for threat modeler"""
    if len(sys.argv) < 2:
        print("Usage: python threat_modeler.py <repository_path> [output_path]")
        sys.exit(1)

    repo_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    print("="*70)
    print("THREAT MODELING AGENT - Aardvark Security System")
    print("2 Acre Studios Autonomous Security Research")
    print("="*70)
    print()

    modeler = ThreatModeler(repo_path)
    threat_model = modeler.analyze_repository()

    print()
    print("="*70)
    print("THREAT MODEL SUMMARY")
    print("="*70)
    print(f"Model ID: {threat_model.model_id}")
    print(f"Repository: {threat_model.repository_path}")
    print(f"Security Objectives: {len(threat_model.security_objectives)}")
    print(f"Attack Surface Components: {len(threat_model.attack_surface)}")
    print()
    print("Risk Distribution:")
    for level, components in threat_model.risk_priorities.items():
        print(f"  {level.upper()}: {len(components)} components")
    print("="*70)

    # Save to file
    saved_path = modeler.save_threat_model(threat_model, output_path)

    # Prepare for enhanced-memory storage
    modeler.store_in_enhanced_memory(threat_model)

    print("\n[✓] Threat modeling complete!")


if __name__ == "__main__":
    main()
