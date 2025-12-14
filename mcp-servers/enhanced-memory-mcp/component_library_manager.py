#!/usr/bin/env python3
"""
Component Library Manager for Enhanced Memory MCP
Provides specialized storage and retrieval for reusable component code, variations, and usage patterns.
Integrates with the existing Enhanced-Memory-MCP architecture.
"""

import json
import sqlite3
import hashlib
import zlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
import re

logger = logging.getLogger("enhanced-memory.component-library")

class ComponentLibraryManager:
    """Manages storage and retrieval of reusable component libraries and code snippets"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_component_library_tables()
    
    def init_component_library_tables(self):
        """Initialize component library specific database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Component libraries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS component_libraries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_name TEXT UNIQUE NOT NULL,
                    component_type TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    category TEXT NOT NULL,
                    code_content BLOB NOT NULL,
                    code_language TEXT NOT NULL,
                    original_size INTEGER,
                    compressed_size INTEGER,
                    compression_ratio REAL,
                    checksum TEXT,
                    props_schema TEXT,
                    variations TEXT,
                    dependencies TEXT,
                    usage_examples TEXT,
                    documentation TEXT,
                    quality_score REAL DEFAULT 0.0,
                    usage_frequency INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Component variations (states, themes, sizes, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS component_variations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id INTEGER,
                    variation_name TEXT NOT NULL,
                    variation_type TEXT NOT NULL,
                    variation_code BLOB,
                    variation_props TEXT,
                    usage_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES component_libraries (id)
                )
            ''')
            
            # Component relationships (which components work well together)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS component_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_component_id INTEGER,
                    child_component_id INTEGER,
                    relationship_type TEXT NOT NULL,
                    compatibility_score REAL DEFAULT 1.0,
                    usage_count INTEGER DEFAULT 0,
                    context_tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_component_id) REFERENCES component_libraries (id),
                    FOREIGN KEY (child_component_id) REFERENCES component_libraries (id)
                )
            ''')
            
            # Component usage analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS component_usage_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id INTEGER,
                    usage_type TEXT NOT NULL,
                    project_context TEXT,
                    performance_metrics TEXT,
                    quality_rating REAL,
                    user_feedback TEXT,
                    code_complexity_score REAL,
                    maintainability_score REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES component_libraries (id)
                )
            ''')
            
            # Framework-specific implementations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS framework_implementations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id INTEGER,
                    framework_name TEXT NOT NULL,
                    implementation_code BLOB NOT NULL,
                    framework_version TEXT,
                    compatibility_notes TEXT,
                    performance_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES component_libraries (id)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_components_type ON component_libraries(component_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_components_framework ON component_libraries(framework)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_components_category ON component_libraries(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_components_quality ON component_libraries(quality_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_variations_component ON component_variations(component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relationships_parent ON component_relationships(parent_component_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_analytics_component ON component_usage_analytics(component_id)')
            
            conn.commit()
            logger.info("🧩 Component library tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize component library tables: {e}")
            raise
        finally:
            conn.close()
    
    def store_component_library(self, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a reusable component with code and metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            component_name = component_data.get("component_name", "")
            component_type = component_data.get("component_type", "unknown")
            framework = component_data.get("framework", "vanilla")
            category = component_data.get("category", "general")
            code_content = component_data.get("code_content", "")
            code_language = component_data.get("code_language", "javascript")
            
            # Compress code content
            code_bytes = code_content.encode('utf-8')
            original_size = len(code_bytes)
            compressed_code = zlib.compress(code_bytes, level=9)
            compressed_size = len(compressed_code)
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            checksum = hashlib.sha256(code_bytes).hexdigest()
            
            # Serialize complex data structures
            props_schema = json.dumps(component_data.get("props_schema", {}))
            variations = json.dumps(component_data.get("variations", []))
            dependencies = json.dumps(component_data.get("dependencies", []))
            usage_examples = json.dumps(component_data.get("usage_examples", []))
            documentation = json.dumps(component_data.get("documentation", {}))
            metadata = json.dumps(component_data.get("metadata", {}))
            
            # Insert or update component
            cursor.execute('''
                INSERT OR REPLACE INTO component_libraries 
                (component_name, component_type, framework, category, code_content,
                 code_language, original_size, compressed_size, compression_ratio, checksum,
                 props_schema, variations, dependencies, usage_examples, documentation,
                 quality_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (component_name, component_type, framework, category, compressed_code,
                  code_language, original_size, compressed_size, compression_ratio, checksum,
                  props_schema, variations, dependencies, usage_examples, documentation,
                  component_data.get("quality_score", 0.0), metadata))
            
            component_id = cursor.lastrowid or cursor.execute(
                "SELECT id FROM component_libraries WHERE component_name = ?", (component_name,)
            ).fetchone()[0]
            
            # Store variations if provided
            for variation in component_data.get("variations", []):
                self._store_component_variation(cursor, component_id, variation)
            
            # Store framework implementations if provided
            for impl in component_data.get("framework_implementations", []):
                self._store_framework_implementation(cursor, component_id, impl)
            
            # Store as entity in main memory system for searchability
            entity_data = {
                "name": f"Component_{component_name}",
                "entityType": "component_library",
                "observations": [
                    f"Component type: {component_type}",
                    f"Framework: {framework}",
                    f"Category: {category}",
                    f"Language: {code_language}",
                    f"Code size: {original_size} bytes (compressed to {compressed_size} bytes)",
                    f"Props schema: {json.dumps(component_data.get('props_schema', {}), indent=2)}",
                    f"Dependencies: {json.dumps(component_data.get('dependencies', []))}",
                    f"Usage examples: {len(component_data.get('usage_examples', []))} provided"
                ]
            }
            
            # Store in main entities table for integration
            from server import create_entities
            create_entities({"entities": [entity_data]})
            
            conn.commit()
            
            result = {
                "success": True,
                "component_id": component_id,
                "component_name": component_name,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "compression_savings": f"{(1 - compression_ratio) * 100:.1f}%",
                "checksum": checksum[:8] + "...",
                "stored_at": datetime.now().isoformat(),
                "integration": "stored_in_main_memory_system"
            }
            
            logger.info(f"🧩 Stored component: {component_name} (ID: {component_id}, {result['compression_savings']} compression)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store component: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def find_reusable_components(self, search_criteria: Dict[str, Any], 
                               max_results: int = 15) -> Dict[str, Any]:
        """Find reusable components based on search criteria"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build search query
            search_conditions = []
            params = []
            
            if search_criteria.get("component_type"):
                search_conditions.append("component_type = ?")
                params.append(search_criteria["component_type"])
            
            if search_criteria.get("framework"):
                search_conditions.append("framework = ?")
                params.append(search_criteria["framework"])
            
            if search_criteria.get("category"):
                search_conditions.append("category = ?")
                params.append(search_criteria["category"])
            
            if search_criteria.get("code_language"):
                search_conditions.append("code_language = ?")
                params.append(search_criteria["code_language"])
            
            # Text search in component names and documentation
            if search_criteria.get("search_text"):
                search_conditions.append("(component_name LIKE ? OR documentation LIKE ?)")
                search_text = f"%{search_criteria['search_text']}%"
                params.extend([search_text, search_text])
            
            # Build base query
            base_query = '''
                SELECT id, component_name, component_type, framework, category,
                       code_content, props_schema, variations, dependencies,
                       usage_examples, documentation, quality_score, usage_frequency,
                       original_size, compressed_size, compression_ratio, last_used
                FROM component_libraries
            '''
            
            if search_conditions:
                base_query += " WHERE " + " AND ".join(search_conditions)
            
            base_query += " ORDER BY quality_score DESC, usage_frequency DESC LIMIT ?"
            params.append(max_results)
            
            cursor.execute(base_query, params)
            
            components = []
            for row in cursor.fetchall():
                (component_id, name, comp_type, framework, category, compressed_code, 
                 props_schema, variations, dependencies, usage_examples, documentation,
                 quality_score, usage_frequency, original_size, compressed_size, 
                 compression_ratio, last_used) = row
                
                # Decompress code
                try:
                    code_content = zlib.decompress(compressed_code).decode('utf-8')
                except Exception as e:
                    logger.error(f"Failed to decompress code for component {name}: {e}")
                    code_content = "// Code decompression failed"
                
                # Parse JSON data
                try:
                    props_schema_data = json.loads(props_schema) if props_schema else {}
                    variations_data = json.loads(variations) if variations else []
                    dependencies_data = json.loads(dependencies) if dependencies else []
                    usage_examples_data = json.loads(usage_examples) if usage_examples else []
                    documentation_data = json.loads(documentation) if documentation else {}
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON data for component {name}: {e}")
                    props_schema_data = {}
                    variations_data = []
                    dependencies_data = []
                    usage_examples_data = []
                    documentation_data = {}
                
                # Get component variations from database
                cursor.execute('''
                    SELECT variation_name, variation_type, variation_props, usage_context
                    FROM component_variations WHERE component_id = ?
                ''', (component_id,))
                
                db_variations = []
                for var_row in cursor.fetchall():
                    db_variations.append({
                        "name": var_row[0],
                        "type": var_row[1],
                        "props": json.loads(var_row[2]) if var_row[2] else {},
                        "context": var_row[3]
                    })
                
                # Calculate relevance score
                relevance_score = self._calculate_component_relevance(search_criteria, {
                    "component_type": comp_type,
                    "framework": framework,
                    "category": category,
                    "dependencies": dependencies_data,
                    "props_schema": props_schema_data
                })
                
                components.append({
                    "component_id": component_id,
                    "component_name": name,
                    "component_type": comp_type,
                    "framework": framework,
                    "category": category,
                    "code_content": code_content,
                    "props_schema": props_schema_data,
                    "variations": variations_data + db_variations,
                    "dependencies": dependencies_data,
                    "usage_examples": usage_examples_data,
                    "documentation": documentation_data,
                    "quality_score": quality_score,
                    "usage_frequency": usage_frequency,
                    "relevance_score": relevance_score,
                    "code_stats": {
                        "original_size": original_size,
                        "compressed_size": compressed_size,
                        "compression_ratio": compression_ratio,
                        "lines_of_code": len(code_content.split('\n'))
                    },
                    "last_used": last_used
                })
            
            # Sort by relevance and quality
            components.sort(
                key=lambda x: (x["relevance_score"] * 0.4 + x["quality_score"] * 0.6), 
                reverse=True
            )
            
            return {
                "success": True,
                "search_criteria": search_criteria,
                "components_found": len(components),
                "components": components,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to find reusable components: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def track_component_usage(self, component_id: int, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track usage of a component and update quality metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update usage frequency and last used timestamp
            cursor.execute('''
                UPDATE component_libraries 
                SET usage_frequency = usage_frequency + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (component_id,))
            
            # Record detailed usage analytics
            cursor.execute('''
                INSERT INTO component_usage_analytics 
                (component_id, usage_type, project_context, performance_metrics,
                 quality_rating, user_feedback, code_complexity_score, maintainability_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                component_id,
                usage_data.get("usage_type", "general"),
                usage_data.get("project_context", ""),
                json.dumps(usage_data.get("performance_metrics", {})),
                usage_data.get("quality_rating", 0.0),
                usage_data.get("user_feedback", ""),
                usage_data.get("code_complexity_score", 0.0),
                usage_data.get("maintainability_score", 0.0)
            ))
            
            # Calculate new quality score based on recent usage
            cursor.execute('''
                SELECT AVG(quality_rating), AVG(code_complexity_score), AVG(maintainability_score)
                FROM component_usage_analytics
                WHERE component_id = ? AND timestamp > datetime('now', '-30 days')
            ''', (component_id,))
            
            result = cursor.fetchone()
            recent_quality = result[0] or 0.0
            recent_complexity = result[1] or 0.0  # Lower is better
            recent_maintainability = result[2] or 0.0  # Higher is better
            
            # Calculate composite quality score
            composite_quality = (
                recent_quality * 0.5 +  # User rating
                (1.0 - min(recent_complexity / 10.0, 1.0)) * 0.2 +  # Complexity (inverted)
                recent_maintainability * 0.3  # Maintainability
            )
            
            # Update quality score (weighted average of historical and recent)
            cursor.execute('''
                UPDATE component_libraries 
                SET quality_score = (quality_score * 0.6 + ? * 0.4)
                WHERE id = ?
            ''', (composite_quality, component_id))
            
            conn.commit()
            
            return {
                "success": True,
                "component_id": component_id,
                "updated_quality_score": composite_quality,
                "recent_metrics": {
                    "quality_rating": recent_quality,
                    "complexity_score": recent_complexity,
                    "maintainability_score": recent_maintainability
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track component usage: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def analyze_component_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in component usage and relationships"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Most popular component types
            cursor.execute('''
                SELECT component_type, COUNT(*) as count, AVG(quality_score) as avg_quality,
                       SUM(usage_frequency) as total_usage
                FROM component_libraries
                GROUP BY component_type
                ORDER BY total_usage DESC
            ''')
            
            popular_types = []
            for row in cursor.fetchall():
                popular_types.append({
                    "component_type": row[0],
                    "count": row[1],
                    "average_quality": row[2],
                    "total_usage": row[3]
                })
            
            # Framework distribution
            cursor.execute('''
                SELECT framework, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM component_libraries
                GROUP BY framework
                ORDER BY count DESC
            ''')
            
            framework_dist = []
            for row in cursor.fetchall():
                framework_dist.append({
                    "framework": row[0],
                    "component_count": row[1],
                    "average_quality": row[2]
                })
            
            # Component relationships analysis
            cursor.execute('''
                SELECT cr.relationship_type, COUNT(*) as count, AVG(cr.compatibility_score) as avg_compatibility
                FROM component_relationships cr
                GROUP BY cr.relationship_type
                ORDER BY count DESC
            ''')
            
            relationship_patterns = []
            for row in cursor.fetchall():
                relationship_patterns.append({
                    "relationship_type": row[0],
                    "occurrence_count": row[1],
                    "average_compatibility": row[2]
                })
            
            # Quality trends over time
            cursor.execute('''
                SELECT DATE(created_at) as date, AVG(quality_score) as avg_quality, COUNT(*) as components_created
                FROM component_libraries
                WHERE created_at > datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            
            quality_trends = []
            for row in cursor.fetchall():
                quality_trends.append({
                    "date": row[0],
                    "average_quality": row[1],
                    "components_created": row[2]
                })
            
            # High-performing components
            cursor.execute('''
                SELECT component_name, component_type, quality_score, usage_frequency
                FROM component_libraries
                WHERE quality_score > 0.8 AND usage_frequency > 5
                ORDER BY quality_score DESC, usage_frequency DESC
                LIMIT 10
            ''')
            
            top_performers = []
            for row in cursor.fetchall():
                top_performers.append({
                    "component_name": row[0],
                    "component_type": row[1],
                    "quality_score": row[2],
                    "usage_frequency": row[3]
                })
            
            return {
                "success": True,
                "analysis_timestamp": datetime.now().isoformat(),
                "popular_component_types": popular_types,
                "framework_distribution": framework_dist,
                "relationship_patterns": relationship_patterns,
                "quality_trends": quality_trends,
                "top_performing_components": top_performers,
                "insights": self._generate_component_insights(
                    popular_types, framework_dist, relationship_patterns, top_performers
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze component patterns: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_component_recommendations(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get intelligent component recommendations based on project context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            framework = project_context.get("framework", "")
            project_type = project_context.get("project_type", "")
            required_features = project_context.get("required_features", [])
            complexity_preference = project_context.get("complexity_preference", "medium")
            
            # Base query for components
            base_conditions = []
            params = []
            
            if framework:
                base_conditions.append("framework = ?")
                params.append(framework)
            
            # Build recommendation query
            query = '''
                SELECT c.id, c.component_name, c.component_type, c.framework, c.category,
                       c.props_schema, c.dependencies, c.quality_score, c.usage_frequency,
                       AVG(u.quality_rating) as recent_rating,
                       AVG(u.code_complexity_score) as avg_complexity,
                       AVG(u.maintainability_score) as avg_maintainability
                FROM component_libraries c
                LEFT JOIN component_usage_analytics u ON c.id = u.component_id 
                    AND u.timestamp > datetime('now', '-60 days')
            '''
            
            if base_conditions:
                query += " WHERE " + " AND ".join(base_conditions)
            
            query += '''
                GROUP BY c.id
                ORDER BY (c.quality_score * 0.3 + COALESCE(recent_rating, 0) * 0.3 + 
                         (c.usage_frequency / 10.0) * 0.2 + 
                         COALESCE(avg_maintainability, 0) * 0.2) DESC
                LIMIT 20
            '''
            
            cursor.execute(query, params)
            
            recommendations = []
            for row in cursor.fetchall():
                (comp_id, name, comp_type, fw, category, props_schema, dependencies,
                 quality_score, usage_freq, recent_rating, avg_complexity, avg_maintainability) = row
                
                # Parse dependencies
                try:
                    deps = json.loads(dependencies) if dependencies else []
                    props = json.loads(props_schema) if props_schema else {}
                except json.JSONDecodeError:
                    deps = []
                    props = {}
                
                # Calculate context relevance
                relevance_score = self._calculate_project_relevance(
                    project_context, {
                        "component_type": comp_type,
                        "category": category,
                        "dependencies": deps,
                        "props_schema": props,
                        "complexity": avg_complexity or 0.0
                    }
                )
                
                recommendations.append({
                    "component_id": comp_id,
                    "component_name": name,
                    "component_type": comp_type,
                    "framework": fw,
                    "category": category,
                    "quality_score": quality_score,
                    "usage_frequency": usage_freq,
                    "recent_rating": recent_rating or 0.0,
                    "complexity_score": avg_complexity or 0.0,
                    "maintainability_score": avg_maintainability or 0.0,
                    "relevance_score": relevance_score,
                    "dependencies": deps,
                    "props_schema": props,
                    "recommendation_reason": self._generate_component_recommendation_reason(
                        project_context, comp_type, category, quality_score, usage_freq
                    )
                })
            
            # Sort by combined relevance and quality score
            recommendations.sort(
                key=lambda x: (x["relevance_score"] * 0.4 + x["quality_score"] * 0.6), 
                reverse=True
            )
            
            return {
                "success": True,
                "project_context": project_context,
                "recommendations": recommendations[:12],
                "total_analyzed": len(recommendations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get component recommendations: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _store_component_variation(self, cursor, component_id: int, variation: Dict[str, Any]):
        """Store a component variation"""
        cursor.execute('''
            INSERT INTO component_variations 
            (component_id, variation_name, variation_type, variation_code, variation_props, usage_context)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            component_id,
            variation.get("name", ""),
            variation.get("type", ""),
            zlib.compress(variation.get("code", "").encode('utf-8')) if variation.get("code") else None,
            json.dumps(variation.get("props", {})),
            variation.get("context", "")
        ))
    
    def _store_framework_implementation(self, cursor, component_id: int, implementation: Dict[str, Any]):
        """Store a framework-specific implementation"""
        impl_code = implementation.get("code", "")
        compressed_code = zlib.compress(impl_code.encode('utf-8'))
        
        cursor.execute('''
            INSERT INTO framework_implementations 
            (component_id, framework_name, implementation_code, framework_version, 
             compatibility_notes, performance_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            component_id,
            implementation.get("framework", ""),
            compressed_code,
            implementation.get("version", ""),
            implementation.get("compatibility_notes", ""),
            implementation.get("performance_notes", "")
        ))
    
    def _calculate_component_relevance(self, criteria: Dict[str, Any], component: Dict[str, Any]) -> float:
        """Calculate how relevant a component is to search criteria"""
        relevance = 0.0
        
        # Exact matches
        if criteria.get("component_type") == component.get("component_type"):
            relevance += 0.3
        if criteria.get("framework") == component.get("framework"):
            relevance += 0.2
        if criteria.get("category") == component.get("category"):
            relevance += 0.2
        
        # Feature matching
        required_features = criteria.get("required_features", [])
        component_props = component.get("props_schema", {})
        
        if required_features and component_props:
            feature_matches = 0
            for feature in required_features:
                if any(feature.lower() in prop.lower() for prop in component_props.keys()):
                    feature_matches += 1
            
            if required_features:
                relevance += (feature_matches / len(required_features)) * 0.3
        
        return min(relevance, 1.0)
    
    def _calculate_project_relevance(self, project_context: Dict[str, Any], 
                                   component: Dict[str, Any]) -> float:
        """Calculate how relevant a component is to project context"""
        relevance = 0.0
        
        # Framework match
        if project_context.get("framework") == component.get("component_type"):
            relevance += 0.3
        
        # Project type relevance
        project_type = project_context.get("project_type", "").lower()
        category = component.get("category", "").lower()
        
        if project_type in category or category in project_type:
            relevance += 0.2
        
        # Complexity preference
        complexity_pref = project_context.get("complexity_preference", "medium")
        component_complexity = component.get("complexity", 0.0)
        
        if complexity_pref == "low" and component_complexity < 3.0:
            relevance += 0.1
        elif complexity_pref == "medium" and 3.0 <= component_complexity <= 7.0:
            relevance += 0.1
        elif complexity_pref == "high" and component_complexity > 7.0:
            relevance += 0.1
        
        # Required features
        required_features = project_context.get("required_features", [])
        component_props = component.get("props_schema", {})
        
        if required_features and component_props:
            feature_matches = sum(
                1 for feature in required_features
                if any(feature.lower() in str(prop).lower() for prop in component_props.keys())
            )
            if required_features:
                relevance += (feature_matches / len(required_features)) * 0.4
        
        return min(relevance, 1.0)
    
    def _generate_component_recommendation_reason(self, context: Dict[str, Any], 
                                                component_type: str, category: str,
                                                quality_score: float, usage_freq: int) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if context.get("framework") and context["framework"].lower() in component_type.lower():
            reasons.append(f"Perfect match for {context['framework']} framework")
        
        if quality_score > 0.8:
            reasons.append("Excellent quality rating")
        
        if usage_freq > 10:
            reasons.append("Widely adopted and tested")
        
        if context.get("project_type", "").lower() in category.lower():
            reasons.append(f"Ideal for {context['project_type']} projects")
        
        if not reasons:
            reasons.append("Solid performance in similar contexts")
        
        return "; ".join(reasons)
    
    def _generate_component_insights(self, popular_types: List[Dict], 
                                   framework_dist: List[Dict],
                                   relationship_patterns: List[Dict],
                                   top_performers: List[Dict]) -> List[str]:
        """Generate insights from component analysis"""
        insights = []
        
        # Most popular component type
        if popular_types:
            top_type = popular_types[0]
            insights.append(
                f"Most popular component type: {top_type['component_type']} "
                f"({top_type['count']} components, avg quality {top_type['average_quality']:.2f})"
            )
        
        # Framework trends
        if framework_dist:
            top_framework = framework_dist[0]
            insights.append(
                f"Leading framework: {top_framework['framework']} "
                f"({top_framework['component_count']} components)"
            )
        
        # Quality insights
        if top_performers:
            high_quality_count = len([p for p in top_performers if p['quality_score'] > 0.9])
            if high_quality_count > 0:
                insights.append(f"{high_quality_count} components show exceptional quality (>0.9)")
        
        # Relationship insights
        if relationship_patterns:
            top_relationship = relationship_patterns[0]
            insights.append(
                f"Most common component relationship: {top_relationship['relationship_type']} "
                f"({top_relationship['occurrence_count']} instances)"
            )
        
        return insights