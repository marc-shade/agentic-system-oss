"""
Regulatory reporting framework for compliance requirements.

Generates comprehensive reports for HIPAA, GDPR, PCI DSS, SOX, and other
regulatory frameworks with automated scheduling and submission.
"""

import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import asyncio
import hashlib
import uuid

import pandas as pd
from jinja2 import Template, Environment, FileSystemLoader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from loguru import logger
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib


class RegulatoryFramework(Enum):
    """Supported regulatory frameworks."""
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    CCPA = "ccpa"
    FERPA = "ferpa"
    GLBA = "glba"


class ReportType(Enum):
    """Types of regulatory reports."""
    BREACH_NOTIFICATION = "breach_notification"
    AUDIT_TRAIL = "audit_trail"
    DATA_INVENTORY = "data_inventory"
    PRIVACY_IMPACT = "privacy_impact"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_ATTESTATION = "compliance_attestation"
    DATA_SUBJECT_REQUEST = "data_subject_request"
    INCIDENT_RESPONSE = "incident_response"
    ACCESS_REVIEW = "access_review"
    RETENTION_COMPLIANCE = "retention_compliance"


class ReportFormat(Enum):
    """Report output formats."""
    PDF = "pdf"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HTML = "html"
    EXCEL = "excel"


@dataclass
class ReportMetadata:
    """Metadata for regulatory reports."""
    report_id: str
    framework: RegulatoryFramework
    report_type: ReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    generated_by: str
    approved_by: Optional[str] = None
    submission_deadline: Optional[datetime] = None
    submitted: bool = False
    submission_date: Optional[datetime] = None


@dataclass
class DataProcessingActivity:
    """GDPR Article 30 - Record of processing activities."""
    activity_id: str
    purpose: str
    legal_basis: str
    data_categories: List[str]
    data_subjects: List[str]
    recipients: List[str]
    international_transfers: List[str]
    retention_period: str
    security_measures: List[str]
    data_controller: str
    data_processor: Optional[str] = None
    dpo_contact: Optional[str] = None


@dataclass
class DataBreachIncident:
    """Data breach incident for notification."""
    incident_id: str
    discovery_date: datetime
    breach_date: datetime
    affected_records: int
    data_types: List[str]
    breach_type: str  # unauthorized access, theft, loss, etc.
    containment_date: Optional[datetime] = None
    notification_required: bool = True
    individuals_notified: bool = False
    authorities_notified: bool = False
    remediation_steps: List[str] = None


