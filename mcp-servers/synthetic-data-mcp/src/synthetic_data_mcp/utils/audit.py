"""
Audit trail management for regulatory compliance.

This module provides comprehensive audit logging capabilities for tracking
all synthetic data generation activities and compliance validations.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class AuditTrail:
    """Comprehensive audit trail management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize audit trail system.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = "audit_trail.db"
        
        self.db_path = Path(db_path)
        self._init_database()
        
        logger.info(f"Audit trail initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize audit trail database."""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_operations (
                    id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    parameters TEXT,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    end_timestamp TEXT,
                    duration_seconds REAL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_validations (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    validation_timestamp TEXT NOT NULL,
                    passed BOOLEAN NOT NULL,
                    risk_score REAL NOT NULL,
                    violations TEXT,
                    recommendations TEXT,
                    FOREIGN KEY (operation_id) REFERENCES audit_operations (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS privacy_assessments (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    assessment_timestamp TEXT NOT NULL,
                    privacy_level TEXT NOT NULL,
                    epsilon REAL,
                    risk_score REAL NOT NULL,
                    techniques_applied TEXT,
                    privacy_budget_used REAL,
                    FOREIGN KEY (operation_id) REFERENCES audit_operations (id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_operations_timestamp 
                ON audit_operations (timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_operations_user 
                ON audit_operations (user_id)
            """)
    
    def start_operation(
        self,
        operation: str,
        parameters: Dict[str, Any],
        user_id: str = "system",
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Start tracking an operation.
        
        Args:
            operation: Type of operation being performed
            parameters: Operation parameters
            user_id: User performing the operation
            timestamp: Operation start timestamp
            
        Returns:
            Unique audit ID for this operation
        """
        
        audit_id = str(uuid.uuid4())
        
        if timestamp is None:
            timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO audit_operations 
                (id, operation_type, user_id, timestamp, parameters, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                audit_id,
                operation,
                user_id,
                timestamp.isoformat(),
                json.dumps(parameters, default=str),
                "in_progress"
            ))
        
        logger.info(f"Started audit trail for operation: {operation} (ID: {audit_id})")
        return audit_id
    
    def complete_operation(
        self,
        audit_id: str,
        result: str = "success",
        end_time: Optional[datetime] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Complete an operation audit trail.
        
        Args:
            audit_id: Audit ID from start_operation
            result: Operation result (success/failure)
            end_time: Operation end time
            error: Error message if applicable
            metadata: Additional metadata about the operation
        """
        
        if end_time is None:
            end_time = datetime.now()
        
        # Calculate duration
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp FROM audit_operations WHERE id = ?
            """, (audit_id,))
            
            row = cursor.fetchone()
            if row:
                start_time = datetime.fromisoformat(row[0])
                duration = (end_time - start_time).total_seconds()
            else:
                duration = 0.0
            
            # Update operation record
            conn.execute("""
                UPDATE audit_operations 
                SET status = ?, result = ?, error = ?, end_timestamp = ?, 
                    duration_seconds = ?, metadata = ?
                WHERE id = ?
            """, (
                result,
                json.dumps({"status": result}, default=str),
                error,
                end_time.isoformat(),
                duration,
                json.dumps(metadata or {}, default=str),
                audit_id
            ))
        
        logger.info(f"Completed audit trail: {audit_id} ({result})")
    
    def log_compliance_validation(
        self,
        operation_id: str,
        framework: str,
        passed: bool,
        risk_score: float,
        violations: List[Dict[str, Any]] = None,
        recommendations: List[str] = None
    ):
        """
        Log compliance validation results.
        
        Args:
            operation_id: Associated operation audit ID
            framework: Compliance framework validated
            passed: Whether validation passed
            risk_score: Compliance risk score
            violations: List of violations found
            recommendations: List of recommendations
        """
        
        validation_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO compliance_validations
                (id, operation_id, framework, validation_timestamp, passed,
                 risk_score, violations, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                validation_id,
                operation_id,
                framework,
                datetime.now().isoformat(),
                passed,
                risk_score,
                json.dumps(violations or [], default=str),
                json.dumps(recommendations or [], default=str)
            ))
        
        logger.info(f"Logged compliance validation: {framework} ({'PASSED' if passed else 'FAILED'})")
    
    def log_privacy_assessment(
        self,
        operation_id: str,
        privacy_level: str,
        epsilon: Optional[float],
        risk_score: float,
        techniques_applied: List[str],
        privacy_budget_used: float = 0.0
    ):
        """
        Log privacy assessment results.
        
        Args:
            operation_id: Associated operation audit ID
            privacy_level: Privacy protection level applied
            epsilon: Differential privacy epsilon value
            risk_score: Privacy risk score
            techniques_applied: List of privacy techniques used
            privacy_budget_used: Amount of privacy budget consumed
        """
        
        assessment_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO privacy_assessments
                (id, operation_id, assessment_timestamp, privacy_level,
                 epsilon, risk_score, techniques_applied, privacy_budget_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assessment_id,
                operation_id,
                datetime.now().isoformat(),
                privacy_level,
                epsilon,
                risk_score,
                json.dumps(techniques_applied, default=str),
                privacy_budget_used
            ))
        
        logger.info(f"Logged privacy assessment: {privacy_level} (Risk: {risk_score:.4f})")
    
    def get_operation_history(
        self,
        user_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve operation history with optional filtering.
        
        Args:
            user_id: Filter by user ID
            operation_type: Filter by operation type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of records to return
            
        Returns:
            List of operation records
        """
        
        query = "SELECT * FROM audit_operations WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if operation_type:
            query += " AND operation_type = ?"
            params.append(operation_type)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            operations = []
            for row in cursor.fetchall():
                operation = dict(row)
                
                # Parse JSON fields
                if operation['parameters']:
                    operation['parameters'] = json.loads(operation['parameters'])
                if operation['result']:
                    operation['result'] = json.loads(operation['result'])
                if operation['metadata']:
                    operation['metadata'] = json.loads(operation['metadata'])
                
                operations.append(operation)
            
            return operations
    
    def get_compliance_history(
        self,
        operation_id: Optional[str] = None,
        framework: Optional[str] = None,
        passed: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve compliance validation history.
        
        Args:
            operation_id: Filter by operation ID
            framework: Filter by compliance framework
            passed: Filter by pass/fail status
            
        Returns:
            List of compliance validation records
        """
        
        query = "SELECT * FROM compliance_validations WHERE 1=1"
        params = []
        
        if operation_id:
            query += " AND operation_id = ?"
            params.append(operation_id)
        
        if framework:
            query += " AND framework = ?"
            params.append(framework)
        
        if passed is not None:
            query += " AND passed = ?"
            params.append(passed)
        
        query += " ORDER BY validation_timestamp DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            validations = []
            for row in cursor.fetchall():
                validation = dict(row)
                
                # Parse JSON fields
                if validation['violations']:
                    validation['violations'] = json.loads(validation['violations'])
                if validation['recommendations']:
                    validation['recommendations'] = json.loads(validation['recommendations'])
                
                validations.append(validation)
            
            return validations
    
    def generate_compliance_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.
        
        Args:
            start_date: Report start date
            end_date: Report end date
            
        Returns:
            Compliance report with statistics and summaries
        """
        
        # Base date filters
        date_filter = "WHERE 1=1"
        date_params = []
        
        if start_date:
            date_filter += " AND validation_timestamp >= ?"
            date_params.append(start_date.isoformat())
        
        if end_date:
            date_filter += " AND validation_timestamp <= ?"
            date_params.append(end_date.isoformat())
        
        with sqlite3.connect(self.db_path) as conn:
            # Overall compliance statistics
            cursor = conn.execute(f"""
                SELECT framework, 
                       COUNT(*) as total_validations,
                       SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passed_validations,
                       AVG(risk_score) as avg_risk_score,
                       MAX(risk_score) as max_risk_score
                FROM compliance_validations 
                {date_filter}
                GROUP BY framework
            """, date_params)
            
            framework_stats = {}
            for row in cursor.fetchall():
                framework, total, passed, avg_risk, max_risk = row
                framework_stats[framework] = {
                    "total_validations": total,
                    "passed_validations": passed,
                    "pass_rate": passed / total if total > 0 else 0.0,
                    "avg_risk_score": avg_risk or 0.0,
                    "max_risk_score": max_risk or 0.0
                }
            
            # Recent violations
            cursor = conn.execute(f"""
                SELECT framework, violations, validation_timestamp
                FROM compliance_validations 
                {date_filter} AND passed = 0
                ORDER BY validation_timestamp DESC
                LIMIT 10
            """, date_params)
            
            recent_violations = []
            for row in cursor.fetchall():
                framework, violations_json, timestamp = row
                violations = json.loads(violations_json) if violations_json else []
                
                recent_violations.append({
                    "framework": framework,
                    "violations": violations,
                    "timestamp": timestamp
                })
            
            # Generate summary
            total_validations = sum(stats["total_validations"] for stats in framework_stats.values())
            total_passed = sum(stats["passed_validations"] for stats in framework_stats.values())
            overall_pass_rate = total_passed / total_validations if total_validations > 0 else 0.0
            
            report = {
                "report_generated": datetime.now().isoformat(),
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_validations": total_validations,
                    "total_passed": total_passed,
                    "overall_pass_rate": overall_pass_rate,
                    "frameworks_covered": list(framework_stats.keys())
                },
                "framework_statistics": framework_stats,
                "recent_violations": recent_violations,
                "compliance_status": "COMPLIANT" if overall_pass_rate > 0.95 else "NON_COMPLIANT"
            }
            
            return report
    
    def export_audit_data(
        self,
        export_format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        Export audit data for regulatory submissions.
        
        Args:
            export_format: Export format (json, csv)
            start_date: Export start date
            end_date: Export end date
            
        Returns:
            Exported data as string
        """
        
        operations = self.get_operation_history(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        compliance_history = self.get_compliance_history()
        
        export_data = {
            "export_metadata": {
                "generated_at": datetime.now().isoformat(),
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
                "total_operations": len(operations),
                "total_compliance_validations": len(compliance_history)
            },
            "operations": operations,
            "compliance_validations": compliance_history
        }
        
        if export_format == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif export_format == "csv":
            # Simple CSV export (would need pandas for better formatting)
            csv_lines = ["timestamp,operation_type,user_id,status,duration_seconds"]
            
            for op in operations:
                csv_lines.append(f"{op['timestamp']},{op['operation_type']},{op['user_id']},{op['status']},{op.get('duration_seconds', 0)}")
            
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def cleanup_old_records(self, retention_days: int = 90):
        """
        Clean up audit records older than specified retention period.
        
        Args:
            retention_days: Number of days to retain records
        """
        
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old compliance validations first (foreign key constraint)
            cursor = conn.execute("""
                DELETE FROM compliance_validations 
                WHERE operation_id IN (
                    SELECT id FROM audit_operations 
                    WHERE timestamp < ?
                )
            """, (cutoff_date.isoformat(),))
            
            compliance_deleted = cursor.rowcount
            
            # Delete old privacy assessments
            cursor = conn.execute("""
                DELETE FROM privacy_assessments 
                WHERE operation_id IN (
                    SELECT id FROM audit_operations 
                    WHERE timestamp < ?
                )
            """, (cutoff_date.isoformat(),))
            
            privacy_deleted = cursor.rowcount
            
            # Delete old operations
            cursor = conn.execute("""
                DELETE FROM audit_operations WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            operations_deleted = cursor.rowcount
            
            logger.info(
                f"Cleaned up audit records: {operations_deleted} operations, "
                f"{compliance_deleted} compliance validations, "
                f"{privacy_deleted} privacy assessments"
            )