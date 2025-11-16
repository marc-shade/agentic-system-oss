#!/usr/bin/env python3
"""
Clone Success Tracker for Enhanced Memory MCP
Provides specialized tracking for design clone operations, success metrics, and learning insights.
Integrates with the existing Enhanced-Memory-MCP architecture.
"""

import json
import sqlite3
import hashlib
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger("enhanced-memory.clone-tracker")

class CloneSuccessTracker:
    """Manages tracking and analysis of design clone operations and success metrics"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_clone_tracking_tables()
    
    def init_clone_tracking_tables(self):
        """Initialize clone success tracking database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Clone operations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_name TEXT NOT NULL,
                    source_url TEXT,
                    target_description TEXT NOT NULL,
                    clone_type TEXT NOT NULL,
                    design_category TEXT,
                    complexity_level TEXT,
                    techniques_used TEXT,
                    tools_used TEXT,
                    time_to_completion_minutes INTEGER,
                    quality_score REAL DEFAULT 0.0,
                    accuracy_score REAL DEFAULT 0.0,
                    user_satisfaction REAL DEFAULT 0.0,
                    iteration_count INTEGER DEFAULT 1,
                    final_success BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Before/after comparisons
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clone_operation_id INTEGER,
                    comparison_type TEXT NOT NULL,
                    source_characteristics TEXT,
                    result_characteristics TEXT,
                    similarity_score REAL DEFAULT 0.0,
                    differences_noted TEXT,
                    improvement_suggestions TEXT,
                    comparison_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (clone_operation_id) REFERENCES clone_operations (id)
                )
            ''')
            
            # Clone techniques effectiveness
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_techniques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technique_name TEXT UNIQUE NOT NULL,
                    technique_category TEXT NOT NULL,
                    success_rate REAL DEFAULT 0.0,
                    avg_time_reduction REAL DEFAULT 0.0,
                    complexity_effectiveness TEXT,
                    best_use_cases TEXT,
                    limitations TEXT,
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Clone operation steps and iterations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_iterations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clone_operation_id INTEGER,
                    iteration_number INTEGER NOT NULL,
                    step_description TEXT NOT NULL,
                    techniques_applied TEXT,
                    time_spent_minutes INTEGER,
                    success_score REAL DEFAULT 0.0,
                    challenges_encountered TEXT,
                    solutions_applied TEXT,
                    iteration_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (clone_operation_id) REFERENCES clone_operations (id)
                )
            ''')
            
            # User feedback and learning insights
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clone_operation_id INTEGER,
                    feedback_type TEXT NOT NULL,
                    feedback_score REAL,
                    feedback_text TEXT,
                    improvement_areas TEXT,
                    success_factors TEXT,
                    would_recommend BOOLEAN,
                    learning_insights TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (clone_operation_id) REFERENCES clone_operations (id)
                )
            ''')
            
            # Cross-project intelligence and patterns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clone_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    source_characteristics TEXT,
                    successful_techniques TEXT,
                    common_challenges TEXT,
                    success_predictors TEXT,
                    avg_success_rate REAL DEFAULT 0.0,
                    usage_frequency INTEGER DEFAULT 0,
                    pattern_confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clone_ops_type ON clone_operations(clone_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clone_ops_category ON clone_operations(design_category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clone_ops_success ON clone_operations(final_success)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clone_ops_quality ON clone_operations(quality_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_comparisons_clone_id ON clone_comparisons(clone_operation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_iterations_clone_id ON clone_iterations(clone_operation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_clone_id ON clone_feedback(clone_operation_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_techniques_success ON clone_techniques(success_rate)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_type ON clone_patterns(pattern_type)')
            
            conn.commit()
            logger.info("🎯 Clone success tracking tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize clone tracking tables: {e}")
            raise
        finally:
            conn.close()
    
    def start_clone_operation(self, operation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start tracking a new clone operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            operation_name = operation_data.get("operation_name", f"Clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            source_url = operation_data.get("source_url", "")
            target_description = operation_data.get("target_description", "")
            clone_type = operation_data.get("clone_type", "design_replication")
            design_category = operation_data.get("design_category", "general")
            complexity_level = operation_data.get("complexity_level", "medium")
            techniques_used = json.dumps(operation_data.get("techniques_used", []))
            tools_used = json.dumps(operation_data.get("tools_used", []))
            metadata = json.dumps(operation_data.get("metadata", {}))
            
            # Insert clone operation
            cursor.execute('''
                INSERT INTO clone_operations 
                (operation_name, source_url, target_description, clone_type, design_category,
                 complexity_level, techniques_used, tools_used, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (operation_name, source_url, target_description, clone_type, design_category,
                  complexity_level, techniques_used, tools_used, metadata))
            
            clone_operation_id = cursor.lastrowid
            
            # Store as entity in main memory system for searchability
            entity_data = {
                "name": f"CloneOperation_{operation_name}",
                "entityType": "clone_operation",
                "observations": [
                    f"Clone type: {clone_type}",
                    f"Design category: {design_category}",
                    f"Complexity level: {complexity_level}",
                    f"Target: {target_description}",
                    f"Source URL: {source_url}",
                    f"Techniques: {json.dumps(operation_data.get('techniques_used', []))}",
                    f"Tools: {json.dumps(operation_data.get('tools_used', []))}"
                ]
            }
            
            # Store in main entities table for integration
            from server import create_entities
            create_entities({"entities": [entity_data]})
            
            conn.commit()
            
            result = {
                "success": True,
                "clone_operation_id": clone_operation_id,
                "operation_name": operation_name,
                "started_at": datetime.now().isoformat(),
                "integration": "stored_in_main_memory_system"
            }
            
            logger.info(f"🎯 Started clone operation: {operation_name} (ID: {clone_operation_id})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to start clone operation: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def track_clone_iteration(self, clone_operation_id: int, iteration_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track an iteration/step in the clone operation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current iteration count
            cursor.execute('''
                SELECT COALESCE(MAX(iteration_number), 0) + 1
                FROM clone_iterations WHERE clone_operation_id = ?
            ''', (clone_operation_id,))
            
            iteration_number = cursor.fetchone()[0]
            
            # Insert iteration record
            cursor.execute('''
                INSERT INTO clone_iterations 
                (clone_operation_id, iteration_number, step_description, techniques_applied,
                 time_spent_minutes, success_score, challenges_encountered, solutions_applied,
                 iteration_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                clone_operation_id,
                iteration_number,
                iteration_data.get("step_description", ""),
                json.dumps(iteration_data.get("techniques_applied", [])),
                iteration_data.get("time_spent_minutes", 0),
                iteration_data.get("success_score", 0.0),
                iteration_data.get("challenges_encountered", ""),
                iteration_data.get("solutions_applied", ""),
                iteration_data.get("iteration_result", "")
            ))
            
            # Update main operation iteration count
            cursor.execute('''
                UPDATE clone_operations 
                SET iteration_count = ?
                WHERE id = ?
            ''', (iteration_number, clone_operation_id))
            
            conn.commit()
            
            return {
                "success": True,
                "clone_operation_id": clone_operation_id,
                "iteration_number": iteration_number,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track clone iteration: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def complete_clone_operation(self, clone_operation_id: int, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark a clone operation as complete and record final metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update completion data
            cursor.execute('''
                UPDATE clone_operations 
                SET time_to_completion_minutes = ?,
                    quality_score = ?,
                    accuracy_score = ?,
                    user_satisfaction = ?,
                    final_success = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                completion_data.get("time_to_completion_minutes", 0),
                completion_data.get("quality_score", 0.0),
                completion_data.get("accuracy_score", 0.0),
                completion_data.get("user_satisfaction", 0.0),
                completion_data.get("final_success", False),
                clone_operation_id
            ))
            
            # Store before/after comparison if provided
            if completion_data.get("comparison_data"):
                comparison = completion_data["comparison_data"]
                cursor.execute('''
                    INSERT INTO clone_comparisons 
                    (clone_operation_id, comparison_type, source_characteristics,
                     result_characteristics, similarity_score, differences_noted,
                     improvement_suggestions, comparison_metrics)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    clone_operation_id,
                    comparison.get("comparison_type", "visual"),
                    json.dumps(comparison.get("source_characteristics", {})),
                    json.dumps(comparison.get("result_characteristics", {})),
                    comparison.get("similarity_score", 0.0),
                    comparison.get("differences_noted", ""),
                    comparison.get("improvement_suggestions", ""),
                    json.dumps(comparison.get("comparison_metrics", {}))
                ))
            
            # Update technique effectiveness based on this operation
            techniques_used = completion_data.get("techniques_used", [])
            success_score = completion_data.get("quality_score", 0.0)
            
            for technique in techniques_used:
                self._update_technique_effectiveness(cursor, technique, success_score)
            
            # Generate and store learning patterns
            self._analyze_and_store_patterns(cursor, clone_operation_id, completion_data)
            
            conn.commit()
            
            # Get final operation summary
            cursor.execute('''
                SELECT operation_name, clone_type, design_category, quality_score, 
                       accuracy_score, time_to_completion_minutes, final_success
                FROM clone_operations WHERE id = ?
            ''', (clone_operation_id,))
            
            operation_summary = cursor.fetchone()
            
            result = {
                "success": True,
                "clone_operation_id": clone_operation_id,
                "operation_name": operation_summary[0] if operation_summary else "",
                "clone_type": operation_summary[1] if operation_summary else "",
                "design_category": operation_summary[2] if operation_summary else "",
                "final_metrics": {
                    "quality_score": operation_summary[3] if operation_summary else 0.0,
                    "accuracy_score": operation_summary[4] if operation_summary else 0.0,
                    "time_to_completion": operation_summary[5] if operation_summary else 0,
                    "final_success": operation_summary[6] if operation_summary else False
                },
                "completed_at": datetime.now().isoformat()
            }
            
            logger.info(f"🎯 Completed clone operation ID {clone_operation_id} with quality score {result['final_metrics']['quality_score']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to complete clone operation: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_clone_success_metrics(self, time_period: str = "30days") -> Dict[str, Any]:
        """Get comprehensive clone success metrics and analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Convert time period to SQL
            time_filter = {
                "7days": "datetime('now', '-7 days')",
                "30days": "datetime('now', '-30 days')",
                "90days": "datetime('now', '-90 days')",
                "1year": "datetime('now', '-1 year')"
            }.get(time_period, "datetime('now', '-30 days')")
            
            # Overall success metrics
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_operations,
                    SUM(CASE WHEN final_success = 1 THEN 1 ELSE 0 END) as successful_operations,
                    AVG(quality_score) as avg_quality_score,
                    AVG(accuracy_score) as avg_accuracy_score,
                    AVG(user_satisfaction) as avg_user_satisfaction,
                    AVG(time_to_completion_minutes) as avg_completion_time,
                    AVG(iteration_count) as avg_iterations
                FROM clone_operations
                WHERE created_at > {time_filter}
            ''')
            
            overall_stats = cursor.fetchone()
            total_ops, successful_ops, avg_quality, avg_accuracy, avg_satisfaction, avg_time, avg_iterations = overall_stats
            
            # Success rate by clone type
            cursor.execute(f'''
                SELECT 
                    clone_type,
                    COUNT(*) as operations,
                    SUM(CASE WHEN final_success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(quality_score) as avg_quality,
                    AVG(time_to_completion_minutes) as avg_time
                FROM clone_operations
                WHERE created_at > {time_filter}
                GROUP BY clone_type
                ORDER BY operations DESC
            ''')
            
            type_performance = []
            for row in cursor.fetchall():
                clone_type, ops, successes, quality, time = row
                success_rate = (successes / ops * 100) if ops > 0 else 0
                type_performance.append({
                    "clone_type": clone_type,
                    "operations": ops,
                    "success_rate": success_rate,
                    "avg_quality_score": quality or 0.0,
                    "avg_completion_time": time or 0.0
                })
            
            # Success rate by design category
            cursor.execute(f'''
                SELECT 
                    design_category,
                    COUNT(*) as operations,
                    SUM(CASE WHEN final_success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(quality_score) as avg_quality
                FROM clone_operations
                WHERE created_at > {time_filter}
                GROUP BY design_category
                ORDER BY operations DESC
            ''')
            
            category_performance = []
            for row in cursor.fetchall():
                category, ops, successes, quality = row
                success_rate = (successes / ops * 100) if ops > 0 else 0
                category_performance.append({
                    "design_category": category,
                    "operations": ops,
                    "success_rate": success_rate,
                    "avg_quality_score": quality or 0.0
                })
            
            # Top performing techniques
            cursor.execute('''
                SELECT technique_name, success_rate, usage_count, avg_time_reduction
                FROM clone_techniques
                WHERE usage_count > 0
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT 10
            ''')
            
            top_techniques = []
            for row in cursor.fetchall():
                top_techniques.append({
                    "technique_name": row[0],
                    "success_rate": row[1],
                    "usage_count": row[2],
                    "avg_time_reduction": row[3]
                })
            
            # Recent improvements trend
            cursor.execute(f'''
                SELECT DATE(created_at) as date, AVG(quality_score) as avg_quality, COUNT(*) as operations
                FROM clone_operations
                WHERE created_at > {time_filter}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            
            quality_trends = []
            for row in cursor.fetchall():
                quality_trends.append({
                    "date": row[0],
                    "avg_quality": row[1],
                    "operations": row[2]
                })
            
            # Calculate overall success rate
            overall_success_rate = (successful_ops / total_ops * 100) if total_ops > 0 else 0
            
            return {
                "success": True,
                "time_period": time_period,
                "overall_metrics": {
                    "total_operations": total_ops or 0,
                    "successful_operations": successful_ops or 0,
                    "overall_success_rate": overall_success_rate,
                    "avg_quality_score": avg_quality or 0.0,
                    "avg_accuracy_score": avg_accuracy or 0.0,
                    "avg_user_satisfaction": avg_satisfaction or 0.0,
                    "avg_completion_time_minutes": avg_time or 0.0,
                    "avg_iterations": avg_iterations or 0.0
                },
                "performance_by_type": type_performance,
                "performance_by_category": category_performance,
                "top_techniques": top_techniques,
                "quality_trends": quality_trends,
                "insights": self._generate_success_insights(
                    overall_success_rate, type_performance, category_performance, top_techniques
                ),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get clone success metrics: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_technique_recommendations(self, clone_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get technique recommendations based on clone context and historical success"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            clone_type = clone_context.get("clone_type", "")
            design_category = clone_context.get("design_category", "")
            complexity_level = clone_context.get("complexity_level", "medium")
            
            # Get techniques that have worked well for similar contexts
            cursor.execute('''
                SELECT DISTINCT ct.technique_name, ct.success_rate, ct.avg_time_reduction,
                       ct.complexity_effectiveness, ct.best_use_cases, ct.usage_count
                FROM clone_techniques ct
                WHERE ct.usage_count > 0 AND ct.success_rate > 0.5
                ORDER BY ct.success_rate DESC, ct.usage_count DESC
            ''')
            
            all_techniques = []
            for row in cursor.fetchall():
                technique_name, success_rate, time_reduction, complexity_eff, use_cases, usage_count = row
                
                # Parse JSON data safely
                try:
                    complexity_effectiveness = json.loads(complexity_eff) if complexity_eff else {}
                    best_use_cases = json.loads(use_cases) if use_cases else []
                except json.JSONDecodeError:
                    complexity_effectiveness = {}
                    best_use_cases = []
                
                # Calculate relevance score
                relevance_score = self._calculate_technique_relevance(
                    clone_context, technique_name, complexity_effectiveness, best_use_cases
                )
                
                all_techniques.append({
                    "technique_name": technique_name,
                    "success_rate": success_rate,
                    "avg_time_reduction": time_reduction,
                    "complexity_effectiveness": complexity_effectiveness,
                    "best_use_cases": best_use_cases,
                    "usage_count": usage_count,
                    "relevance_score": relevance_score,
                    "recommendation_reason": self._generate_technique_recommendation_reason(
                        clone_context, technique_name, success_rate, complexity_effectiveness
                    )
                })
            
            # Sort by combined relevance and success rate
            recommendations = sorted(
                all_techniques,
                key=lambda x: (x["relevance_score"] * 0.4 + x["success_rate"] * 0.6),
                reverse=True
            )[:10]
            
            # Get historical context patterns
            cursor.execute('''
                SELECT pattern_name, successful_techniques, avg_success_rate, pattern_confidence
                FROM clone_patterns
                WHERE pattern_type = ? OR pattern_type = 'general'
                ORDER BY pattern_confidence DESC, avg_success_rate DESC
                LIMIT 5
            ''', (clone_type,))
            
            relevant_patterns = []
            for row in cursor.fetchall():
                try:
                    successful_techniques = json.loads(row[1]) if row[1] else []
                except json.JSONDecodeError:
                    successful_techniques = []
                
                relevant_patterns.append({
                    "pattern_name": row[0],
                    "successful_techniques": successful_techniques,
                    "avg_success_rate": row[2],
                    "pattern_confidence": row[3]
                })
            
            return {
                "success": True,
                "clone_context": clone_context,
                "technique_recommendations": recommendations,
                "relevant_patterns": relevant_patterns,
                "recommendation_strategy": self._generate_recommendation_strategy(
                    clone_context, recommendations, relevant_patterns
                ),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get technique recommendations: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _update_technique_effectiveness(self, cursor, technique_name: str, success_score: float):
        """Update technique effectiveness based on operation results"""
        # Get or create technique record
        cursor.execute('SELECT id, success_rate, usage_count FROM clone_techniques WHERE technique_name = ?', (technique_name,))
        result = cursor.fetchone()
        
        if result:
            technique_id, current_success_rate, usage_count = result
            # Update with weighted average
            new_success_rate = (current_success_rate * usage_count + success_score) / (usage_count + 1)
            new_usage_count = usage_count + 1
            
            cursor.execute('''
                UPDATE clone_techniques 
                SET success_rate = ?, usage_count = ?, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_success_rate, new_usage_count, technique_id))
        else:
            # Create new technique record
            cursor.execute('''
                INSERT INTO clone_techniques 
                (technique_name, technique_category, success_rate, usage_count)
                VALUES (?, ?, ?, ?)
            ''', (technique_name, "general", success_score, 1))
    
    def _analyze_and_store_patterns(self, cursor, clone_operation_id: int, completion_data: Dict[str, Any]):
        """Analyze operation results and store/update patterns"""
        # Get operation details
        cursor.execute('''
            SELECT clone_type, design_category, techniques_used, quality_score, final_success
            FROM clone_operations WHERE id = ?
        ''', (clone_operation_id,))
        
        result = cursor.fetchone()
        if not result:
            return
        
        clone_type, design_category, techniques_used_json, quality_score, final_success = result
        
        try:
            techniques_used = json.loads(techniques_used_json) if techniques_used_json else []
        except json.JSONDecodeError:
            techniques_used = []
        
        # Create or update pattern
        pattern_name = f"{clone_type}_{design_category}_pattern"
        
        cursor.execute('SELECT id, avg_success_rate, usage_frequency FROM clone_patterns WHERE pattern_name = ?', (pattern_name,))
        pattern_result = cursor.fetchone()
        
        if pattern_result:
            pattern_id, current_avg, usage_freq = pattern_result
            new_avg = (current_avg * usage_freq + quality_score) / (usage_freq + 1)
            new_usage_freq = usage_freq + 1
            
            cursor.execute('''
                UPDATE clone_patterns 
                SET avg_success_rate = ?, usage_frequency = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_avg, new_usage_freq, pattern_id))
        else:
            cursor.execute('''
                INSERT INTO clone_patterns 
                (pattern_name, pattern_type, successful_techniques, avg_success_rate, usage_frequency, pattern_confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (pattern_name, clone_type, json.dumps(techniques_used), quality_score, 1, min(quality_score, 0.8)))
    
    def _calculate_technique_relevance(self, context: Dict[str, Any], technique_name: str,
                                     complexity_effectiveness: Dict[str, Any], 
                                     best_use_cases: List[str]) -> float:
        """Calculate how relevant a technique is to the given context"""
        relevance = 0.0
        
        # Context matching
        clone_type = context.get("clone_type", "").lower()
        design_category = context.get("design_category", "").lower()
        complexity_level = context.get("complexity_level", "medium").lower()
        
        # Check if technique name contains context keywords
        technique_lower = technique_name.lower()
        if clone_type in technique_lower or design_category in technique_lower:
            relevance += 0.3
        
        # Complexity effectiveness matching
        if complexity_level in complexity_effectiveness:
            effectiveness = complexity_effectiveness[complexity_level]
            if isinstance(effectiveness, (int, float)):
                relevance += min(effectiveness / 10.0, 0.4)  # Normalize to 0.4 max
        
        # Use case matching
        for use_case in best_use_cases:
            use_case_lower = use_case.lower()
            if clone_type in use_case_lower or design_category in use_case_lower:
                relevance += 0.2
                break
        
        # Base technique popularity
        relevance += 0.1  # Base score for any technique
        
        return min(relevance, 1.0)
    
    def _generate_technique_recommendation_reason(self, context: Dict[str, Any], 
                                                technique_name: str, success_rate: float,
                                                complexity_effectiveness: Dict[str, Any]) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if success_rate > 0.8:
            reasons.append(f"High success rate ({success_rate:.1%})")
        
        complexity_level = context.get("complexity_level", "medium")
        if complexity_level in complexity_effectiveness:
            reasons.append(f"Effective for {complexity_level} complexity projects")
        
        clone_type = context.get("clone_type", "")
        if clone_type.lower() in technique_name.lower():
            reasons.append(f"Specifically designed for {clone_type}")
        
        if not reasons:
            reasons.append("Proven technique with consistent results")
        
        return "; ".join(reasons)
    
    def _generate_recommendation_strategy(self, context: Dict[str, Any],
                                        recommendations: List[Dict[str, Any]],
                                        patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate an overall recommendation strategy"""
        strategy = {
            "primary_techniques": recommendations[:3],
            "fallback_techniques": recommendations[3:6] if len(recommendations) > 3 else [],
            "estimated_success_probability": 0.0,
            "recommended_approach": "",
            "key_considerations": []
        }
        
        if recommendations:
            # Calculate estimated success probability
            top_3_success_rates = [rec["success_rate"] for rec in recommendations[:3]]
            strategy["estimated_success_probability"] = statistics.mean(top_3_success_rates)
            
            # Generate approach recommendation
            complexity = context.get("complexity_level", "medium")
            if complexity == "low":
                strategy["recommended_approach"] = "Start with the highest-rated technique and iterate quickly"
            elif complexity == "high":
                strategy["recommended_approach"] = "Use multiple techniques in combination, expect more iterations"
            else:
                strategy["recommended_approach"] = "Begin with primary technique, use fallbacks if needed"
            
            # Key considerations
            if strategy["estimated_success_probability"] > 0.8:
                strategy["key_considerations"].append("High confidence in success based on historical data")
            elif strategy["estimated_success_probability"] < 0.6:
                strategy["key_considerations"].append("Consider breaking down into simpler components")
            
            strategy["key_considerations"].append(f"Average techniques per successful project: {len(recommendations[:3])}")
        
        return strategy
    
    def _generate_success_insights(self, overall_success_rate: float,
                                 type_performance: List[Dict[str, Any]],
                                 category_performance: List[Dict[str, Any]],
                                 top_techniques: List[Dict[str, Any]]) -> List[str]:
        """Generate insights from success metrics"""
        insights = []
        
        # Overall performance insight
        if overall_success_rate > 80:
            insights.append(f"Excellent overall success rate of {overall_success_rate:.1f}%")
        elif overall_success_rate > 60:
            insights.append(f"Good success rate of {overall_success_rate:.1f}% with room for improvement")
        else:
            insights.append(f"Success rate of {overall_success_rate:.1f}% indicates need for technique refinement")
        
        # Best performing clone type
        if type_performance:
            best_type = max(type_performance, key=lambda x: x["success_rate"])
            insights.append(f"Most successful clone type: {best_type['clone_type']} ({best_type['success_rate']:.1f}% success rate)")
        
        # Best performing category
        if category_performance:
            best_category = max(category_performance, key=lambda x: x["success_rate"])
            insights.append(f"Most successful design category: {best_category['design_category']} ({best_category['success_rate']:.1f}% success rate)")
        
        # Top technique insight
        if top_techniques:
            top_technique = top_techniques[0]
            insights.append(f"Most effective technique: {top_technique['technique_name']} with {top_technique['success_rate']:.1%} success rate")
        
        return insights