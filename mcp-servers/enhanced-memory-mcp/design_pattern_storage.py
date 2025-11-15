#!/usr/bin/env python3
"""
Design Pattern Storage Module for Enhanced Memory MCP
Provides specialized storage and retrieval for design patterns, visual characteristics, and usage analytics.
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

logger = logging.getLogger("enhanced-memory.design-patterns")

class DesignPatternStorage:
    """Manages storage and retrieval of design patterns with visual characteristics"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_design_pattern_tables()
    
    def init_design_pattern_tables(self):
        """Initialize design pattern specific database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Design patterns table with visual characteristics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS design_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_name TEXT UNIQUE NOT NULL,
                    pattern_type TEXT NOT NULL,
                    style_category TEXT NOT NULL,
                    color_palette TEXT,
                    typography_system TEXT,
                    spacing_patterns TEXT,
                    visual_characteristics TEXT,
                    usage_context TEXT,
                    success_score REAL DEFAULT 0.0,
                    usage_frequency INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Pattern combinations that work well together
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pattern_combinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    primary_pattern_id INTEGER,
                    secondary_pattern_id INTEGER,
                    combination_score REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    context_tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (primary_pattern_id) REFERENCES design_patterns (id),
                    FOREIGN KEY (secondary_pattern_id) REFERENCES design_patterns (id)
                )
            ''')
            
            # Pattern usage analytics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pattern_usage_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id INTEGER,
                    usage_type TEXT NOT NULL,
                    project_context TEXT,
                    success_rating REAL,
                    performance_metrics TEXT,
                    user_feedback TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pattern_id) REFERENCES design_patterns (id)
                )
            ''')
            
            # Design trends tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS design_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trend_name TEXT NOT NULL,
                    trend_category TEXT NOT NULL,
                    popularity_score REAL DEFAULT 0.0,
                    related_patterns TEXT,
                    time_period TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_type ON design_patterns(pattern_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_style ON design_patterns(style_category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_success ON design_patterns(success_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_combinations_score ON pattern_combinations(combination_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_analytics_pattern ON pattern_usage_analytics(pattern_id)')
            
            conn.commit()
            logger.info("🎨 Design pattern tables initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize design pattern tables: {e}")
            raise
        finally:
            conn.close()
    
    def store_design_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a design pattern with visual characteristics and metadata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            pattern_name = pattern_data.get("pattern_name", "")
            pattern_type = pattern_data.get("pattern_type", "unknown")
            style_category = pattern_data.get("style_category", "general")
            
            # Serialize complex data structures
            color_palette = json.dumps(pattern_data.get("color_palette", {}))
            typography_system = json.dumps(pattern_data.get("typography_system", {}))
            spacing_patterns = json.dumps(pattern_data.get("spacing_patterns", {}))
            visual_characteristics = json.dumps(pattern_data.get("visual_characteristics", {}))
            usage_context = json.dumps(pattern_data.get("usage_context", {}))
            metadata = json.dumps(pattern_data.get("metadata", {}))
            
            # Insert or update design pattern
            cursor.execute('''
                INSERT OR REPLACE INTO design_patterns 
                (pattern_name, pattern_type, style_category, color_palette, 
                 typography_system, spacing_patterns, visual_characteristics, 
                 usage_context, success_score, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pattern_name, pattern_type, style_category, color_palette,
                  typography_system, spacing_patterns, visual_characteristics,
                  usage_context, pattern_data.get("success_score", 0.0), metadata))
            
            pattern_id = cursor.lastrowid or cursor.execute(
                "SELECT id FROM design_patterns WHERE pattern_name = ?", (pattern_name,)
            ).fetchone()[0]
            
            # Store as entity in main memory system for searchability
            entity_data = {
                "name": f"DesignPattern_{pattern_name}",
                "entityType": "design_pattern",
                "observations": [
                    f"Pattern type: {pattern_type}",
                    f"Style category: {style_category}",
                    f"Visual characteristics: {json.dumps(pattern_data.get('visual_characteristics', {}), indent=2)}",
                    f"Usage context: {json.dumps(pattern_data.get('usage_context', {}), indent=2)}"
                ]
            }
            
            # Store in main entities table for integration
            from server import create_entities
            create_entities({"entities": [entity_data]})
            
            conn.commit()
            
            result = {
                "success": True,
                "pattern_id": pattern_id,
                "pattern_name": pattern_name,
                "stored_at": datetime.now().isoformat(),
                "integration": "stored_in_main_memory_system"
            }
            
            logger.info(f"🎨 Stored design pattern: {pattern_name} (ID: {pattern_id})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store design pattern: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def retrieve_similar_patterns(self, query_characteristics: Dict[str, Any], 
                                max_results: int = 10) -> Dict[str, Any]:
        """Find similar design patterns based on visual characteristics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build search query based on characteristics
            search_conditions = []
            params = []
            
            if query_characteristics.get("pattern_type"):
                search_conditions.append("pattern_type = ?")
                params.append(query_characteristics["pattern_type"])
            
            if query_characteristics.get("style_category"):
                search_conditions.append("style_category = ?")
                params.append(query_characteristics["style_category"])
            
            # Build base query
            base_query = '''
                SELECT id, pattern_name, pattern_type, style_category, 
                       color_palette, typography_system, visual_characteristics,
                       success_score, usage_frequency, last_used
                FROM design_patterns
            '''
            
            if search_conditions:
                base_query += " WHERE " + " AND ".join(search_conditions)
            
            base_query += " ORDER BY success_score DESC, usage_frequency DESC LIMIT ?"
            params.append(max_results)
            
            cursor.execute(base_query, params)
            
            patterns = []
            for row in cursor.fetchall():
                pattern_id, name, ptype, style, palette, typography, visual, score, frequency, last_used = row
                
                # Parse JSON data
                try:
                    color_palette = json.loads(palette) if palette else {}
                    typography_system = json.loads(typography) if typography else {}
                    visual_characteristics = json.loads(visual) if visual else {}
                except json.JSONDecodeError:
                    color_palette = {}
                    typography_system = {}
                    visual_characteristics = {}
                
                # Calculate similarity score
                similarity_score = self._calculate_pattern_similarity(
                    query_characteristics, {
                        "pattern_type": ptype,
                        "style_category": style,
                        "color_palette": color_palette,
                        "typography_system": typography_system,
                        "visual_characteristics": visual_characteristics
                    }
                )
                
                patterns.append({
                    "pattern_id": pattern_id,
                    "pattern_name": name,
                    "pattern_type": ptype,
                    "style_category": style,
                    "color_palette": color_palette,
                    "typography_system": typography_system,
                    "visual_characteristics": visual_characteristics,
                    "success_score": score,
                    "usage_frequency": frequency,
                    "similarity_score": similarity_score,
                    "last_used": last_used
                })
            
            # Sort by similarity score
            patterns.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return {
                "success": True,
                "query_characteristics": query_characteristics,
                "patterns_found": len(patterns),
                "patterns": patterns,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar patterns: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def track_pattern_usage(self, pattern_id: int, usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track usage of a design pattern and update success metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update usage frequency and last used timestamp
            cursor.execute('''
                UPDATE design_patterns 
                SET usage_frequency = usage_frequency + 1,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (pattern_id,))
            
            # Record detailed usage analytics
            cursor.execute('''
                INSERT INTO pattern_usage_analytics 
                (pattern_id, usage_type, project_context, success_rating, 
                 performance_metrics, user_feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                pattern_id,
                usage_data.get("usage_type", "general"),
                usage_data.get("project_context", ""),
                usage_data.get("success_rating", 0.0),
                json.dumps(usage_data.get("performance_metrics", {})),
                usage_data.get("user_feedback", "")
            ))
            
            # Calculate new success score based on recent usage
            cursor.execute('''
                SELECT AVG(success_rating)
                FROM pattern_usage_analytics
                WHERE pattern_id = ? AND timestamp > datetime('now', '-30 days')
            ''', (pattern_id,))
            
            recent_avg_rating = cursor.fetchone()[0] or 0.0
            
            # Update success score (weighted average of historical and recent)
            cursor.execute('''
                UPDATE design_patterns 
                SET success_score = (success_score * 0.7 + ? * 0.3)
                WHERE id = ?
            ''', (recent_avg_rating, pattern_id))
            
            conn.commit()
            
            return {
                "success": True,
                "pattern_id": pattern_id,
                "updated_success_score": recent_avg_rating,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track pattern usage: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_pattern_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get intelligent pattern recommendations based on context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            project_type = context.get("project_type", "")
            design_goals = context.get("design_goals", [])
            target_audience = context.get("target_audience", "")
            
            # Get top patterns by success score and recent usage
            cursor.execute('''
                SELECT p.id, p.pattern_name, p.pattern_type, p.style_category,
                       p.visual_characteristics, p.success_score, p.usage_frequency,
                       AVG(u.success_rating) as recent_rating
                FROM design_patterns p
                LEFT JOIN pattern_usage_analytics u ON p.id = u.pattern_id 
                    AND u.timestamp > datetime('now', '-30 days')
                GROUP BY p.id
                ORDER BY (p.success_score * 0.4 + COALESCE(recent_rating, 0) * 0.4 + 
                         (p.usage_frequency / 10.0) * 0.2) DESC
                LIMIT 15
            ''')
            
            recommendations = []
            for row in cursor.fetchall():
                pattern_id, name, ptype, style, visual_char, score, frequency, recent_rating = row
                
                try:
                    visual_characteristics = json.loads(visual_char) if visual_char else {}
                except json.JSONDecodeError:
                    visual_characteristics = {}
                
                # Calculate context relevance
                relevance_score = self._calculate_context_relevance(
                    context, {
                        "pattern_type": ptype,
                        "style_category": style,
                        "visual_characteristics": visual_characteristics
                    }
                )
                
                recommendations.append({
                    "pattern_id": pattern_id,
                    "pattern_name": name,
                    "pattern_type": ptype,
                    "style_category": style,
                    "visual_characteristics": visual_characteristics,
                    "success_score": score,
                    "recent_rating": recent_rating or 0.0,
                    "relevance_score": relevance_score,
                    "usage_frequency": frequency,
                    "recommendation_reason": self._generate_recommendation_reason(
                        context, ptype, style, visual_characteristics
                    )
                })
            
            # Sort by combined score
            recommendations.sort(
                key=lambda x: (x["relevance_score"] * 0.4 + 
                              x["success_score"] * 0.3 + 
                              x["recent_rating"] * 0.3), 
                reverse=True
            )
            
            return {
                "success": True,
                "context": context,
                "recommendations": recommendations[:10],
                "total_patterns_analyzed": len(recommendations),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get pattern recommendations: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def analyze_design_trends(self, time_period: str = "30days") -> Dict[str, Any]:
        """Analyze design trends from pattern usage data"""
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
            
            # Analyze pattern type trends
            cursor.execute(f'''
                SELECT p.pattern_type, COUNT(u.id) as usage_count, AVG(u.success_rating) as avg_rating
                FROM design_patterns p
                JOIN pattern_usage_analytics u ON p.id = u.pattern_id
                WHERE u.timestamp > {time_filter}
                GROUP BY p.pattern_type
                ORDER BY usage_count DESC
            ''')
            
            pattern_type_trends = []
            for row in cursor.fetchall():
                pattern_type_trends.append({
                    "pattern_type": row[0],
                    "usage_count": row[1],
                    "average_rating": row[2],
                    "trend_strength": row[1] * row[2]  # Combined metric
                })
            
            # Analyze style category trends
            cursor.execute(f'''
                SELECT p.style_category, COUNT(u.id) as usage_count, AVG(u.success_rating) as avg_rating
                FROM design_patterns p
                JOIN pattern_usage_analytics u ON p.id = u.pattern_id
                WHERE u.timestamp > {time_filter}
                GROUP BY p.style_category
                ORDER BY usage_count DESC
            ''')
            
            style_trends = []
            for row in cursor.fetchall():
                style_trends.append({
                    "style_category": row[0],
                    "usage_count": row[1],
                    "average_rating": row[2],
                    "trend_strength": row[1] * row[2]
                })
            
            # Identify emerging patterns (new patterns with high success)
            cursor.execute(f'''
                SELECT p.pattern_name, p.pattern_type, p.success_score, p.usage_frequency
                FROM design_patterns p
                WHERE p.created_at > {time_filter} AND p.success_score > 0.7
                ORDER BY p.success_score DESC
            ''')
            
            emerging_patterns = []
            for row in cursor.fetchall():
                emerging_patterns.append({
                    "pattern_name": row[0],
                    "pattern_type": row[1],
                    "success_score": row[2],
                    "usage_frequency": row[3]
                })
            
            return {
                "success": True,
                "time_period": time_period,
                "pattern_type_trends": pattern_type_trends,
                "style_category_trends": style_trends,
                "emerging_patterns": emerging_patterns,
                "analysis_timestamp": datetime.now().isoformat(),
                "insights": self._generate_trend_insights(pattern_type_trends, style_trends, emerging_patterns)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze design trends: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _calculate_pattern_similarity(self, query: Dict[str, Any], pattern: Dict[str, Any]) -> float:
        """Calculate similarity score between query characteristics and pattern"""
        similarity = 0.0
        factors = 0
        
        # Pattern type match
        if query.get("pattern_type") and pattern.get("pattern_type"):
            if query["pattern_type"] == pattern["pattern_type"]:
                similarity += 0.3
            factors += 0.3
        
        # Style category match
        if query.get("style_category") and pattern.get("style_category"):
            if query["style_category"] == pattern["style_category"]:
                similarity += 0.2
            factors += 0.2
        
        # Visual characteristics similarity
        query_visual = query.get("visual_characteristics", {})
        pattern_visual = pattern.get("visual_characteristics", {})
        
        if query_visual and pattern_visual:
            visual_matches = 0
            visual_total = 0
            
            for key in set(query_visual.keys()) | set(pattern_visual.keys()):
                visual_total += 1
                if key in query_visual and key in pattern_visual:
                    if query_visual[key] == pattern_visual[key]:
                        visual_matches += 1
            
            if visual_total > 0:
                visual_similarity = visual_matches / visual_total
                similarity += visual_similarity * 0.3
            factors += 0.3
        
        # Color palette similarity
        query_colors = query.get("color_palette", {})
        pattern_colors = pattern.get("color_palette", {})
        
        if query_colors and pattern_colors:
            color_similarity = self._calculate_color_similarity(query_colors, pattern_colors)
            similarity += color_similarity * 0.2
            factors += 0.2
        
        return similarity / factors if factors > 0 else 0.0
    
    def _calculate_color_similarity(self, colors1: Dict, colors2: Dict) -> float:
        """Calculate similarity between two color palettes"""
        if not colors1 or not colors2:
            return 0.0
        
        # Simple implementation - can be enhanced with color theory
        common_keys = set(colors1.keys()) & set(colors2.keys())
        total_keys = set(colors1.keys()) | set(colors2.keys())
        
        if not total_keys:
            return 0.0
        
        return len(common_keys) / len(total_keys)
    
    def _calculate_context_relevance(self, context: Dict[str, Any], pattern: Dict[str, Any]) -> float:
        """Calculate how relevant a pattern is to the given context"""
        relevance = 0.0
        
        # Project type relevance
        project_type = context.get("project_type", "").lower()
        pattern_type = pattern.get("pattern_type", "").lower()
        
        if project_type in pattern_type or pattern_type in project_type:
            relevance += 0.4
        
        # Design goals relevance
        design_goals = [goal.lower() for goal in context.get("design_goals", [])]
        visual_chars = pattern.get("visual_characteristics", {})
        
        for goal in design_goals:
            for char_key, char_value in visual_chars.items():
                if goal in str(char_value).lower() or goal in char_key.lower():
                    relevance += 0.1
                    break
        
        # Style category relevance
        if context.get("preferred_style"):
            if context["preferred_style"].lower() == pattern.get("style_category", "").lower():
                relevance += 0.3
        
        return min(relevance, 1.0)  # Cap at 1.0
    
    def _generate_recommendation_reason(self, context: Dict[str, Any], 
                                      pattern_type: str, style_category: str, 
                                      visual_characteristics: Dict[str, Any]) -> str:
        """Generate a human-readable reason for the recommendation"""
        reasons = []
        
        if context.get("project_type", "").lower() in pattern_type.lower():
            reasons.append(f"Matches your {context['project_type']} project type")
        
        if context.get("preferred_style", "").lower() == style_category.lower():
            reasons.append(f"Aligns with your {style_category} style preference")
        
        if visual_characteristics.get("complexity", "").lower() == "minimal":
            reasons.append("Clean, minimal design approach")
        
        if not reasons:
            reasons.append("High success rate in similar contexts")
        
        return "; ".join(reasons)
    
    def _generate_trend_insights(self, pattern_trends: List[Dict], 
                               style_trends: List[Dict], 
                               emerging_patterns: List[Dict]) -> List[str]:
        """Generate insights from trend analysis"""
        insights = []
        
        # Top pattern type
        if pattern_trends:
            top_pattern = pattern_trends[0]
            insights.append(f"Most popular pattern type: {top_pattern['pattern_type']} with {top_pattern['usage_count']} uses")
        
        # Top style category
        if style_trends:
            top_style = style_trends[0]
            insights.append(f"Leading style category: {top_style['style_category']} with average rating {top_style['average_rating']:.2f}")
        
        # Emerging patterns
        if emerging_patterns:
            insights.append(f"Found {len(emerging_patterns)} emerging high-performing patterns")
        
        # Quality trends
        if pattern_trends:
            high_quality = [p for p in pattern_trends if p['average_rating'] > 0.8]
            if high_quality:
                insights.append(f"{len(high_quality)} pattern types showing excellent performance (>0.8 rating)")
        
        return insights