class RegulatoryReportGenerator:
    """Generates regulatory compliance reports."""
    
    def __init__(self, output_dir: str = "/var/reports/regulatory"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = Path(__file__).parent / "templates"
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize report templates."""
        if not self.templates_dir.exists():
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_templates()
        
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
    
    def _create_default_templates(self):
        """Create default report templates."""
        # HIPAA Breach Notification Template
        hipaa_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HIPAA Breach Notification Report</title>
            <style>
                body { font-family: Arial, sans-serif; }
                .header { background-color: #2c3e50; color: white; padding: 20px; }
                .section { margin: 20px; padding: 15px; border: 1px solid #ddd; }
                .critical { color: red; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>HIPAA Breach Notification Report</h1>
                <p>Report ID: {{ report_id }}</p>
                <p>Generated: {{ generated_date }}</p>
            </div>
            <div class="section">
                <h2>Incident Summary</h2>
                <p><strong>Incident ID:</strong> {{ incident.incident_id }}</p>
                <p><strong>Discovery Date:</strong> {{ incident.discovery_date }}</p>
                <p><strong>Affected Records:</strong> <span class="critical">{{ incident.affected_records }}</span></p>
                <p><strong>Data Types:</strong> {{ incident.data_types | join(', ') }}</p>
            </div>
            <div class="section">
                <h2>Notification Requirements</h2>
                <p>Individual Notification: {{ 'Required' if incident.notification_required else 'Not Required' }}</p>
                <p>HHS Notification: Required within 60 days</p>
                <p>Media Notification: {{ 'Required' if incident.affected_records > 500 else 'Not Required' }}</p>
            </div>
        </body>
        </html>
        """
        
        with open(self.templates_dir / "hipaa_breach.html", "w") as f:
            f.write(hipaa_template)
        
        # GDPR Data Processing Template
        gdpr_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>GDPR Processing Activities Record</title>
        </head>
        <body>
            <h1>Record of Processing Activities (Article 30)</h1>
            <table border="1">
                <tr>
                    <th>Activity ID</th>
                    <th>Purpose</th>
                    <th>Legal Basis</th>
                    <th>Data Categories</th>
                    <th>Retention</th>
                </tr>
                {% for activity in activities %}
                <tr>
                    <td>{{ activity.activity_id }}</td>
                    <td>{{ activity.purpose }}</td>
                    <td>{{ activity.legal_basis }}</td>
                    <td>{{ activity.data_categories | join(', ') }}</td>
                    <td>{{ activity.retention_period }}</td>
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """
        
        with open(self.templates_dir / "gdpr_processing.html", "w") as f:
            f.write(gdpr_template)
    
    async def generate_hipaa_breach_notification(
        self,
        incident: DataBreachIncident,
        format: ReportFormat = ReportFormat.PDF
    ) -> str:
        """Generate HIPAA breach notification report."""
        report_id = f"HIPAA-BREACH-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Determine notification requirements
        notification_timeline = self._calculate_hipaa_timeline(incident)
        
        report_data = {
            "report_id": report_id,
            "generated_date": datetime.utcnow().isoformat(),
            "incident": incident,
            "notification_timeline": notification_timeline,
            "risk_assessment": await self._perform_hipaa_risk_assessment(incident)
        }
        
        # Generate report in requested format
        if format == ReportFormat.PDF:
            output_path = await self._generate_pdf_report(
                "hipaa_breach",
                report_data,
                report_id
            )
        elif format == ReportFormat.HTML:
            output_path = await self._generate_html_report(
                "hipaa_breach.html",
                report_data,
                report_id
            )
        elif format == ReportFormat.JSON:
            output_path = await self._generate_json_report(
                report_data,
                report_id
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Log report generation
        logger.info(f"Generated HIPAA breach notification: {report_id}")
        
        # Schedule automatic submission if required
        if incident.affected_records > 500:
            await self._schedule_hhs_submission(report_id, output_path)
        
        return output_path
    
    def _calculate_hipaa_timeline(self, incident: DataBreachIncident) -> Dict[str, Any]:
        """Calculate HIPAA notification timeline."""
        discovery = incident.discovery_date
        
        timeline = {
            "individual_notification": discovery + timedelta(days=60),
            "hhs_notification": discovery + timedelta(days=60),
            "media_notification": None
        }
        
        # Media notification required for 500+ affected individuals
        if incident.affected_records >= 500:
            timeline["media_notification"] = discovery + timedelta(days=60)
        
        # Immediate notification for imminent misuse
        if "ssn" in incident.data_types or "financial" in incident.data_types:
            timeline["individual_notification"] = discovery + timedelta(days=5)
        
        return timeline
    
    async def _perform_hipaa_risk_assessment(
        self,
        incident: DataBreachIncident
    ) -> Dict[str, Any]:
        """Perform HIPAA risk assessment."""
        risk_factors = {
            "nature_extent": self._assess_nature_extent(incident),
            "unauthorized_person": self._assess_unauthorized_person(incident),
            "information_acquired": self._assess_information_acquired(incident),
            "mitigation": self._assess_mitigation(incident)
        }
        
        # Calculate overall risk level
        risk_score = sum(risk_factors.values()) / len(risk_factors)
        
        if risk_score < 0.3:
            risk_level = "low"
        elif risk_score < 0.7:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return {
            "risk_factors": risk_factors,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "notification_required": risk_level != "low"
        }
    
    def _assess_nature_extent(self, incident: DataBreachIncident) -> float:
        """Assess nature and extent of PHI involved."""
        score = 0.0
        
        # Type of PHI
        if "diagnosis" in incident.data_types:
            score += 0.3
        if "treatment" in incident.data_types:
            score += 0.3
        if "financial" in incident.data_types:
            score += 0.2
        if "demographics" in incident.data_types:
            score += 0.1
        
        # Amount of PHI
        if incident.affected_records > 10000:
            score += 0.3
        elif incident.affected_records > 1000:
            score += 0.2
        elif incident.affected_records > 100:
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_unauthorized_person(self, incident: DataBreachIncident) -> float:
        """Assess the unauthorized person who accessed PHI."""
        # In real implementation, would check actual breach details
        if incident.breach_type == "external_attack":
            return 0.9
        elif incident.breach_type == "unauthorized_access":
            return 0.6
        elif incident.breach_type == "loss":
            return 0.5
        else:
            return 0.3
    
    def _assess_information_acquired(self, incident: DataBreachIncident) -> float:
        """Assess whether PHI was actually acquired or viewed."""
        # In real implementation, would check logs and forensics
        if incident.breach_type in ["theft", "external_attack"]:
            return 0.9
        else:
            return 0.5
    
    def _assess_mitigation(self, incident: DataBreachIncident) -> float:
        """Assess mitigation measures."""
        if incident.containment_date:
            days_to_contain = (incident.containment_date - incident.discovery_date).days
            if days_to_contain <= 1:
                return 0.2
            elif days_to_contain <= 7:
                return 0.5
            else:
                return 0.8
        return 1.0
    
    async def generate_gdpr_processing_record(
        self,
        activities: List[DataProcessingActivity],
        format: ReportFormat = ReportFormat.PDF
    ) -> str:
        """Generate GDPR Article 30 processing activities record."""
        report_id = f"GDPR-RPA-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        report_data = {
            "report_id": report_id,
            "generated_date": datetime.utcnow().isoformat(),
            "activities": activities,
            "total_activities": len(activities),
            "data_categories": self._extract_unique_categories(activities),
            "international_transfers": self._analyze_transfers(activities)
        }
        
        # Generate report
        if format == ReportFormat.PDF:
            output_path = await self._generate_pdf_report(
                "gdpr_processing",
                report_data,
                report_id
            )
        elif format == ReportFormat.CSV:
            output_path = await self._generate_csv_report(
                activities,
                report_id
            )
        elif format == ReportFormat.EXCEL:
            output_path = await self._generate_excel_report(
                activities,
                report_id
            )
        else:
            output_path = await self._generate_html_report(
                "gdpr_processing.html",
                report_data,
                report_id
            )
        
        logger.info(f"Generated GDPR processing record: {report_id}")
        
        return output_path
    
    def _extract_unique_categories(
        self,
        activities: List[DataProcessingActivity]
    ) -> List[str]:
        """Extract unique data categories."""
        categories = set()
        for activity in activities:
            categories.update(activity.data_categories)
        return sorted(list(categories))
    
    def _analyze_transfers(
        self,
        activities: List[DataProcessingActivity]
    ) -> Dict[str, Any]:
        """Analyze international transfers."""
        transfers = {}
        for activity in activities:
            for country in activity.international_transfers:
                if country not in transfers:
                    transfers[country] = {
                        "activities": [],
                        "adequacy_decision": self._check_adequacy_decision(country)
                    }
                transfers[country]["activities"].append(activity.activity_id)
        
        return transfers
    
    def _check_adequacy_decision(self, country: str) -> bool:
        """Check if country has EU adequacy decision."""
        adequate_countries = [
            "Andorra", "Argentina", "Canada", "Faroe Islands",
            "Guernsey", "Israel", "Isle of Man", "Japan",
            "Jersey", "New Zealand", "Republic of Korea",
            "Switzerland", "United Kingdom", "Uruguay"
        ]
        return country in adequate_countries
    
    async def generate_pci_dss_compliance_report(
        self,
        assessment_data: Dict[str, Any],
        format: ReportFormat = ReportFormat.PDF
    ) -> str:
        """Generate PCI DSS compliance report."""
        report_id = f"PCI-DSS-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # PCI DSS requirements assessment
        requirements = self._assess_pci_requirements(assessment_data)
        
        report_data = {
            "report_id": report_id,
            "generated_date": datetime.utcnow().isoformat(),
            "merchant_level": assessment_data.get("merchant_level", "4"),
            "requirements": requirements,
            "compliance_status": all(r["compliant"] for r in requirements.values()),
            "scan_results": assessment_data.get("vulnerability_scans", []),
            "penetration_tests": assessment_data.get("penetration_tests", [])
        }
        
        # Generate SAQ (Self-Assessment Questionnaire)
        if format == ReportFormat.PDF:
            output_path = await self._generate_pci_saq_pdf(report_data, report_id)
        else:
            output_path = await self._generate_json_report(report_data, report_id)
        
        logger.info(f"Generated PCI DSS compliance report: {report_id}")
        
        return output_path
    
    def _assess_pci_requirements(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess PCI DSS requirements."""
        requirements = {}
        
        # Requirement 1: Firewall
        requirements["1"] = {
            "description": "Install and maintain a firewall configuration",
            "compliant": assessment_data.get("firewall_configured", False),
            "evidence": assessment_data.get("firewall_evidence", [])
        }
        
        # Requirement 2: Default passwords
        requirements["2"] = {
            "description": "Do not use vendor-supplied defaults",
            "compliant": assessment_data.get("defaults_changed", False),
            "evidence": assessment_data.get("password_evidence", [])
        }
        
        # Requirement 3: Protect cardholder data
        requirements["3"] = {
            "description": "Protect stored cardholder data",
            "compliant": assessment_data.get("data_encrypted", False),
            "evidence": assessment_data.get("encryption_evidence", [])
        }
        
        # Requirement 4: Encrypt transmission
        requirements["4"] = {
            "description": "Encrypt transmission of cardholder data",
            "compliant": assessment_data.get("transmission_encrypted", False),
            "evidence": assessment_data.get("tls_evidence", [])
        }
        
        # Additional requirements...
        
        return requirements
    
    async def generate_sox_compliance_report(
        self,
        controls_data: Dict[str, Any],
        format: ReportFormat = ReportFormat.PDF
    ) -> str:
        """Generate SOX compliance report."""
        report_id = f"SOX-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Assess SOX controls
        control_assessment = self._assess_sox_controls(controls_data)
        
        report_data = {
            "report_id": report_id,
            "generated_date": datetime.utcnow().isoformat(),
            "fiscal_year": controls_data.get("fiscal_year"),
            "control_assessment": control_assessment,
            "material_weaknesses": self._identify_material_weaknesses(control_assessment),
            "management_assertion": controls_data.get("management_assertion"),
            "auditor_opinion": controls_data.get("auditor_opinion")
        }
        
        # Generate report
        if format == ReportFormat.PDF:
            output_path = await self._generate_sox_pdf(report_data, report_id)
        else:
            output_path = await self._generate_json_report(report_data, report_id)
        
        logger.info(f"Generated SOX compliance report: {report_id}")
        
        return output_path
    
    def _assess_sox_controls(self, controls_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess SOX internal controls."""
        controls = {}
        
        # Entity-level controls
        controls["entity"] = {
            "control_environment": controls_data.get("control_environment", {}),
            "risk_assessment": controls_data.get("risk_assessment", {}),
            "information_communication": controls_data.get("information_communication", {}),
            "monitoring": controls_data.get("monitoring", {})
        }
        
        # IT general controls
        controls["it_general"] = {
            "access_controls": controls_data.get("access_controls", {}),
            "change_management": controls_data.get("change_management", {}),
            "operations": controls_data.get("operations", {}),
            "backup_recovery": controls_data.get("backup_recovery", {})
        }
        
        # Application controls
        controls["application"] = {
            "input_controls": controls_data.get("input_controls", {}),
            "processing_controls": controls_data.get("processing_controls", {}),
            "output_controls": controls_data.get("output_controls", {})
        }
        
        return controls
    
    def _identify_material_weaknesses(
        self,
        control_assessment: Dict[str, Any]
    ) -> List[str]:
        """Identify material weaknesses in controls."""
        weaknesses = []
        
        # Check for control deficiencies
        for category, controls in control_assessment.items():
            for control_name, control_data in controls.items():
                if isinstance(control_data, dict):
                    effectiveness = control_data.get("effectiveness", 0)
                    if effectiveness < 0.5:
                        weaknesses.append(f"{category}.{control_name}: Low effectiveness ({effectiveness})")
        
        return weaknesses
    
    async def _generate_pdf_report(
        self,
        template_name: str,
        data: Dict[str, Any],
        report_id: str
    ) -> str:
        """Generate PDF report."""
        output_path = self.output_dir / f"{report_id}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
        )
        
        story.append(Paragraph(f"Regulatory Compliance Report", title_style))
        story.append(Spacer(1, 12))
        
        # Report metadata
        story.append(Paragraph(f"<b>Report ID:</b> {report_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {data['generated_date']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Add content based on template
        if template_name == "hipaa_breach":
            story.extend(self._create_hipaa_pdf_content(data, styles))
        elif template_name == "gdpr_processing":
            story.extend(self._create_gdpr_pdf_content(data, styles))
        
        # Build PDF
        doc.build(story)
        
        return str(output_path)
    
    def _create_hipaa_pdf_content(
        self,
        data: Dict[str, Any],
        styles
    ) -> List:
        """Create HIPAA breach notification PDF content."""
        content = []
        
        # Incident details
        content.append(Paragraph("<b>Incident Details</b>", styles['Heading2']))
        
        incident = data['incident']
        incident_data = [
            ['Field', 'Value'],
            ['Incident ID', incident.incident_id],
            ['Discovery Date', str(incident.discovery_date)],
            ['Affected Records', str(incident.affected_records)],
            ['Data Types', ', '.join(incident.data_types)],
            ['Breach Type', incident.breach_type]
        ]
        
        table = Table(incident_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        content.append(Spacer(1, 12))
        
        # Risk assessment
        if 'risk_assessment' in data:
            content.append(Paragraph("<b>Risk Assessment</b>", styles['Heading2']))
            risk = data['risk_assessment']
            content.append(Paragraph(f"Risk Level: <b>{risk['risk_level'].upper()}</b>", styles['Normal']))
            content.append(Paragraph(f"Risk Score: {risk['risk_score']:.2f}", styles['Normal']))
            content.append(Paragraph(f"Notification Required: {'Yes' if risk['notification_required'] else 'No'}", styles['Normal']))
        
        return content
    
    def _create_gdpr_pdf_content(
        self,
        data: Dict[str, Any],
        styles
    ) -> List:
        """Create GDPR processing activities PDF content."""
        content = []
        
        content.append(Paragraph("<b>Processing Activities Record</b>", styles['Heading2']))
        content.append(Paragraph(f"Total Activities: {data['total_activities']}", styles['Normal']))
        content.append(Spacer(1, 12))
        
        # Activities table
        table_data = [['Activity ID', 'Purpose', 'Legal Basis', 'Retention']]
        
        for activity in data['activities']:
            table_data.append([
                activity.activity_id,
                activity.purpose[:30] + '...' if len(activity.purpose) > 30 else activity.purpose,
                activity.legal_basis,
                activity.retention_period
            ])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(table)
        
        return content
    
    async def _generate_html_report(
        self,
        template_name: str,
        data: Dict[str, Any],
        report_id: str
    ) -> str:
        """Generate HTML report."""
        template = self.jinja_env.get_template(template_name)
        html_content = template.render(**data)
        
        output_path = self.output_dir / f"{report_id}.html"
        with open(output_path, "w") as f:
            f.write(html_content)
        
        return str(output_path)
    
    async def _generate_json_report(
        self,
        data: Dict[str, Any],
        report_id: str
    ) -> str:
        """Generate JSON report."""
        output_path = self.output_dir / f"{report_id}.json"
        
        # Convert dataclasses to dicts
        serializable_data = self._make_serializable(data)
        
        with open(output_path, "w") as f:
            json.dump(serializable_data, f, indent=2, default=str)
        
        return str(output_path)
    
    def _make_serializable(self, obj: Any) -> Any:
        """Make object JSON serializable."""
        if hasattr(obj, '__dict__'):
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (datetime, timedelta)):
            return str(obj)
        else:
            return obj
    
    async def _generate_csv_report(
        self,
        data: List[Any],
        report_id: str
    ) -> str:
        """Generate CSV report."""
        output_path = self.output_dir / f"{report_id}.csv"
        
        if data and hasattr(data[0], '__dict__'):
            # Convert objects to dicts
            rows = [obj.__dict__ for obj in data]
            
            with open(output_path, "w", newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        return str(output_path)
    
    async def _generate_excel_report(
        self,
        data: List[Any],
        report_id: str
    ) -> str:
        """Generate Excel report."""
        output_path = self.output_dir / f"{report_id}.xlsx"
        
        if data and hasattr(data[0], '__dict__'):
            # Convert to DataFrame
            df = pd.DataFrame([obj.__dict__ for obj in data])
            
            # Write to Excel with formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Report', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['Report']
                for column in df:
                    column_width = max(df[column].astype(str).map(len).max(), len(column))
                    col_idx = df.columns.get_loc(column)
                    worksheet.column_dimensions[chr(65 + col_idx)].width = column_width
        
        return str(output_path)
    
    async def _generate_pci_saq_pdf(
        self,
        data: Dict[str, Any],
        report_id: str
    ) -> str:
        """Generate PCI DSS Self-Assessment Questionnaire PDF."""
        output_path = self.output_dir / f"{report_id}_SAQ.pdf"
        
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        story.append(Paragraph("PCI DSS Self-Assessment Questionnaire", styles['Title']))
        story.append(Spacer(1, 12))
        
        # Merchant information
        story.append(Paragraph(f"<b>Merchant Level:</b> {data['merchant_level']}", styles['Normal']))
        story.append(Paragraph(f"<b>Report Date:</b> {data['generated_date']}", styles['Normal']))
        story.append(Paragraph(f"<b>Compliance Status:</b> {'COMPLIANT' if data['compliance_status'] else 'NON-COMPLIANT'}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Requirements assessment
        story.append(Paragraph("<b>Requirements Assessment</b>", styles['Heading2']))
        
        for req_id, req_data in data['requirements'].items():
            story.append(Paragraph(f"Requirement {req_id}: {req_data['description']}", styles['Normal']))
            status = "✓ Compliant" if req_data['compliant'] else "✗ Non-Compliant"
            story.append(Paragraph(status, styles['Normal']))
            story.append(Spacer(1, 6))
        
        doc.build(story)
        
        return str(output_path)
    
    async def _generate_sox_pdf(
        self,
        data: Dict[str, Any],
        report_id: str
    ) -> str:
        """Generate SOX compliance PDF."""
        output_path = self.output_dir / f"{report_id}_SOX.pdf"
        
        doc = SimpleDocTemplate(str(output_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        story.append(Paragraph("SOX Compliance Report", styles['Title']))
        story.append(Paragraph(f"Fiscal Year: {data['fiscal_year']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Material weaknesses
        if data['material_weaknesses']:
            story.append(Paragraph("<b>Material Weaknesses Identified</b>", styles['Heading2']))
            for weakness in data['material_weaknesses']:
                story.append(Paragraph(f"• {weakness}", styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Management assertion
        if data.get('management_assertion'):
            story.append(Paragraph("<b>Management Assertion</b>", styles['Heading2']))
            story.append(Paragraph(data['management_assertion'], styles['Normal']))
        
        doc.build(story)
        
        return str(output_path)
    
    async def _schedule_hhs_submission(self, report_id: str, report_path: str):
        """Schedule automatic HHS breach notification submission."""
        # In production, would integrate with HHS breach reporting tool
        logger.info(f"Scheduled HHS submission for report {report_id}")
        
        # Create submission task
        asyncio.create_task(self._submit_to_hhs(report_id, report_path))
    
    async def _submit_to_hhs(self, report_id: str, report_path: str):
        """Submit breach notification to HHS."""
        # Wait for review period (in production, would be configurable)
        await asyncio.sleep(3600)  # 1 hour review period
        
        # In production, would use HHS API or secure file transfer
        logger.info(f"Submitting report {report_id} to HHS")
        
        # Mark as submitted
        submission_record = {
            "report_id": report_id,
            "submission_date": datetime.utcnow().isoformat(),
            "submission_method": "automated",
            "confirmation_number": str(uuid.uuid4())
        }
        
        # Store submission record
        submission_path = self.output_dir / f"{report_id}_submission.json"
        with open(submission_path, "w") as f:
            json.dump(submission_record, f, indent=2)


class RegulatoryReportScheduler:
    """Schedules and manages regulatory report generation."""
    
    def __init__(self, report_generator: RegulatoryReportGenerator):
        self.generator = report_generator
        self.scheduled_reports = {}
        self._start_scheduler()
    
    def _start_scheduler(self):
        """Start the report scheduling loop."""
        asyncio.create_task(self._scheduler_loop())
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while True:
            try:
                # Check for due reports
                current_time = datetime.utcnow()
                
                for report_id, schedule in list(self.scheduled_reports.items()):
                    if schedule['next_run'] <= current_time:
                        # Generate report
                        await self._generate_scheduled_report(report_id, schedule)
                        
                        # Update next run time
                        if schedule['frequency'] == 'daily':
                            schedule['next_run'] = current_time + timedelta(days=1)
                        elif schedule['frequency'] == 'weekly':
                            schedule['next_run'] = current_time + timedelta(weeks=1)
                        elif schedule['frequency'] == 'monthly':
                            schedule['next_run'] = current_time + timedelta(days=30)
                        elif schedule['frequency'] == 'quarterly':
                            schedule['next_run'] = current_time + timedelta(days=90)
                        elif schedule['frequency'] == 'annually':
                            schedule['next_run'] = current_time + timedelta(days=365)
                        else:
                            # One-time report
                            del self.scheduled_reports[report_id]
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(3600)
    
    async def _generate_scheduled_report(
        self,
        report_id: str,
        schedule: Dict[str, Any]
    ):
        """Generate a scheduled report."""
        try:
            framework = schedule['framework']
            report_type = schedule['report_type']
            
            logger.info(f"Generating scheduled report: {report_id}")
            
            # Generate report based on type
            if framework == RegulatoryFramework.HIPAA:
                # Generate HIPAA report
                pass
            elif framework == RegulatoryFramework.GDPR:
                # Generate GDPR report
                pass
            # ... other frameworks
            
            # Send notification
            await self._send_report_notification(report_id, schedule)
            
        except Exception as e:
            logger.error(f"Failed to generate scheduled report {report_id}: {e}")
    
    async def _send_report_notification(
        self,
        report_id: str,
        schedule: Dict[str, Any]
    ):
        """Send notification that report is ready."""
        if 'notification_email' in schedule:
            # Send email notification
            # In production, would use proper email service
            logger.info(f"Sending report notification to {schedule['notification_email']}")
    
    def schedule_report(
        self,
        framework: RegulatoryFramework,
        report_type: ReportType,
        frequency: str,
        start_date: datetime,
        **kwargs
    ) -> str:
        """Schedule a recurring regulatory report."""
        report_id = f"SCHED-{framework.value}-{uuid.uuid4().hex[:8]}"
        
        self.scheduled_reports[report_id] = {
            "framework": framework,
            "report_type": report_type,
            "frequency": frequency,
            "next_run": start_date,
            "created_at": datetime.utcnow(),
            **kwargs
        }
        
        logger.info(f"Scheduled report {report_id} - {frequency} starting {start_date}")
        
        return report_id