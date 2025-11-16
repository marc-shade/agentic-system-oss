#!/usr/bin/env python3
"""
Image Generation Pattern Integration for Enhanced Memory MCP
Specialized storage and retrieval for design-system-aware image generation patterns.
Integrates with the enhanced Image-Gen-MCP for intelligent pattern learning.
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger("enhanced-memory.image-gen-patterns")

class ImageGenPatternIntegration:
    """Manages integration with enhanced Image-Gen-MCP design patterns"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_image_gen_tables()
    
    def init_image_gen_tables(self):
        """Initialize tables specific to image generation patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Image generation design patterns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_gen_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT UNIQUE NOT NULL,
                    design_tokens TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    generation_quality TEXT,
                    prompt_template TEXT,
                    style_characteristics TEXT,
                    success_metrics TEXT,
                    provider_preferences TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    quality_score REAL DEFAULT 0.0
                )
            ''')
            
            # Style transfer mappings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS style_transfer_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_style TEXT NOT NULL,
                    target_aesthetic TEXT NOT NULL,
                    transfer_intensity REAL DEFAULT 0.8,
                    enhancement_prompts TEXT,
                    success_rate REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Component asset generation history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS component_asset_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_type TEXT NOT NULL,
                    design_pattern_id INTEGER,
                    dimensions TEXT,
                    variants TEXT,
                    states TEXT,
                    generation_results TEXT,
                    quality_metrics TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (design_pattern_id) REFERENCES image_gen_patterns (id)
                )
            ''')
            
            # Optimization presets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_name TEXT UNIQUE NOT NULL,
                    preset_type TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    performance_metrics TEXT,
                    use_cases TEXT,
                    success_rate REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_gen_patterns_hash ON image_gen_patterns(pattern_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_gen_patterns_type ON image_gen_patterns(asset_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_gen_patterns_quality ON image_gen_patterns(quality_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_style_transfer_success ON style_transfer_mappings(success_rate)')
            
            conn.commit()
            logger.info("🎨 Image generation pattern tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize image gen tables: {e}")
            raise
        finally:
            conn.close()
    
    def store_image_gen_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store an image generation pattern with design tokens"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create pattern hash for deduplication
            pattern_content = json.dumps({
                "design_tokens": pattern_data.get("design_tokens", {}),
                "asset_type": pattern_data.get("asset_type", ""),
                "prompt_template": pattern_data.get("prompt_template", "")
            }, sort_keys=True)
            pattern_hash = hashlib.sha256(pattern_content.encode()).hexdigest()[:16]
            
            # Serialize data
            design_tokens = json.dumps(pattern_data.get("design_tokens", {}))
            asset_type = pattern_data.get("asset_type", "general")
            generation_quality = pattern_data.get("generation_quality", "standard")
            prompt_template = pattern_data.get("prompt_template", "")
            style_characteristics = json.dumps(pattern_data.get("style_characteristics", {}))
            success_metrics = json.dumps(pattern_data.get("success_metrics", {}))
            provider_preferences = json.dumps(pattern_data.get("provider_preferences", {}))
            
            # Insert or update
            cursor.execute('''
                INSERT OR REPLACE INTO image_gen_patterns
                (pattern_hash, design_tokens, asset_type, generation_quality,
                 prompt_template, style_characteristics, success_metrics, 
                 provider_preferences, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pattern_hash, design_tokens, asset_type, generation_quality,
                  prompt_template, style_characteristics, success_metrics,
                  provider_preferences, pattern_data.get("quality_score", 0.0)))
            
            pattern_id = cursor.lastrowid
            
            # Also store in main design patterns for cross-reference
            from design_pattern_storage import DesignPatternStorage
            dps = DesignPatternStorage(self.db_path)
            
            main_pattern_data = {
                "pattern_name": f"ImageGen_{asset_type}_{pattern_hash[:8]}",
                "pattern_type": f"image_generation_{asset_type}",
                "style_category": pattern_data.get("style_category", "general"),
                "color_palette": pattern_data.get("design_tokens", {}).get("colors", {}),
                "typography_system": pattern_data.get("design_tokens", {}).get("typography", {}),
                "spacing_patterns": pattern_data.get("design_tokens", {}).get("spacing", {}),
                "visual_characteristics": style_characteristics,
                "usage_context": {
                    "asset_type": asset_type,
                    "quality": generation_quality,
                    "prompt_template": prompt_template
                },
                "success_score": pattern_data.get("quality_score", 0.0),
                "metadata": {
                    "image_gen_pattern_id": pattern_id,
                    "pattern_hash": pattern_hash
                }
            }
            
            dps.store_design_pattern(main_pattern_data)
            
            conn.commit()
            
            return {
                "success": True,
                "pattern_id": pattern_id,
                "pattern_hash": pattern_hash,
                "asset_type": asset_type,
                "stored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to store image gen pattern: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_best_patterns_for_asset_type(self, asset_type: str, 
                                        design_tokens: Optional[Dict[str, Any]] = None,
                                        max_results: int = 5) -> Dict[str, Any]:
        """Get best performing patterns for a specific asset type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Base query for asset type
            query = '''
                SELECT id, pattern_hash, design_tokens, generation_quality,
                       prompt_template, style_characteristics, success_metrics,
                       provider_preferences, quality_score, usage_count
                FROM image_gen_patterns
                WHERE asset_type = ?
                ORDER BY quality_score DESC, usage_count DESC
                LIMIT ?
            '''
            
            cursor.execute(query, (asset_type, max_results))
            
            patterns = []
            for row in cursor.fetchall():
                pattern_id, phash, tokens, quality, prompt, style, metrics, providers, score, usage = row
                
                # Parse JSON fields
                design_tokens_parsed = json.loads(tokens)
                style_chars = json.loads(style)
                success_metrics = json.loads(metrics)
                provider_prefs = json.loads(providers)
                
                # Calculate similarity if design tokens provided
                similarity_score = 1.0
                if design_tokens:
                    similarity_score = self._calculate_token_similarity(
                        design_tokens, design_tokens_parsed
                    )
                
                patterns.append({
                    "pattern_id": pattern_id,
                    "pattern_hash": phash,
                    "design_tokens": design_tokens_parsed,
                    "generation_quality": quality,
                    "prompt_template": prompt,
                    "style_characteristics": style_chars,
                    "success_metrics": success_metrics,
                    "provider_preferences": provider_prefs,
                    "quality_score": score,
                    "usage_count": usage,
                    "similarity_score": similarity_score
                })
            
            # Sort by combined score if design tokens provided
            if design_tokens:
                patterns.sort(
                    key=lambda x: (x["similarity_score"] * 0.5 + x["quality_score"] * 0.5),
                    reverse=True
                )
            
            return {
                "success": True,
                "asset_type": asset_type,
                "patterns_found": len(patterns),
                "patterns": patterns,
                "search_criteria": {
                    "asset_type": asset_type,
                    "design_tokens_provided": design_tokens is not None
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get patterns for asset type: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def store_style_transfer_mapping(self, mapping_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a successful style transfer mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO style_transfer_mappings
                (source_style, target_aesthetic, transfer_intensity,
                 enhancement_prompts, success_rate, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                mapping_data.get("source_style", ""),
                mapping_data.get("target_aesthetic", ""),
                mapping_data.get("transfer_intensity", 0.8),
                json.dumps(mapping_data.get("enhancement_prompts", [])),
                mapping_data.get("success_rate", 0.0),
                json.dumps(mapping_data.get("metadata", {}))
            ))
            
            mapping_id = cursor.lastrowid
            conn.commit()
            
            return {
                "success": True,
                "mapping_id": mapping_id,
                "stored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to store style transfer mapping: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def track_component_generation(self, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track component asset generation results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO component_asset_history
                (component_type, design_pattern_id, dimensions, variants,
                 states, generation_results, quality_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                component_data.get("component_type", ""),
                component_data.get("design_pattern_id"),
                json.dumps(component_data.get("dimensions", [])),
                json.dumps(component_data.get("variants", [])),
                json.dumps(component_data.get("states", [])),
                json.dumps(component_data.get("generation_results", {})),
                json.dumps(component_data.get("quality_metrics", {}))
            ))
            
            history_id = cursor.lastrowid
            
            # Update pattern usage count and quality score
            if component_data.get("design_pattern_id"):
                quality_score = component_data.get("quality_metrics", {}).get("overall_score", 0.0)
                cursor.execute('''
                    UPDATE image_gen_patterns
                    SET usage_count = usage_count + 1,
                        last_used = CURRENT_TIMESTAMP,
                        quality_score = (quality_score * 0.8 + ? * 0.2)
                    WHERE id = ?
                ''', (quality_score, component_data["design_pattern_id"]))
            
            conn.commit()
            
            return {
                "success": True,
                "history_id": history_id,
                "tracked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track component generation: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_optimization_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimization recommendations based on context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            asset_type = context.get("asset_type", "")
            target_format = context.get("target_format", "web")
            quality_requirements = context.get("quality_requirements", "standard")
            
            # Get relevant optimization presets
            cursor.execute('''
                SELECT preset_name, configuration, performance_metrics,
                       use_cases, success_rate
                FROM optimization_presets
                WHERE preset_type LIKE ? OR use_cases LIKE ?
                ORDER BY success_rate DESC
                LIMIT 10
            ''', (f"%{target_format}%", f"%{asset_type}%"))
            
            recommendations = []
            for row in cursor.fetchall():
                preset_name, config, metrics, use_cases, success_rate = row
                
                config_parsed = json.loads(config)
                metrics_parsed = json.loads(metrics) if metrics else {}
                use_cases_parsed = json.loads(use_cases) if use_cases else []
                
                # Calculate relevance score
                relevance = self._calculate_optimization_relevance(
                    context, use_cases_parsed, metrics_parsed
                )
                
                recommendations.append({
                    "preset_name": preset_name,
                    "configuration": config_parsed,
                    "performance_metrics": metrics_parsed,
                    "use_cases": use_cases_parsed,
                    "success_rate": success_rate,
                    "relevance_score": relevance,
                    "recommendation_reason": self._generate_optimization_reason(
                        context, preset_name, use_cases_parsed
                    )
                })
            
            # Sort by relevance and success rate
            recommendations.sort(
                key=lambda x: (x["relevance_score"] * 0.6 + x["success_rate"] * 0.4),
                reverse=True
            )
            
            return {
                "success": True,
                "context": context,
                "recommendations": recommendations[:5],
                "total_presets_analyzed": len(recommendations)
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimization recommendations: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def analyze_generation_trends(self) -> Dict[str, Any]:
        """Analyze image generation trends and patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Most successful asset types
            cursor.execute('''
                SELECT asset_type, AVG(quality_score) as avg_quality,
                       SUM(usage_count) as total_usage
                FROM image_gen_patterns
                GROUP BY asset_type
                ORDER BY avg_quality DESC
            ''')
            
            asset_type_performance = []
            for row in cursor.fetchall():
                asset_type_performance.append({
                    "asset_type": row[0],
                    "average_quality": row[1],
                    "total_usage": row[2]
                })
            
            # Provider preference trends
            cursor.execute('''
                SELECT provider_preferences, COUNT(*) as pattern_count,
                       AVG(quality_score) as avg_quality
                FROM image_gen_patterns
                WHERE usage_count > 5
                GROUP BY provider_preferences
            ''')
            
            provider_trends = {}
            for row in cursor.fetchall():
                prefs = json.loads(row[0]) if row[0] else {}
                for provider, score in prefs.items():
                    if provider not in provider_trends:
                        provider_trends[provider] = {
                            "usage_count": 0,
                            "quality_sum": 0
                        }
                    provider_trends[provider]["usage_count"] += row[1]
                    provider_trends[provider]["quality_sum"] += row[2]
            
            # Calculate provider averages
            provider_performance = []
            for provider, stats in provider_trends.items():
                if stats["usage_count"] > 0:
                    provider_performance.append({
                        "provider": provider,
                        "average_quality": stats["quality_sum"] / stats["usage_count"],
                        "total_patterns": stats["usage_count"]
                    })
            
            # Style transfer success rates
            cursor.execute('''
                SELECT target_aesthetic, AVG(success_rate) as avg_success,
                       SUM(usage_count) as total_usage
                FROM style_transfer_mappings
                GROUP BY target_aesthetic
                ORDER BY avg_success DESC
            ''')
            
            style_transfer_performance = []
            for row in cursor.fetchall():
                style_transfer_performance.append({
                    "target_aesthetic": row[0],
                    "average_success_rate": row[1],
                    "total_usage": row[2]
                })
            
            return {
                "success": True,
                "asset_type_performance": asset_type_performance,
                "provider_performance": provider_performance,
                "style_transfer_performance": style_transfer_performance,
                "analysis_timestamp": datetime.now().isoformat(),
                "insights": self._generate_generation_insights(
                    asset_type_performance, 
                    provider_performance,
                    style_transfer_performance
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze generation trends: {e}")
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def _calculate_token_similarity(self, tokens1: Dict, tokens2: Dict) -> float:
        """Calculate similarity between two design token sets"""
        similarity = 0.0
        factors = 0
        
        # Color similarity
        if "colors" in tokens1 and "colors" in tokens2:
            color_sim = self._compare_color_tokens(
                tokens1.get("colors", {}),
                tokens2.get("colors", {})
            )
            similarity += color_sim * 0.3
            factors += 0.3
        
        # Typography similarity
        if "typography" in tokens1 and "typography" in tokens2:
            typo_sim = self._compare_typography_tokens(
                tokens1.get("typography", {}),
                tokens2.get("typography", {})
            )
            similarity += typo_sim * 0.2
            factors += 0.2
        
        # Spacing similarity
        if "spacing" in tokens1 and "spacing" in tokens2:
            spacing_sim = self._compare_spacing_tokens(
                tokens1.get("spacing", {}),
                tokens2.get("spacing", {})
            )
            similarity += spacing_sim * 0.2
            factors += 0.2
        
        # Effects similarity
        if "effects" in tokens1 and "effects" in tokens2:
            effects_sim = self._compare_effects_tokens(
                tokens1.get("effects", {}),
                tokens2.get("effects", {})
            )
            similarity += effects_sim * 0.3
            factors += 0.3
        
        return similarity / factors if factors > 0 else 0.0
    
    def _compare_color_tokens(self, colors1: Dict, colors2: Dict) -> float:
        """Compare color token similarity"""
        if not colors1 or not colors2:
            return 0.0
        
        # Compare palettes
        palette1 = colors1.get("palette", {})
        palette2 = colors2.get("palette", {})
        
        common_colors = 0
        total_colors = len(set(palette1.keys()) | set(palette2.keys()))
        
        if total_colors == 0:
            return 0.0
        
        for key in palette1:
            if key in palette2:
                # Simple color matching - could be enhanced with color distance
                if palette1[key] == palette2[key]:
                    common_colors += 1
        
        return common_colors / total_colors
    
    def _compare_typography_tokens(self, typo1: Dict, typo2: Dict) -> float:
        """Compare typography token similarity"""
        if not typo1 or not typo2:
            return 0.0
        
        similarity = 0.0
        
        # Font family comparison
        fonts1 = set(typo1.get("font_families", {}).keys())
        fonts2 = set(typo2.get("font_families", {}).keys())
        
        if fonts1 and fonts2:
            common_fonts = len(fonts1 & fonts2)
            total_fonts = len(fonts1 | fonts2)
            similarity += (common_fonts / total_fonts) * 0.5
        
        # Font size comparison
        sizes1 = set(typo1.get("font_sizes", {}).keys())
        sizes2 = set(typo2.get("font_sizes", {}).keys())
        
        if sizes1 and sizes2:
            common_sizes = len(sizes1 & sizes2)
            total_sizes = len(sizes1 | sizes2)
            similarity += (common_sizes / total_sizes) * 0.5
        
        return similarity
    
    def _compare_spacing_tokens(self, spacing1: Dict, spacing2: Dict) -> float:
        """Compare spacing token similarity"""
        if not spacing1 or not spacing2:
            return 0.0
        
        # Compare margins and paddings
        margins1 = set(spacing1.get("margins", {}).keys())
        margins2 = set(spacing2.get("margins", {}).keys())
        
        paddings1 = set(spacing1.get("paddings", {}).keys())
        paddings2 = set(spacing2.get("paddings", {}).keys())
        
        all_spacing1 = margins1 | paddings1
        all_spacing2 = margins2 | paddings2
        
        if not all_spacing1 or not all_spacing2:
            return 0.0
        
        common_spacing = len(all_spacing1 & all_spacing2)
        total_spacing = len(all_spacing1 | all_spacing2)
        
        return common_spacing / total_spacing
    
    def _compare_effects_tokens(self, effects1: Dict, effects2: Dict) -> float:
        """Compare effects token similarity"""
        if not effects1 or not effects2:
            return 0.0
        
        similarity = 0.0
        factors = 0
        
        # Shadow comparison
        if "shadows" in effects1 and "shadows" in effects2:
            shadows1 = set(effects1.get("shadows", {}).keys())
            shadows2 = set(effects2.get("shadows", {}).keys())
            
            if shadows1 and shadows2:
                common_shadows = len(shadows1 & shadows2)
                total_shadows = len(shadows1 | shadows2)
                similarity += (common_shadows / total_shadows) * 0.5
                factors += 0.5
        
        # Border radius comparison
        if "border_radius" in effects1 and "border_radius" in effects2:
            radius1 = set(effects1.get("border_radius", {}).keys())
            radius2 = set(effects2.get("border_radius", {}).keys())
            
            if radius1 and radius2:
                common_radius = len(radius1 & radius2)
                total_radius = len(radius1 | radius2)
                similarity += (common_radius / total_radius) * 0.5
                factors += 0.5
        
        return similarity / factors if factors > 0 else 0.0
    
    def _calculate_optimization_relevance(self, context: Dict, 
                                        use_cases: List[str], 
                                        metrics: Dict) -> float:
        """Calculate how relevant an optimization preset is to the context"""
        relevance = 0.0
        
        # Asset type match
        asset_type = context.get("asset_type", "").lower()
        for use_case in use_cases:
            if asset_type in use_case.lower():
                relevance += 0.3
                break
        
        # Format match
        target_format = context.get("target_format", "").lower()
        for use_case in use_cases:
            if target_format in use_case.lower():
                relevance += 0.3
                break
        
        # Quality requirements match
        quality = context.get("quality_requirements", "standard")
        if metrics.get("quality_level", "").lower() == quality.lower():
            relevance += 0.2
        
        # Performance requirements
        if context.get("performance_critical") and metrics.get("compression_ratio", 0) > 50:
            relevance += 0.2
        
        return min(relevance, 1.0)
    
    def _generate_optimization_reason(self, context: Dict, 
                                    preset_name: str, 
                                    use_cases: List[str]) -> str:
        """Generate reason for optimization recommendation"""
        reasons = []
        
        asset_type = context.get("asset_type", "")
        if asset_type and any(asset_type.lower() in case.lower() for case in use_cases):
            reasons.append(f"Optimized for {asset_type} assets")
        
        target_format = context.get("target_format", "")
        if target_format and any(target_format.lower() in case.lower() for case in use_cases):
            reasons.append(f"Designed for {target_format} delivery")
        
        if "performance" in preset_name.lower():
            reasons.append("High performance optimization")
        
        if not reasons:
            reasons.append("Proven optimization preset")
        
        return "; ".join(reasons)
    
    def _generate_generation_insights(self, asset_performance: List[Dict],
                                    provider_performance: List[Dict],
                                    style_performance: List[Dict]) -> List[str]:
        """Generate insights from generation trend analysis"""
        insights = []
        
        # Best performing asset type
        if asset_performance:
            best_asset = max(asset_performance, key=lambda x: x["average_quality"])
            insights.append(
                f"Best performing asset type: {best_asset['asset_type']} "
                f"with {best_asset['average_quality']:.2f} quality score"
            )
        
        # Most reliable provider
        if provider_performance:
            best_provider = max(provider_performance, key=lambda x: x["average_quality"])
            insights.append(
                f"Most reliable provider: {best_provider['provider']} "
                f"with {best_provider['average_quality']:.2f} average quality"
            )
        
        # Most successful style transfer
        if style_performance:
            best_style = max(style_performance, key=lambda x: x["average_success_rate"])
            insights.append(
                f"Most successful style transfer: {best_style['target_aesthetic']} "
                f"with {best_style['average_success_rate']:.2%} success rate"
            )
        
        # Usage patterns
        if asset_performance:
            total_usage = sum(ap["total_usage"] for ap in asset_performance)
            insights.append(f"Total generation patterns tracked: {total_usage}")
        
        return insights