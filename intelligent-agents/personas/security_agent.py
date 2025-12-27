"""
Security Agent Persona

A specialized persona for security analysis and enforcement.
Follows Kai pattern: deterministic, capable, bounded.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import re

from .persona_base import (
    AgentPersona,
    PersonaType,
    PersonaCapability,
    PersonaConstraint,
    PersonaTrait,
    CommunicationStyle,
    DecisionFramework,
)


class ThreatSeverity(Enum):
    """Severity levels for security threats."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityDomain(Enum):
    """Security focus domains."""
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    DATA = "data"
    IDENTITY = "identity"
    NETWORK = "network"
    COMPLIANCE = "compliance"


@dataclass
class SecurityFinding:
    """A security finding from analysis."""
    title: str
    severity: ThreatSeverity
    domain: SecurityDomain
    description: str
    location: str = ""
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    false_positive_risk: float = 0.0


@dataclass
class SecurityContext:
    """Context for a security task."""
    domains: List[SecurityDomain]
    threat_model: Optional[str] = None
    compliance_standards: List[str] = field(default_factory=list)
    sensitive_data_types: List[str] = field(default_factory=list)
    acceptable_risk_level: ThreatSeverity = ThreatSeverity.MEDIUM


class SecurityAgentPersona(AgentPersona):
    """
    Security Agent: Expert security analyst and enforcer persona.

    Specializations:
    - Code security analysis
    - Vulnerability detection
    - Security policy enforcement
    - Threat modeling
    - Compliance checking
    - Secret detection

    Constraints:
    - Cannot exploit vulnerabilities
    - Cannot access or store secrets directly
    - Cannot bypass security controls
    - Cannot disable security features
    - Must report all findings
    """

    PERSONA_NAME = "SecurityAgent"

    # Common vulnerability patterns
    VULNERABILITY_PATTERNS = {
        "sql_injection": [
            r"execute\s*\(\s*['\"].*\+",
            r"cursor\.execute\s*\([^,]*\%",
            r"f['\"].*SELECT.*{",
        ],
        "xss": [
            r"innerHTML\s*=",
            r"document\.write\s*\(",
            r"\.html\s*\([^)]*\+",
        ],
        "command_injection": [
            r"os\.system\s*\([^)]*\+",
            r"subprocess\..*shell\s*=\s*True",
            r"eval\s*\([^)]*input",
        ],
        "path_traversal": [
            r"open\s*\([^)]*\+",
            r"\.\.\/",
            r"%2e%2e%2f",
        ],
        "hardcoded_secrets": [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"api_key\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"token\s*=\s*['\"][A-Za-z0-9+/=]{20,}['\"]",
        ],
        "insecure_crypto": [
            r"md5\s*\(",
            r"sha1\s*\(",
            r"DES\s*\(",
            r"random\.random\s*\(",  # Non-cryptographic random
        ],
    }

    def __init__(
        self,
        domains: Optional[List[SecurityDomain]] = None,
        offensive_mode: bool = False,
        compliance_focus: Optional[List[str]] = None
    ):
        """
        Initialize Security Agent.

        Args:
            domains: Security domains to focus on
            offensive_mode: If True, can perform active testing (requires approval)
            compliance_focus: Compliance standards to check (SOC2, PCI-DSS, etc.)
        """
        self.domains = domains or [SecurityDomain.APPLICATION]
        self.offensive_mode = offensive_mode
        self.compliance_focus = compliance_focus or []

        traits = [
            PersonaTrait.CAUTIOUS,
            PersonaTrait.THOROUGH,
            PersonaTrait.FOCUSED,
        ]

        decision_framework = DecisionFramework(
            primary_goal="Identify and help remediate security vulnerabilities",
            success_metrics=[
                "vulnerabilities_found",
                "false_positives_minimized",
                "remediation_provided",
                "compliance_verified",
                "secrets_protected",
            ],
            failure_indicators=[
                "vulnerability_missed",
                "false_positive_flood",
                "secrets_exposed",
                "security_bypassed",
            ],
            escalation_triggers=[
                "critical_vulnerability",
                "active_exploitation",
                "data_breach_suspected",
                "compliance_violation",
                "credential_exposure",
            ],
            default_action="report_and_recommend",
            risk_tolerance="low",
        )

        domains_str = ", ".join(d.value for d in self.domains)
        super().__init__(
            name=f"Security Agent ({domains_str})",
            persona_type=PersonaType.SECURITY,
            description=f"Expert security analyst for {domains_str} security",
            primary_purpose="Analyze, detect, and help remediate security vulnerabilities",
            communication_style=CommunicationStyle.TECHNICAL,
            traits=traits,
            decision_framework=decision_framework,
        )

    def _setup_capabilities(self) -> None:
        """Set up security agent capabilities."""

        # Core security analysis capabilities
        self.add_capability(PersonaCapability(
            name="code_security_analysis",
            description="Analyze code for security vulnerabilities",
            tools=["Read", "Grep", "Glob"],
            proficiency=0.95,
            max_complexity=10,
        ))

        self.add_capability(PersonaCapability(
            name="secret_detection",
            description="Detect hardcoded secrets and credentials",
            tools=["Grep", "Read", "Glob"],
            proficiency=0.95,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="configuration_audit",
            description="Audit configuration for security issues",
            tools=["Read", "Glob", "Grep"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="dependency_analysis",
            description="Analyze dependencies for known vulnerabilities",
            tools=["Read", "Bash", "WebFetch"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="threat_modeling",
            description="Model threats and attack surfaces",
            tools=["Read", "Glob"],
            proficiency=0.85,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="security_reporting",
            description="Generate security assessment reports",
            tools=["Write", "Read"],
            proficiency=0.9,
            max_complexity=7,
        ))

        self.add_capability(PersonaCapability(
            name="remediation_guidance",
            description="Provide security remediation recommendations",
            tools=["Read", "Write"],
            proficiency=0.9,
            max_complexity=8,
        ))

        # Compliance capabilities
        if self.compliance_focus:
            self.add_capability(PersonaCapability(
                name="compliance_checking",
                description=f"Check compliance: {', '.join(self.compliance_focus)}",
                tools=["Read", "Grep", "Glob"],
                proficiency=0.85,
                max_complexity=8,
            ))

        # Offensive testing (with approval)
        if self.offensive_mode:
            self.add_capability(PersonaCapability(
                name="penetration_testing",
                description="Active security testing (requires approval)",
                tools=["Bash", "WebFetch"],
                proficiency=0.8,
                requires_confirmation=True,
                max_complexity=9,
            ))

            self.add_capability(PersonaCapability(
                name="vulnerability_verification",
                description="Verify vulnerabilities are exploitable",
                tools=["Bash", "Read"],
                proficiency=0.8,
                requires_confirmation=True,
                max_complexity=8,
            ))

        # Domain-specific capabilities
        for domain in self.domains:
            if domain == SecurityDomain.INFRASTRUCTURE:
                self._setup_infra_capabilities()
            elif domain == SecurityDomain.NETWORK:
                self._setup_network_capabilities()
            elif domain == SecurityDomain.IDENTITY:
                self._setup_identity_capabilities()

    def _setup_infra_capabilities(self) -> None:
        """Infrastructure security capabilities."""
        self.add_capability(PersonaCapability(
            name="infrastructure_audit",
            description="Audit infrastructure security configuration",
            tools=["Read", "Bash", "Glob"],
            proficiency=0.85,
            max_complexity=8,
        ))

    def _setup_network_capabilities(self) -> None:
        """Network security capabilities."""
        self.add_capability(PersonaCapability(
            name="network_analysis",
            description="Analyze network security posture",
            tools=["Bash", "Read"],
            proficiency=0.85,
            max_complexity=8,
        ))

    def _setup_identity_capabilities(self) -> None:
        """Identity security capabilities."""
        self.add_capability(PersonaCapability(
            name="identity_audit",
            description="Audit identity and access management",
            tools=["Read", "Grep"],
            proficiency=0.85,
            max_complexity=8,
        ))

    def _setup_constraints(self) -> None:
        """Set up security agent constraints."""

        # Never exploit vulnerabilities
        self.add_constraint(PersonaConstraint(
            name="no_exploitation",
            description="Cannot exploit vulnerabilities maliciously",
            type="forbidden",
            patterns=[
                r"exploit",
                r"pwn",
                r"attack",
                r"hack\s+into",
                r"break\s+into",
            ],
            reason="Security agent identifies vulnerabilities but does not exploit them",
        ))

        # Cannot access secrets directly
        self.add_constraint(PersonaConstraint(
            name="no_secret_access",
            description="Cannot access or store secrets directly",
            type="forbidden",
            patterns=[
                r"cat.*\.env",
                r"echo.*secret",
                r"print.*password",
                r"export.*key",
            ],
            reason="Secrets must remain protected - can detect but not access",
        ))

        # Cannot bypass security controls
        self.add_constraint(PersonaConstraint(
            name="no_security_bypass",
            description="Cannot bypass security controls",
            type="forbidden",
            patterns=[
                r"disable.*auth",
                r"skip.*validation",
                r"bypass.*security",
                r"turn\s+off.*firewall",
            ],
            reason="Security controls must remain active",
        ))

        # Cannot disable security features
        self.add_constraint(PersonaConstraint(
            name="no_security_disable",
            description="Cannot disable security features",
            type="forbidden",
            patterns=[
                r"disable.*security",
                r"turn\s+off.*ssl",
                r"disable.*tls",
                r"remove.*auth",
            ],
            reason="Security features must remain enabled",
        ))

        # Must report critical findings
        self.add_constraint(PersonaConstraint(
            name="must_report_critical",
            description="Must report all critical findings",
            type="limited",
            patterns=[],  # Enforced through finding reporting
            reason="Critical vulnerabilities must always be reported",
        ))

        # Offensive testing requires approval
        if self.offensive_mode:
            self.add_constraint(PersonaConstraint(
                name="offensive_requires_approval",
                description="Active testing requires explicit approval",
                type="requires_approval",
                patterns=[
                    r"scan",
                    r"test.*vulnerability",
                    r"probe",
                    r"enumerate",
                ],
                reason="Active security testing requires authorization",
            ))

    def scan_code_for_vulnerabilities(
        self,
        code: str,
        filename: str = ""
    ) -> List[SecurityFinding]:
        """
        Scan code for common security vulnerabilities.

        Args:
            code: Source code to scan
            filename: Optional filename for context

        Returns:
            List of security findings
        """
        findings = []

        for vuln_type, patterns in self.VULNERABILITY_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE))
                for match in matches:
                    # Determine severity based on vulnerability type
                    severity = self._get_vuln_severity(vuln_type)

                    # Find line number
                    line_num = code[:match.start()].count('\n') + 1

                    findings.append(SecurityFinding(
                        title=f"Potential {vuln_type.replace('_', ' ').title()}",
                        severity=severity,
                        domain=SecurityDomain.APPLICATION,
                        description=f"Pattern matched: {match.group()[:50]}...",
                        location=f"{filename}:{line_num}" if filename else f"Line {line_num}",
                        remediation=self._get_remediation(vuln_type),
                        false_positive_risk=0.2,  # Regex detection has FP risk
                    ))

        return findings

    def _get_vuln_severity(self, vuln_type: str) -> ThreatSeverity:
        """Get severity for vulnerability type."""
        severity_map = {
            "sql_injection": ThreatSeverity.CRITICAL,
            "xss": ThreatSeverity.HIGH,
            "command_injection": ThreatSeverity.CRITICAL,
            "path_traversal": ThreatSeverity.HIGH,
            "hardcoded_secrets": ThreatSeverity.HIGH,
            "insecure_crypto": ThreatSeverity.MEDIUM,
        }
        return severity_map.get(vuln_type, ThreatSeverity.MEDIUM)

    def _get_remediation(self, vuln_type: str) -> str:
        """Get remediation guidance for vulnerability type."""
        remediation_map = {
            "sql_injection": "Use parameterized queries or prepared statements",
            "xss": "Sanitize user input and use context-aware output encoding",
            "command_injection": "Use safe APIs, avoid shell=True, validate input",
            "path_traversal": "Validate and canonicalize paths, use allowlists",
            "hardcoded_secrets": "Use environment variables or secret management",
            "insecure_crypto": "Use strong cryptographic algorithms (SHA-256+, AES)",
        }
        return remediation_map.get(vuln_type, "Review and remediate according to security best practices")

    def scan_for_secrets(self, code: str) -> List[SecurityFinding]:
        """
        Specifically scan for hardcoded secrets.

        Args:
            code: Source code to scan

        Returns:
            List of secret-related findings
        """
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\'][^"\']{10,}["\']', "API Key"),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', "Password"),
            (r'secret\s*[=:]\s*["\'][^"\']+["\']', "Secret"),
            (r'token\s*[=:]\s*["\'][A-Za-z0-9+/=]{20,}["\']', "Token"),
            (r'private[_-]?key', "Private Key Reference"),
            (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "Private Key"),
            (r'aws[_-]?secret[_-]?access[_-]?key', "AWS Secret Key"),
            (r'ghp_[A-Za-z0-9]{36}', "GitHub Token"),
            (r'sk-[A-Za-z0-9]{32,}', "OpenAI API Key"),
        ]

        findings = []
        for pattern, secret_type in secret_patterns:
            matches = list(re.finditer(pattern, code, re.IGNORECASE))
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                # Redact the actual secret
                redacted = match.group()[:10] + "..." if len(match.group()) > 10 else "[REDACTED]"

                findings.append(SecurityFinding(
                    title=f"Hardcoded {secret_type} Detected",
                    severity=ThreatSeverity.HIGH,
                    domain=SecurityDomain.DATA,
                    description=f"Potential hardcoded secret found: {redacted}",
                    location=f"Line {line_num}",
                    remediation="Move secrets to environment variables or secure vault",
                    references=["CWE-798: Use of Hard-coded Credentials"],
                ))

        return findings

    def create_security_context(
        self,
        threat_model: Optional[str] = None,
        sensitive_data: Optional[List[str]] = None
    ) -> SecurityContext:
        """
        Create a security analysis context.

        Args:
            threat_model: Optional threat model description
            sensitive_data: Types of sensitive data present

        Returns:
            SecurityContext for the analysis
        """
        return SecurityContext(
            domains=self.domains,
            threat_model=threat_model,
            compliance_standards=self.compliance_focus,
            sensitive_data_types=sensitive_data or [],
            acceptable_risk_level=ThreatSeverity.MEDIUM,
        )

    def prioritize_findings(
        self,
        findings: List[SecurityFinding]
    ) -> List[SecurityFinding]:
        """
        Prioritize security findings by severity.

        Args:
            findings: List of findings to prioritize

        Returns:
            Sorted findings (critical first)
        """
        severity_order = {
            ThreatSeverity.CRITICAL: 0,
            ThreatSeverity.HIGH: 1,
            ThreatSeverity.MEDIUM: 2,
            ThreatSeverity.LOW: 3,
            ThreatSeverity.INFO: 4,
        }

        return sorted(
            findings,
            key=lambda f: (severity_order[f.severity], f.false_positive_risk)
        )

    def generate_security_report(
        self,
        findings: List[SecurityFinding],
        context: SecurityContext
    ) -> Dict[str, Any]:
        """
        Generate a security assessment report.

        Args:
            findings: List of findings
            context: Security context

        Returns:
            Structured report
        """
        # Group by severity
        by_severity = {}
        for finding in findings:
            sev = finding.severity.value
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(finding)

        # Calculate risk score
        risk_weights = {
            ThreatSeverity.CRITICAL: 10,
            ThreatSeverity.HIGH: 5,
            ThreatSeverity.MEDIUM: 2,
            ThreatSeverity.LOW: 1,
            ThreatSeverity.INFO: 0,
        }
        risk_score = sum(risk_weights[f.severity] for f in findings)
        max_score = len(findings) * 10 if findings else 1
        risk_percentage = (risk_score / max_score) * 100

        return {
            "summary": {
                "total_findings": len(findings),
                "critical": len(by_severity.get("critical", [])),
                "high": len(by_severity.get("high", [])),
                "medium": len(by_severity.get("medium", [])),
                "low": len(by_severity.get("low", [])),
                "risk_score": risk_score,
                "risk_percentage": round(risk_percentage, 1),
            },
            "domains_analyzed": [d.value for d in context.domains],
            "compliance_checked": context.compliance_standards,
            "findings": [
                {
                    "title": f.title,
                    "severity": f.severity.value,
                    "domain": f.domain.value,
                    "description": f.description,
                    "location": f.location,
                    "remediation": f.remediation,
                }
                for f in self.prioritize_findings(findings)
            ],
            "recommendations": self._generate_recommendations(findings, context),
        }

    def _generate_recommendations(
        self,
        findings: List[SecurityFinding],
        context: SecurityContext
    ) -> List[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        # Check for critical issues
        critical = [f for f in findings if f.severity == ThreatSeverity.CRITICAL]
        if critical:
            recommendations.append(
                f"IMMEDIATE: Address {len(critical)} critical vulnerabilities before deployment"
            )

        # Check for secrets
        secrets = [f for f in findings if "secret" in f.title.lower() or "key" in f.title.lower()]
        if secrets:
            recommendations.append(
                "Implement secrets management solution (HashiCorp Vault, AWS Secrets Manager)"
            )

        # General recommendations
        if len(findings) > 10:
            recommendations.append(
                "Consider implementing automated security scanning in CI/CD pipeline"
            )

        if SecurityDomain.APPLICATION in context.domains:
            recommendations.append(
                "Implement input validation and output encoding consistently"
            )

        return recommendations

    def get_security_prompt_additions(self) -> str:
        """Get security-specific prompt additions."""
        additions = [
            f"SECURITY DOMAINS: {', '.join(d.value for d in self.domains)}",
            f"MODE: {'Offensive testing enabled' if self.offensive_mode else 'Analysis only'}",
        ]

        if self.compliance_focus:
            additions.append(f"COMPLIANCE: {', '.join(self.compliance_focus)}")

        additions.extend([
            "\nSECURITY PRINCIPLES:",
            "- Never expose or log actual secrets",
            "- Report all findings, prioritized by severity",
            "- Provide actionable remediation guidance",
            "- Consider false positive likelihood",
            "- Follow responsible disclosure practices",
        ])

        return "\n".join(additions)


if __name__ == '__main__':
    print("SecurityAgentPersona Self-Test")
    print("=" * 50)

    # Test general security agent
    agent = SecurityAgentPersona(domains=[SecurityDomain.APPLICATION])
    print(f"\nSecurity Agent: {agent.name}")
    print(f"Capabilities: {len(agent._capabilities)}")
    print(f"Constraints: {len(agent._constraints)}")

    # Test capability checks
    assert agent.has_capability("code_security_analysis"), "Should have code analysis"
    assert agent.has_capability("secret_detection"), "Should have secret detection"
    assert agent.can_use_tool("Grep"), "Should be able to use Grep"

    # Test constraint checks
    constraint = agent.check_constraint("exploit the vulnerability")
    assert constraint is not None, "Should detect exploitation"
    assert constraint.name == "no_exploitation"

    constraint = agent.check_constraint("disable authentication")
    assert constraint is not None, "Should detect security disable"

    safe = agent.check_constraint("scan code for vulnerabilities")
    # Note: "scan" might trigger offensive constraint only in offensive mode
    # In normal mode, code analysis is allowed

    # Test vulnerability scanning
    vulnerable_code = '''
def login(username, password):
    query = "SELECT * FROM users WHERE name='" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()
'''
    findings = agent.scan_code_for_vulnerabilities(vulnerable_code)
    assert len(findings) > 0, "Should find SQL injection"
    assert any("sql" in f.title.lower() for f in findings), "Should identify as SQL injection"

    # Test secret scanning
    code_with_secrets = '''
API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyz"
password = "mysecretpassword123"
'''
    secrets = agent.scan_for_secrets(code_with_secrets)
    assert len(secrets) >= 2, "Should find multiple secrets"

    # Test offensive mode
    offensive_agent = SecurityAgentPersona(
        domains=[SecurityDomain.APPLICATION],
        offensive_mode=True
    )
    assert offensive_agent.has_capability("penetration_testing"), "Offensive should have pentest"
    constraint = offensive_agent.check_constraint("scan the target")
    assert constraint is not None, "Offensive testing should require approval"

    # Test compliance mode
    compliance_agent = SecurityAgentPersona(
        domains=[SecurityDomain.APPLICATION, SecurityDomain.DATA],
        compliance_focus=["SOC2", "PCI-DSS"]
    )
    assert compliance_agent.has_capability("compliance_checking"), "Should have compliance"

    # Test finding prioritization
    findings = [
        SecurityFinding("Low Issue", ThreatSeverity.LOW, SecurityDomain.APPLICATION, "desc"),
        SecurityFinding("Critical Issue", ThreatSeverity.CRITICAL, SecurityDomain.APPLICATION, "desc"),
        SecurityFinding("High Issue", ThreatSeverity.HIGH, SecurityDomain.APPLICATION, "desc"),
    ]
    prioritized = agent.prioritize_findings(findings)
    assert prioritized[0].severity == ThreatSeverity.CRITICAL, "Critical should be first"

    # Test report generation
    context = agent.create_security_context(threat_model="Web application")
    report = agent.generate_security_report(findings, context)
    assert report["summary"]["total_findings"] == 3
    assert report["summary"]["critical"] == 1
    assert len(report["recommendations"]) > 0

    # Test system prompt
    prompt = agent.generate_system_prompt()
    assert "Security Agent" in prompt
    assert "code_security_analysis" in prompt

    print("\n" + agent.get_summary())
    print("\nSecurity prompt additions:")
    print(agent.get_security_prompt_additions())

    # Print sample report
    print("\nSample Security Report:")
    print(f"  Findings: {report['summary']['total_findings']}")
    print(f"  Critical: {report['summary']['critical']}")
    print(f"  Risk Score: {report['summary']['risk_score']}")
    print(f"  Recommendations: {len(report['recommendations'])}")

    print("\nAll SecurityAgentPersona tests passed!")
