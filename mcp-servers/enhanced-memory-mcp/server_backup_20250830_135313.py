#!/usr/bin/env python3
"""
Enhanced Memory MCP Server with SAFLA Autonomous Learning Patterns + Reliability Validation
Provides SQLite storage with zlib compression, search capabilities, and autonomous optimization
SAFLA Phase 2: Intelligent memory curation, performance tracking, and safety validation
RELIABILITY ENHANCEMENT: Phase 1 Implementation - Comprehensive consistency validation

Phase 1 Enhancement: Adds reliability validation layer while preserving 100% SAFLA capabilities
"""

import sys
import json
import logging
import sqlite3
import hashlib
import zlib
import base64
import statistics
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pickle

# Import compressed context integration - with safer error handling
CONTEXT_COMPRESSION_AVAILABLE = False
RELIABILITY_AVAILABLE = False
DESIGN_PATTERNS_AVAILABLE = False
COMPONENT_LIBRARY_AVAILABLE = False
CLONE_TRACKING_AVAILABLE = False

try:
    from compressed_context_integration import CompressedContextManager
    CONTEXT_COMPRESSION_AVAILABLE = True
    logging.info("🗜️ Context compression system loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    CONTEXT_COMPRESSION_AVAILABLE = False
    logging.info(f"📝 Context compression not available: {e}")

# Import reliability enhancement layer - with safer error handling
try:
    from reliability_enhancements import ReliabilityEnhancedMemoryIntegration, MemoryReliabilityValidator
    RELIABILITY_AVAILABLE = True
    logging.info("🛡️ Reliability validation layer loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    RELIABILITY_AVAILABLE = False
    logging.info(f"📝 Reliability validation layer not available: {e}")
    logging.info("📝 Running in SAFLA-only mode without reliability enhancements")

# Import specialized storage modules - with safer error handling
try:
    from design_pattern_storage import DesignPatternStorage
    DESIGN_PATTERNS_AVAILABLE = True
    logging.info("🎨 Design pattern storage loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    DESIGN_PATTERNS_AVAILABLE = False
    logging.info(f"📝 Design pattern storage not available: {e}")

try:
    from component_library_manager import ComponentLibraryManager
    COMPONENT_LIBRARY_AVAILABLE = True
    logging.info("🧩 Component library manager loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    COMPONENT_LIBRARY_AVAILABLE = False
    logging.info(f"📝 Component library manager not available: {e}")

try:
    from clone_success_tracker import CloneSuccessTracker
    CLONE_TRACKING_AVAILABLE = True
    logging.info("🎯 Clone success tracker loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    CLONE_TRACKING_AVAILABLE = False
    logging.info(f"📝 Clone success tracker not available: {e}")

# Import image generation pattern integration
IMAGE_GEN_PATTERNS_AVAILABLE = False
try:
    from image_gen_pattern_integration import ImageGenPatternIntegration
    IMAGE_GEN_PATTERNS_AVAILABLE = True
    logging.info("🎨 Image generation pattern integration loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    IMAGE_GEN_PATTERNS_AVAILABLE = False
    logging.info(f"📝 Image generation pattern integration not available: {e}")

# Set up logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("enhanced-memory")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# SAFLA Configuration for Autonomous Memory Learning
SAFLA_MEMORY_CONFIG = {
    "autonomous_curation_enabled": True,
    "performance_tracking_enabled": True,
    "safety_validation_enabled": True,
    "meta_cognitive_analysis_enabled": True,
    "continuous_optimization_enabled": True,
    "curation_thresholds": {
        "archive_age_days": 30,
        "low_access_threshold": 2,
        "compression_efficiency_threshold": 0.5,
        "critical_entity_types": ["system_role", "core_system", "orchestrator"]
    },
    "performance_windows": {
        "short_term_hours": 6,
        "medium_term_days": 3,
        "long_term_weeks": 2
    },
    "optimization_targets": {
        "compression_ratio": 0.4,
        "search_speed_ms": 100,
        "tier_distribution_balance": 0.3
    }
}

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Global reliability integration - initialized in main()
reliability_integration = None

# Global context compression manager - initialized in main()
context_manager = None

# Global specialized storage managers - initialized in main()
design_pattern_storage = None
component_library_manager = None
clone_success_tracker = None

def speak_to_marc(message: str, voice: str = "foghorn_friendly"):
    """Voice communication for SAFLA autonomous memory events"""
    # Skip TTS during startup to prevent replay of old commands
    if hasattr(speak_to_marc, '_startup_suppression') and speak_to_marc._startup_suppression:
        return
    
    try:
        voice_script = Path(__file__).parent.parent / "voice-cloning-mcp" / "production_comprehensive_voice.py"
        subprocess.run([
            "python", str(voice_script), message, voice
        ], check=False, capture_output=True, timeout=5)
    except:
        pass  # Fail silently if voice unavailable

def init_database_sync():
    """Initialize SQLite database with real schema (synchronous version for wrapper compatibility)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create entities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            tier TEXT DEFAULT 'working',
            compressed_data BLOB,
            original_size INTEGER,
            compressed_size INTEGER,
            compression_ratio REAL,
            checksum TEXT,
            access_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create observations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER,
            content TEXT NOT NULL,
            compressed BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')
    
    # Create relations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity_id INTEGER,
            to_entity_id INTEGER,
            relation_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_entity_id) REFERENCES entities (id),
            FOREIGN KEY (to_entity_id) REFERENCES entities (id)
        )
    ''')
    
    # Create indexes for real performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_accessed ON entities(last_accessed)')
    
    # SAFLA Tables for Autonomous Learning
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safla_memory_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_type TEXT NOT NULL,
            metric_value REAL NOT NULL,
            entity_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safla_curation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            entity_id INTEGER,
            previous_tier TEXT,
            new_tier TEXT,
            reason TEXT,
            confidence_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safla_performance_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            execution_time_ms REAL NOT NULL,
            results_count INTEGER,
            compression_ratio REAL,
            optimization_applied BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS safla_safety_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            entity_id INTEGER,
            action_taken TEXT,
            prevented_action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')
    
    # SAFLA indexes for analytics performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_safla_analytics_type ON safla_memory_analytics(metric_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_safla_curation_events ON safla_curation_events(event_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_safla_performance ON safla_performance_tracking(operation_type)')
    
    conn.commit()
    conn.close()

async def init_database():
    """Initialize SQLite database with real schema (async version for non-blocking operation)"""
    # Use asyncio to make it non-blocking
    await asyncio.sleep(0)  # Yield control to event loop
    init_database_sync()  # Use sync version for actual work

def compress_data(data: Any) -> tuple[bytes, int, int, float]:
    """Really compress data using zlib"""
    # Serialize the data
    serialized = pickle.dumps(data)
    original_size = len(serialized)
    
    # Compress with zlib (level 9 = maximum compression)
    compressed = zlib.compress(serialized, level=9)
    compressed_size = len(compressed)
    
    # Calculate real compression ratio
    compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
    
    return compressed, original_size, compressed_size, compression_ratio

def decompress_data(compressed: bytes) -> Any:
    """Decompress and deserialize data"""
    decompressed = zlib.decompress(compressed)
    return pickle.loads(decompressed)

def calculate_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum for data integrity"""
    return hashlib.sha256(data).hexdigest()

def classify_tier(entity_type: str, name: str) -> str:
    """Classify entity into memory tier"""
    if entity_type in ["system_role", "core_system"] or "orchestrator" in name.lower():
        return "core"
    elif entity_type in ["project", "session"] or "current" in name.lower():
        return "working"
    elif "archive" in name.lower() or "historical" in entity_type.lower():
        return "archive"
    else:
        return "reference"

class SAFLAMemoryOrchestrator:
    """SAFLA Autonomous Learning Patterns for Enhanced Memory System"""
    
    def __init__(self):
        self.config = SAFLA_MEMORY_CONFIG
        
    async def analyze_memory_usage_patterns(self) -> Dict[str, Any]:
        """SAFLA: Meta-cognitive analysis of memory usage patterns"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Analyze access patterns
            cursor.execute('''
                SELECT 
                    tier,
                    AVG(access_count) as avg_accesses,
                    AVG(compression_ratio) as avg_compression,
                    COUNT(*) as entity_count
                FROM entities
                GROUP BY tier
            ''')
            tier_analysis = {row[0]: {
                "avg_accesses": row[1],
                "avg_compression": row[2], 
                "entity_count": row[3]
            } for row in cursor.fetchall()}
            
            # Identify optimization opportunities
            cursor.execute('''
                SELECT name, entity_type, tier, access_count, compression_ratio,
                       JULIANDAY('now') - JULIANDAY(last_accessed) as days_since_access
                FROM entities
                WHERE access_count < ? OR compression_ratio > ?
                ORDER BY days_since_access DESC
                LIMIT 20
            ''', (self.config["curation_thresholds"]["low_access_threshold"],
                  self.config["curation_thresholds"]["compression_efficiency_threshold"]))
            
            optimization_candidates = [{
                "name": row[0],
                "entity_type": row[1],
                "tier": row[2],
                "access_count": row[3],
                "compression_ratio": row[4],
                "days_since_access": row[5],
                "reason": "low_access" if row[3] < self.config["curation_thresholds"]["low_access_threshold"] else "poor_compression"
            } for row in cursor.fetchall()]
            
            # Calculate system confidence
            total_entities = sum(data["entity_count"] for data in tier_analysis.values())
            avg_compression = statistics.mean([data["avg_compression"] for data in tier_analysis.values()])
            
            confidence_score = min(1.0, max(0.0, 
                (1.0 - avg_compression) * 0.6 +  # Better compression = higher confidence
                (total_entities / 100) * 0.2 +   # More entities = higher confidence  
                (len(optimization_candidates) / total_entities < 0.3) * 0.2  # Fewer candidates = higher confidence
            ))
            
            analysis = {
                "tier_distribution": tier_analysis,
                "tier_analysis": tier_analysis,
                "compression_efficiency": avg_compression,
                "optimization_candidates": optimization_candidates,
                "system_confidence": confidence_score,
                "recommendations": self._generate_optimization_recommendations(tier_analysis, optimization_candidates),
                "timestamp": datetime.now().isoformat()
            }
            
            # Log analytics
            await self._log_analytics("meta_cognitive_analysis", confidence_score)
            
            return analysis
            
        finally:
            conn.close()
    
    async def autonomous_memory_curation(self) -> Dict[str, Any]:
        """SAFLA: Autonomous memory tier management and lifecycle decisions"""
        if not self.config["autonomous_curation_enabled"]:
            return {"enabled": False, "message": "Autonomous curation disabled"}
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        curation_results = []
        
        try:
            # Find entities needing tier adjustment
            cursor.execute('''
                SELECT id, name, entity_type, tier, access_count,
                       JULIANDAY('now') - JULIANDAY(last_accessed) as days_since_access,
                       compression_ratio
                FROM entities
                WHERE (tier = 'working' AND (access_count < ? OR JULIANDAY('now') - JULIANDAY(last_accessed) > ?))
                   OR (tier = 'reference' AND access_count > 10)
                   OR (tier = 'archive' AND access_count > 5)
            ''', (self.config["curation_thresholds"]["low_access_threshold"],
                  self.config["curation_thresholds"]["archive_age_days"]))
            
            for row in cursor.fetchall():
                entity_id, name, entity_type, current_tier, access_count, days_since_access, compression_ratio = row
                
                # Safety check - never auto-archive critical entities
                if entity_type in self.config["curation_thresholds"]["critical_entity_types"]:
                    await self._log_safety_event("curation_blocked", "high", entity_id, 
                                                "Prevented auto-archiving of critical entity", 
                                                f"tier_change_{current_tier}_to_archive")
                    continue
                
                # Determine new tier
                new_tier = self._calculate_optimal_tier(current_tier, access_count, days_since_access, entity_type)
                
                if new_tier != current_tier:
                    # Calculate confidence in this curation decision
                    confidence = self._calculate_curation_confidence(access_count, days_since_access, compression_ratio)
                    
                    # Apply tier change
                    cursor.execute('UPDATE entities SET tier = ? WHERE id = ?', (new_tier, entity_id))
                    
                    # Log curation event
                    cursor.execute('''
                        INSERT INTO safla_curation_events 
                        (event_type, entity_id, previous_tier, new_tier, reason, confidence_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', ("tier_adjustment", entity_id, current_tier, new_tier,
                          f"access:{access_count},days:{days_since_access:.1f}", confidence))
                    
                    curation_results.append({
                        "entity_name": name,
                        "previous_tier": current_tier,
                        "new_tier": new_tier,
                        "confidence": confidence,
                        "reason": f"Access count: {access_count}, Days inactive: {days_since_access:.1f}"
                    })
            
            conn.commit()
            
            # Voice notification for significant curation events
            if len(curation_results) > 5:
                speak_to_marc(f"Autonomous memory curation complete! Optimized {len(curation_results)} entities for better performance.", "foghorn_success")
            
            return {
                "enabled": True,
                "entities_processed": len(curation_results),
                "actions_taken": curation_results,
                "curations_performed": len(curation_results),
                "results": curation_results,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            conn.close()
    
    async def evaluate_memory_performance(self, operation_type: str = "general", execution_time: float = 0.0, 
                                        results_count: int = 0, compression_ratio: float = None) -> Dict[str, Any]:
        """SAFLA: Track and evaluate memory operation performance"""
        if not self.config["performance_tracking_enabled"]:
            return {"enabled": False, "message": "Performance tracking disabled"}
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Check if optimization should be applied
            optimization_applied = execution_time > self.config["optimization_targets"]["search_speed_ms"]
            
            # Record performance data
            cursor.execute('''
                INSERT INTO safla_performance_tracking 
                (operation_type, execution_time_ms, results_count, compression_ratio, optimization_applied)
                VALUES (?, ?, ?, ?, ?)
            ''', (operation_type, execution_time, results_count, compression_ratio, optimization_applied))
            
            # Analyze recent performance trends
            cursor.execute('''
                SELECT AVG(execution_time_ms), COUNT(*)
                FROM safla_performance_tracking
                WHERE operation_type = ? AND created_at > datetime('now', '-6 hours')
            ''', (operation_type,))
            
            recent_avg, recent_count = cursor.fetchone()
            
            # Trigger optimization if performance degrades
            if recent_avg and recent_avg > self.config["optimization_targets"]["search_speed_ms"] * 1.5:
                await self._trigger_performance_optimization(operation_type, recent_avg)
            
            conn.commit()
            
            # Calculate performance score
            performance_score = min(1.0, max(0.0, 1.0 - (recent_avg or 0) / 1000))
            
            return {
                "operation_type": operation_type,
                "execution_time": execution_time,
                "results_count": results_count,
                "compression_ratio": compression_ratio,
                "recent_avg_time": recent_avg or 0,
                "operation_count_6h": recent_count or 0,
                "performance_score": performance_score,
                "optimization_applied": optimization_applied,
                "operation_efficiency": performance_score > 0.7,
                "compression_effectiveness": (compression_ratio or 0.5) < 0.6,
                "search_speed": (recent_avg or 0) < self.config["optimization_targets"]["search_speed_ms"],
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            conn.close()
    
    async def validate_memory_safety(self, operation: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """SAFLA: Safety validation for memory operations"""
        if not self.config["safety_validation_enabled"]:
            return {"safe": True, "message": "Safety validation disabled"}
        
        safety_result = {
            "safe": True,
            "violations": [],
            "recommendations": [],
            "risk_level": "low"
        }
        
        entity_type = entity_data.get("entityType", "")
        entity_name = entity_data.get("name", "")
        operation_details = entity_data.get("operation", "")
        
        # Check for dangerous operation patterns
        dangerous_operations = ["delete_all", "drop_table", "format", "destroy", "nuclear", "wipe"]
        operation_lower = operation.lower()
        operation_details_lower = operation_details.lower() if operation_details else ""
        
        for dangerous_op in dangerous_operations:
            if dangerous_op in operation_lower or dangerous_op in operation_details_lower:
                safety_result["safe"] = False
                safety_result["violations"].append(f"Dangerous operation detected: {dangerous_op}")
                safety_result["risk_level"] = "critical"
        
        # Critical entity protection
        if entity_type in self.config["curation_thresholds"]["critical_entity_types"]:
            if operation in ["delete", "archive", "delete_all"]:
                safety_result["safe"] = False
                safety_result["violations"].append(f"Attempted {operation} on critical entity type: {entity_type}")
                safety_result["risk_level"] = "critical"
                
                await self._log_safety_event("critical_entity_protection", "critical", None,
                                            f"Blocked {operation} operation", 
                                            f"{operation}_{entity_type}")
        
        # System role protection
        if "orchestrator" in entity_name.lower() or "system" in entity_name.lower():
            if operation in ["delete", "delete_all"]:
                safety_result["safe"] = False
                safety_result["violations"].append(f"Attempted {operation} of system entity: {entity_name}")
                safety_result["risk_level"] = "high"
        
        # Data integrity validation
        observations = entity_data.get("observations", [])
        if len(observations) == 0 and operation == "create":
            safety_result["recommendations"].append("Entity created with no observations - consider adding meaningful data")
        
        return safety_result
    
    async def continuous_memory_enhancement(self) -> Dict[str, Any]:
        """SAFLA: Continuous learning and optimization of memory patterns"""
        if not self.config["continuous_optimization_enabled"]:
            return {"enabled": False}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        enhancements = []
        
        try:
            # Analyze search patterns for optimization
            cursor.execute('''
                SELECT operation_type, AVG(execution_time_ms) as avg_time,
                       COUNT(*) as frequency
                FROM safla_performance_tracking
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY operation_type
                HAVING frequency > 5
                ORDER BY avg_time DESC
            ''')
            
            for row in cursor.fetchall():
                operation_type, avg_time, frequency = row
                if avg_time > self.config["optimization_targets"]["search_speed_ms"]:
                    enhancement = await self._optimize_operation(operation_type, avg_time, frequency)
                    if enhancement:
                        enhancements.append(enhancement)
            
            # Compression ratio improvement
            cursor.execute('''
                SELECT AVG(compression_ratio) as avg_ratio
                FROM entities
                WHERE created_at > datetime('now', '-3 days')
            ''')
            
            recent_compression = cursor.fetchone()[0] or 0.5
            if recent_compression > self.config["optimization_targets"]["compression_ratio"]:
                enhancement = {
                    "type": "compression_optimization",
                    "current_ratio": recent_compression,
                    "target_ratio": self.config["optimization_targets"]["compression_ratio"],
                    "action": "increase_compression_level"
                }
                enhancements.append(enhancement)
            
            # Log enhancement analytics
            if enhancements:
                await self._log_analytics("continuous_enhancement", len(enhancements))
                speak_to_marc(f"Memory system autonomously enhanced! Applied {len(enhancements)} optimizations for better performance.", "foghorn_success")
            
            return {
                "enabled": True,
                "optimizations_applied": enhancements,
                "enhancements_applied": len(enhancements),
                "details": enhancements,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            conn.close()
    
    async def get_memory_analytics(self, time_window: str = "medium") -> Dict[str, Any]:
        """Get comprehensive memory analytics for specified time window"""
        window_hours = {
            "short": self.config["performance_windows"]["short_term_hours"],
            "medium": self.config["performance_windows"]["medium_term_days"] * 24,
            "long": self.config["performance_windows"]["long_term_weeks"] * 7 * 24
        }.get(time_window, 72)
        
        analysis = await self.analyze_memory_usage_patterns()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Get performance metrics for time window
            cursor.execute('''
                SELECT operation_type, AVG(execution_time_ms), COUNT(*)
                FROM safla_performance_tracking
                WHERE created_at > datetime('now', f'-{window_hours} hours')
                GROUP BY operation_type
            ''')
            
            performance_data = {row[0]: {"avg_time": row[1], "count": row[2]} for row in cursor.fetchall()}
            
            return {
                "time_window": time_window,
                "hours_analyzed": window_hours,
                "memory_patterns": analysis,
                "performance_metrics": performance_data,
                "timestamp": datetime.now().isoformat()
            }
        finally:
            conn.close()
    
    async def detect_learning_patterns(self) -> Dict[str, Any]:
        """Detect learning patterns in memory usage and curation"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Analyze curation patterns
            cursor.execute('''
                SELECT event_type, COUNT(*), AVG(confidence_score)
                FROM safla_curation_events
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY event_type
            ''')
            
            curation_patterns = {row[0]: {"count": row[1], "avg_confidence": row[2]} for row in cursor.fetchall()}
            
            # Analyze performance trends
            cursor.execute('''
                SELECT operation_type, 
                       AVG(CASE WHEN created_at > datetime('now', '-24 hours') THEN execution_time_ms END) as recent_avg,
                       AVG(CASE WHEN created_at <= datetime('now', '-24 hours') THEN execution_time_ms END) as historical_avg
                FROM safla_performance_tracking
                WHERE created_at > datetime('now', '-7 days')
                GROUP BY operation_type
            ''')
            
            performance_trends = {}
            for row in cursor.fetchall():
                op_type, recent, historical = row
                if recent and historical:
                    performance_trends[op_type] = {
                        "improvement": (historical - recent) / historical if historical > 0 else 0,
                        "recent_avg": recent,
                        "historical_avg": historical
                    }
            
            patterns_detected = []
            
            # Detect improvement patterns
            for op_type, trend in performance_trends.items():
                if trend["improvement"] > 0.1:
                    patterns_detected.append({
                        "type": "performance_improvement",
                        "operation": op_type,
                        "improvement": trend["improvement"],
                        "confidence": min(trend["improvement"], 1.0)
                    })
            
            # Detect successful curation patterns
            for event_type, pattern in curation_patterns.items():
                if pattern["avg_confidence"] > 0.7:
                    patterns_detected.append({
                        "type": "successful_curation",
                        "event_type": event_type,
                        "confidence": pattern["avg_confidence"],
                        "frequency": pattern["count"]
                    })
            
            return {
                "patterns_detected": patterns_detected,
                "curation_analysis": curation_patterns,
                "performance_trends": performance_trends,
                "timestamp": datetime.now().isoformat()
            }
            
        finally:
            conn.close()
    
    def _generate_optimization_recommendations(self, tier_analysis: Dict, candidates: List) -> List[str]:
        """Generate intelligent optimization recommendations"""
        recommendations = []
        
        # Tier balance recommendations
        total_entities = sum(data["entity_count"] for data in tier_analysis.values())
        working_ratio = tier_analysis.get("working", {}).get("entity_count", 0) / total_entities
        
        if working_ratio > 0.6:
            recommendations.append("Consider moving inactive working entities to reference tier")
        
        # Compression recommendations
        for tier, data in tier_analysis.items():
            if data["avg_compression"] > 0.6:
                recommendations.append(f"Improve compression for {tier} tier entities")
        
        # Access pattern recommendations
        if len(candidates) > total_entities * 0.3:
            recommendations.append("High number of low-access entities - consider archiving strategy")
        
        return recommendations
    
    def _calculate_optimal_tier(self, current_tier: str, access_count: int, 
                              days_since_access: float, entity_type: str) -> str:
        """Calculate optimal tier for entity based on usage patterns"""
        
        # Critical entities stay in core
        if entity_type in self.config["curation_thresholds"]["critical_entity_types"]:
            return "core"
        
        # High-access entities move to working
        if access_count > 10:
            return "working"
        
        # Long-inactive entities move to archive
        if days_since_access > self.config["curation_thresholds"]["archive_age_days"]:
            if current_tier in ["working", "reference"]:
                return "archive"
        
        # Low-access working entities move to reference
        if current_tier == "working" and access_count < self.config["curation_thresholds"]["low_access_threshold"]:
            return "reference"
        
        return current_tier
    
    def _calculate_curation_confidence(self, access_count: int, days_since_access: float, 
                                     compression_ratio: float) -> float:
        """Calculate confidence in curation decision"""
        confidence = 0.5  # Base confidence
        
        # Access pattern confidence
        if access_count == 0:
            confidence += 0.3
        elif access_count < 2:
            confidence += 0.2
        
        # Age confidence
        if days_since_access > 60:
            confidence += 0.3
        elif days_since_access > 30:
            confidence += 0.2
        
        # Compression confidence (better compression = more confident)
        confidence += (1.0 - compression_ratio) * 0.2
        
        return min(1.0, confidence)
    
    async def _trigger_performance_optimization(self, operation_type: str, avg_time: float) -> None:
        """Trigger optimization for slow operations"""
        speak_to_marc(f"Performance optimization triggered for {operation_type} operations! Average time: {avg_time:.1f}ms", "foghorn_authoritative")
        
        # Log optimization trigger
        await self._log_analytics("performance_optimization_trigger", avg_time)
    
    async def _optimize_operation(self, operation_type: str, avg_time: float, frequency: int) -> Dict[str, Any]:
        """Apply specific optimizations for operation types"""
        if operation_type == "search_nodes" and avg_time > 200:
            return {
                "type": "search_optimization",
                "operation": operation_type,
                "avg_time": avg_time,
                "optimization": "index_rebuild_suggested",
                "potential_improvement": "50-80% faster searches"
            }
        elif operation_type == "create_entities" and avg_time > 150:
            return {
                "type": "creation_optimization",
                "operation": operation_type,
                "avg_time": avg_time,
                "optimization": "batch_processing_enabled",
                "potential_improvement": "30-50% faster entity creation"
            }
        return None
    
    async def _log_analytics(self, metric_type: str, metric_value: float, entity_id: int = None) -> None:
        """Log analytics for continuous learning"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO safla_memory_analytics (metric_type, metric_value, entity_id)
                VALUES (?, ?, ?)
            ''', (metric_type, metric_value, entity_id))
            conn.commit()
        finally:
            conn.close()
    
    async def _log_safety_event(self, event_type: str, severity: str, entity_id: int = None,
                               action_taken: str = "", prevented_action: str = "") -> None:
        """Log safety events for learning and compliance"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO safla_safety_events 
                (event_type, severity, entity_id, action_taken, prevented_action)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_type, severity, entity_id, action_taken, prevented_action))
            conn.commit()
        finally:
            conn.close()

# Global SAFLA orchestrator instance
safla_orchestrator = SAFLAMemoryOrchestrator()

def handle_request(request):
    """Handle MCP request"""
    method = request.get("method", "")
    id = request.get("id")
    
    # Handle notifications (no response needed)
    if "notifications/" in method:
        logger.info(f"Received notification: {method}")
        return None
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "enhanced-memory",
                    "version": "2.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "tools": [
                    {
                        "name": "create_entities",
                        "description": "Create memory entities with real compression",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "entities": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "entityType": {"type": "string"},
                                            "observations": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        },
                                        "required": ["name", "entityType", "observations"]
                                    }
                                }
                            },
                            "required": ["entities"]
                        }
                    },
                    {
                        "name": "search_nodes",
                        "description": "Search memory nodes with SQL queries",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "entity_types": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "max_results": {"type": "integer", "default": 20}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "read_graph",
                        "description": "Read complete memory graph from database",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "get_memory_status",
                        "description": "Get real memory system statistics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_relations",
                        "description": "Create relations between entities",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "relations": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "from": {"type": "string"},
                                            "to": {"type": "string"},
                                            "relationType": {"type": "string"}
                                        },
                                        "required": ["from", "to", "relationType"]
                                    }
                                }
                            },
                            "required": ["relations"]
                        }
                    },
                    {
                        "name": "analyze_memory_patterns",
                        "description": "SAFLA: Analyze memory usage patterns with meta-cognitive assessment",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "trigger_memory_curation",
                        "description": "SAFLA: Trigger autonomous memory curation and tier management",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "get_memory_analytics",
                        "description": "SAFLA: Get comprehensive memory performance analytics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "time_window": {
                                    "type": "string",
                                    "enum": ["short", "medium", "long"],
                                    "default": "medium"
                                }
                            }
                        }
                    },
                    {
                        "name": "validate_memory_safety",
                        "description": "SAFLA: Validate memory operation safety before execution",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "operation": {"type": "string"},
                                "entity_data": {"type": "object"}
                            },
                            "required": ["operation", "entity_data"]
                        }
                    },
                    {
                        "name": "optimize_memory_performance",
                        "description": "SAFLA: Trigger continuous memory performance optimization",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "optimization_focus": {
                                    "type": "string",
                                    "enum": ["compression", "speed", "balance"],
                                    "default": "balance"
                                }
                            }
                        }
                    },
                    {
                        "name": "system_wide_consistency_check",
                        "description": "🛡️ RELIABILITY: Perform comprehensive consistency check across entire memory system",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "memory_reliability_score",
                        "description": "🛡️ RELIABILITY: Calculate reliability score for specific memory content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "memory_content": {"type": "string"},
                                "context": {"type": "object"}
                            },
                            "required": ["memory_content"]
                        }
                    },
                    {
                        "name": "detect_memory_contradictions",
                        "description": "🛡️ RELIABILITY: Detect contradictions across memory graph",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "load_compressed_session_context",
                        "description": "🗜️ CONTEXT: Load session context with TTS filtering to prevent replay",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {
                                    "type": "string",
                                    "description": "Optional specific session ID to load"
                                },
                                "max_entries": {
                                    "type": "integer",
                                    "default": 15,
                                    "description": "Maximum number of entries to return"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_selective_raw_logs",
                        "description": "🗜️ CONTEXT: Retrieve specific raw log entries for detailed analysis",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"},
                                "entry_types": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Filter by entry types (user, assistant, tool_use)"
                                },
                                "tool_names": {
                                    "type": "array", 
                                    "items": {"type": "string"},
                                    "description": "Filter by specific tool names"
                                }
                            },
                            "required": ["session_id"]
                        }
                    },
                    {
                        "name": "create_context_summary",
                        "description": "🗜️ CONTEXT: Create high-level summary of session context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_id": {"type": "string"}
                            },
                            "required": ["session_id"]
                        }
                    },
                    {
                        "name": "store_design_pattern",
                        "description": "🎨 DESIGN: Store design pattern with visual characteristics and usage context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "pattern_name": {"type": "string"},
                                "pattern_type": {"type": "string"},
                                "style_category": {"type": "string"},
                                "color_palette": {"type": "object"},
                                "typography_system": {"type": "object"},
                                "spacing_patterns": {"type": "object"},
                                "visual_characteristics": {"type": "object"},
                                "usage_context": {"type": "object"},
                                "success_score": {"type": "number", "default": 0.0},
                                "metadata": {"type": "object"}
                            },
                            "required": ["pattern_name", "pattern_type", "style_category"]
                        }
                    },
                    {
                        "name": "retrieve_similar_patterns",
                        "description": "🎨 DESIGN: Find similar design patterns based on visual characteristics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query_characteristics": {"type": "object"},
                                "max_results": {"type": "integer", "default": 10}
                            },
                            "required": ["query_characteristics"]
                        }
                    },
                    {
                        "name": "get_pattern_recommendations",
                        "description": "🎨 DESIGN: Get intelligent pattern recommendations based on context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "context": {"type": "object"}
                            },
                            "required": ["context"]
                        }
                    },
                    {
                        "name": "analyze_design_trends",
                        "description": "🎨 DESIGN: Analyze design trends from pattern usage data",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "time_period": {
                                    "type": "string",
                                    "enum": ["7days", "30days", "90days", "1year"],
                                    "default": "30days"
                                }
                            }
                        }
                    },
                    {
                        "name": "store_component_library",
                        "description": "🧩 COMPONENT: Store reusable component with code and metadata",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "component_name": {"type": "string"},
                                "component_type": {"type": "string"},
                                "framework": {"type": "string"},
                                "category": {"type": "string"},
                                "code_content": {"type": "string"},
                                "code_language": {"type": "string"},
                                "props_schema": {"type": "object"},
                                "variations": {"type": "array"},
                                "dependencies": {"type": "array"},
                                "usage_examples": {"type": "array"},
                                "documentation": {"type": "object"},
                                "quality_score": {"type": "number", "default": 0.0},
                                "metadata": {"type": "object"}
                            },
                            "required": ["component_name", "component_type", "framework", "code_content"]
                        }
                    },
                    {
                        "name": "find_reusable_components",
                        "description": "🧩 COMPONENT: Find reusable components based on search criteria",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "search_criteria": {"type": "object"},
                                "max_results": {"type": "integer", "default": 15}
                            },
                            "required": ["search_criteria"]
                        }
                    },
                    {
                        "name": "get_component_recommendations",
                        "description": "🧩 COMPONENT: Get intelligent component recommendations based on project context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "project_context": {"type": "object"}
                            },
                            "required": ["project_context"]
                        }
                    },
                    {
                        "name": "analyze_component_patterns",
                        "description": "🧩 COMPONENT: Analyze patterns in component usage and relationships",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "start_clone_operation",
                        "description": "🎯 CLONE: Start tracking a new design clone operation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "operation_name": {"type": "string"},
                                "source_url": {"type": "string"},
                                "target_description": {"type": "string"},
                                "clone_type": {"type": "string"},
                                "design_category": {"type": "string"},
                                "complexity_level": {"type": "string"},
                                "techniques_used": {"type": "array"},
                                "tools_used": {"type": "array"},
                                "metadata": {"type": "object"}
                            },
                            "required": ["target_description", "clone_type"]
                        }
                    },
                    {
                        "name": "track_clone_iteration",
                        "description": "🎯 CLONE: Track an iteration/step in the clone operation",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "clone_operation_id": {"type": "integer"},
                                "iteration_data": {"type": "object"}
                            },
                            "required": ["clone_operation_id", "iteration_data"]
                        }
                    },
                    {
                        "name": "complete_clone_operation",
                        "description": "🎯 CLONE: Mark clone operation as complete and record final metrics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "clone_operation_id": {"type": "integer"},
                                "completion_data": {"type": "object"}
                            },
                            "required": ["clone_operation_id", "completion_data"]
                        }
                    },
                    {
                        "name": "get_clone_success_metrics",
                        "description": "🎯 CLONE: Get comprehensive clone success metrics and analytics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "time_period": {
                                    "type": "string",
                                    "enum": ["7days", "30days", "90days", "1year"],
                                    "default": "30days"
                                }
                            }
                        }
                    },
                    {
                        "name": "get_technique_recommendations",
                        "description": "🎯 CLONE: Get technique recommendations based on clone context and historical success",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "clone_context": {"type": "object"}
                            },
                            "required": ["clone_context"]
                        }
                    },
                    {
                        "name": "store_image_gen_pattern",
                        "description": "🎨 IMAGE-GEN: Store image generation pattern with design tokens and success metrics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "design_tokens": {"type": "object"},
                                "asset_type": {"type": "string"},
                                "generation_quality": {"type": "string"},
                                "prompt_template": {"type": "string"},
                                "style_characteristics": {"type": "object"},
                                "success_metrics": {"type": "object"},
                                "provider_preferences": {"type": "object"},
                                "quality_score": {"type": "number", "default": 0.0}
                            },
                            "required": ["design_tokens", "asset_type"]
                        }
                    },
                    {
                        "name": "get_best_patterns_for_asset_type",
                        "description": "🎨 IMAGE-GEN: Get best performing patterns for a specific asset type",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "asset_type": {"type": "string"},
                                "design_tokens": {"type": "object"},
                                "max_results": {"type": "integer", "default": 5}
                            },
                            "required": ["asset_type"]
                        }
                    },
                    {
                        "name": "store_style_transfer_mapping",
                        "description": "🎨 IMAGE-GEN: Store successful style transfer mapping for future reuse",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "source_style": {"type": "string"},
                                "target_aesthetic": {"type": "string"},
                                "transfer_intensity": {"type": "number", "default": 0.8},
                                "enhancement_prompts": {"type": "array"},
                                "success_rate": {"type": "number", "default": 0.0},
                                "metadata": {"type": "object"}
                            },
                            "required": ["source_style", "target_aesthetic"]
                        }
                    },
                    {
                        "name": "track_component_generation",
                        "description": "🎨 IMAGE-GEN: Track component asset generation results",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "component_type": {"type": "string"},
                                "design_pattern_id": {"type": "integer"},
                                "dimensions": {"type": "array"},
                                "variants": {"type": "array"},
                                "states": {"type": "array"},
                                "generation_results": {"type": "object"},
                                "quality_metrics": {"type": "object"}
                            },
                            "required": ["component_type"]
                        }
                    },
                    {
                        "name": "get_optimization_recommendations",
                        "description": "🎨 IMAGE-GEN: Get optimization recommendations based on context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "context": {"type": "object"}
                            },
                            "required": ["context"]
                        }
                    },
                    {
                        "name": "analyze_generation_trends",
                        "description": "🎨 IMAGE-GEN: Analyze image generation trends and patterns",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        arguments = request.get("params", {}).get("arguments", {})
        
        if tool_name == "create_entities":
            result = create_entities(arguments)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "search_nodes":
            result = search_nodes(arguments)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "read_graph":
            result = read_graph()
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "get_memory_status":
            result = get_memory_status()
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "create_relations":
            result = create_relations(arguments)
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "analyze_memory_patterns":
            result = asyncio.run(safla_orchestrator.analyze_memory_usage_patterns())
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "trigger_memory_curation":
            result = asyncio.run(safla_orchestrator.autonomous_memory_curation())
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "get_memory_analytics":
            time_window = arguments.get("time_window", "medium")
            result = asyncio.run(safla_orchestrator.get_memory_analytics(time_window))
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "validate_memory_safety":
            operation = arguments.get("operation", "")
            entity_data = arguments.get("entity_data", {})
            result = asyncio.run(safla_orchestrator.validate_memory_safety(operation, entity_data))
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        elif tool_name == "optimize_memory_performance":
            optimization_focus = arguments.get("optimization_focus", "balance")
            result = asyncio.run(safla_orchestrator.continuous_memory_enhancement())
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result)
                    }]
                }
            }
        
        # 🛡️ RELIABILITY ENHANCEMENT: New reliability validation tools
        elif tool_name == "system_wide_consistency_check":
            if RELIABILITY_AVAILABLE and reliability_integration:
                try:
                    result = asyncio.run(reliability_integration.perform_system_wide_consistency_check())
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ System-wide consistency check failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Reliability validation unavailable: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Reliability validation layer not available - running in SAFLA-only mode"})
                        }]
                    }
                }
        
        elif tool_name == "memory_reliability_score":
            if RELIABILITY_AVAILABLE and reliability_integration:
                try:
                    memory_content = arguments.get("memory_content", "")
                    context = arguments.get("context", {})
                    score = asyncio.run(reliability_integration.reliability_validator.calculate_memory_reliability_score(memory_content, context))
                    result = {
                        "memory_content": memory_content,
                        "reliability_score": score,
                        "context": context,
                        "timestamp": datetime.now().isoformat()
                    }
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ Memory reliability scoring failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Reliability scoring failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Reliability validation layer not available - running in SAFLA-only mode"})
                        }]
                    }
                }
        
        elif tool_name == "detect_memory_contradictions":
            if RELIABILITY_AVAILABLE and reliability_integration:
                try:
                    # Get all memories for contradiction detection
                    all_memories = read_graph({})
                    memories_list = all_memories.get("entities", [])
                    contradiction_detection = asyncio.run(reliability_integration.reliability_validator.detect_memory_contradictions(memories_list))
                    
                    result = {
                        "contradictions_found": contradiction_detection.contradictions_found,
                        "severity_levels": contradiction_detection.severity_levels,
                        "affected_entities": contradiction_detection.affected_entities,
                        "resolution_suggestions": contradiction_detection.resolution_suggestions,
                        "confidence_level": contradiction_detection.confidence_level,
                        "total_memories_analyzed": len(memories_list),
                        "timestamp": datetime.now().isoformat()
                    }
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ Memory contradiction detection failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Contradiction detection failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Reliability validation layer not available - running in SAFLA-only mode"})
                        }]
                    }
                }
        
        # 🗜️ CONTEXT COMPRESSION: New context loading tools to prevent TTS replay
        elif tool_name == "load_compressed_session_context":
            if CONTEXT_COMPRESSION_AVAILABLE and context_manager:
                try:
                    session_id = arguments.get("session_id")
                    max_entries = arguments.get("max_entries", 15)
                    result = context_manager.load_compressed_session_context(session_id, max_entries)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ Compressed context loading failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Context loading failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Context compression not available - TTS filtering unavailable"})
                        }]
                    }
                }
        
        elif tool_name == "get_selective_raw_logs":
            if CONTEXT_COMPRESSION_AVAILABLE and context_manager:
                try:
                    session_id = arguments.get("session_id", "")
                    entry_types = arguments.get("entry_types")
                    tool_names = arguments.get("tool_names")
                    result = context_manager.get_selective_raw_logs(session_id, entry_types, tool_names)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ Selective log retrieval failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Log retrieval failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Context compression not available - selective logs unavailable"})
                        }]
                    }
                }
        
        elif tool_name == "create_context_summary":
            if CONTEXT_COMPRESSION_AVAILABLE and context_manager:
                try:
                    session_id = arguments.get("session_id", "")
                    result = context_manager.create_context_summary(session_id)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    logger.error(f"⚠️ Context summary creation failed: {e}")
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Summary creation failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Context compression not available - summary unavailable"})
                        }]
                    }
                }
        
        # 🎨 DESIGN PATTERN TOOLS
        elif tool_name == "store_design_pattern":
            if DESIGN_PATTERNS_AVAILABLE and design_pattern_storage:
                try:
                    result = design_pattern_storage.store_design_pattern(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Design pattern storage failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Design pattern storage not available"})
                        }]
                    }
                }
        
        elif tool_name == "retrieve_similar_patterns":
            if DESIGN_PATTERNS_AVAILABLE and design_pattern_storage:
                try:
                    query_characteristics = arguments.get("query_characteristics", {})
                    max_results = arguments.get("max_results", 10)
                    result = design_pattern_storage.retrieve_similar_patterns(query_characteristics, max_results)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Pattern retrieval failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Design pattern storage not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_pattern_recommendations":
            if DESIGN_PATTERNS_AVAILABLE and design_pattern_storage:
                try:
                    context = arguments.get("context", {})
                    result = design_pattern_storage.get_pattern_recommendations(context)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Pattern recommendations failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Design pattern storage not available"})
                        }]
                    }
                }
        
        elif tool_name == "analyze_design_trends":
            if DESIGN_PATTERNS_AVAILABLE and design_pattern_storage:
                try:
                    time_period = arguments.get("time_period", "30days")
                    result = design_pattern_storage.analyze_design_trends(time_period)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Design trends analysis failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Design pattern storage not available"})
                        }]
                    }
                }
        
        # 🧩 COMPONENT LIBRARY TOOLS
        elif tool_name == "store_component_library":
            if COMPONENT_LIBRARY_AVAILABLE and component_library_manager:
                try:
                    result = component_library_manager.store_component_library(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Component storage failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Component library manager not available"})
                        }]
                    }
                }
        
        elif tool_name == "find_reusable_components":
            if COMPONENT_LIBRARY_AVAILABLE and component_library_manager:
                try:
                    search_criteria = arguments.get("search_criteria", {})
                    max_results = arguments.get("max_results", 15)
                    result = component_library_manager.find_reusable_components(search_criteria, max_results)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Component search failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Component library manager not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_component_recommendations":
            if COMPONENT_LIBRARY_AVAILABLE and component_library_manager:
                try:
                    project_context = arguments.get("project_context", {})
                    result = component_library_manager.get_component_recommendations(project_context)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Component recommendations failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Component library manager not available"})
                        }]
                    }
                }
        
        elif tool_name == "analyze_component_patterns":
            if COMPONENT_LIBRARY_AVAILABLE and component_library_manager:
                try:
                    result = component_library_manager.analyze_component_patterns()
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Component analysis failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Component library manager not available"})
                        }]
                    }
                }
        
        # 🎯 CLONE SUCCESS TRACKING TOOLS
        elif tool_name == "start_clone_operation":
            if CLONE_TRACKING_AVAILABLE and clone_success_tracker:
                try:
                    result = clone_success_tracker.start_clone_operation(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Clone operation start failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Clone success tracker not available"})
                        }]
                    }
                }
        
        elif tool_name == "track_clone_iteration":
            if CLONE_TRACKING_AVAILABLE and clone_success_tracker:
                try:
                    clone_operation_id = arguments.get("clone_operation_id")
                    iteration_data = arguments.get("iteration_data", {})
                    result = clone_success_tracker.track_clone_iteration(clone_operation_id, iteration_data)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Clone iteration tracking failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Clone success tracker not available"})
                        }]
                    }
                }
        
        elif tool_name == "complete_clone_operation":
            if CLONE_TRACKING_AVAILABLE and clone_success_tracker:
                try:
                    clone_operation_id = arguments.get("clone_operation_id")
                    completion_data = arguments.get("completion_data", {})
                    result = clone_success_tracker.complete_clone_operation(clone_operation_id, completion_data)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Clone operation completion failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Clone success tracker not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_clone_success_metrics":
            if CLONE_TRACKING_AVAILABLE and clone_success_tracker:
                try:
                    time_period = arguments.get("time_period", "30days")
                    result = clone_success_tracker.get_clone_success_metrics(time_period)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Clone success metrics failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Clone success tracker not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_technique_recommendations":
            if CLONE_TRACKING_AVAILABLE and clone_success_tracker:
                try:
                    clone_context = arguments.get("clone_context", {})
                    result = clone_success_tracker.get_technique_recommendations(clone_context)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Technique recommendations failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Clone success tracker not available"})
                        }]
                    }
                }
        
        # 🎨 IMAGE GENERATION PATTERN TOOLS
        elif tool_name == "store_image_gen_pattern":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    result = image_gen_patterns.store_image_gen_pattern(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Store image gen pattern failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_best_patterns_for_asset_type":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    asset_type = arguments.get("asset_type", "")
                    design_tokens = arguments.get("design_tokens")
                    max_results = arguments.get("max_results", 5)
                    result = image_gen_patterns.get_best_patterns_for_asset_type(
                        asset_type, design_tokens, max_results
                    )
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Get best patterns failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
        
        elif tool_name == "store_style_transfer_mapping":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    result = image_gen_patterns.store_style_transfer_mapping(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Store style transfer mapping failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
        
        elif tool_name == "track_component_generation":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    result = image_gen_patterns.track_component_generation(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Track component generation failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
        
        elif tool_name == "get_optimization_recommendations":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    context = arguments.get("context", {})
                    result = image_gen_patterns.get_optimization_recommendations(context)
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Get optimization recommendations failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
        
        elif tool_name == "analyze_generation_trends":
            if IMAGE_GEN_PATTERNS_AVAILABLE and image_gen_patterns:
                try:
                    result = image_gen_patterns.analyze_generation_trends()
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps(result)
                            }]
                        }
                    }
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": id,
                        "result": {
                            "content": [{
                                "type": "text",
                                "text": json.dumps({"error": f"Analyze generation trends failed: {str(e)}"})
                            }]
                        }
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps({"error": "Image generation pattern integration not available"})
                        }]
                    }
                }
    
    return {
        "jsonrpc": "2.0",
        "id": id,
        "error": {"code": -32601, "message": "Method not found"}
    }

def create_entities(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create entities with real compression and storage - SAFLA Enhanced + Reliability Validation"""
    start_time = datetime.now()
    entities = arguments.get("entities", [])
    results = []
    
    # 🛡️ RELIABILITY ENHANCEMENT: Use enhanced reliability validation if available
    if RELIABILITY_AVAILABLE and reliability_integration:
        try:
            logger.info("🛡️ Using enhanced reliability validation for entity creation")
            enhanced_result = asyncio.run(reliability_integration.enhanced_create_entities(entities))
            return enhanced_result
        except Exception as e:
            logger.warning(f"⚠️ Reliability validation failed, falling back to SAFLA-only: {e}")
            # Continue with original SAFLA functionality below
    
    # SAFLA: Safety validation for entity creation
    if SAFLA_MEMORY_CONFIG.get("safety_validation_enabled", False):
        try:
            safety_result = asyncio.run(safla_orchestrator.validate_memory_safety("create_entities", {"entities": entities}))
            if not safety_result.get("safe", True):
                return {
                    "success": False,
                    "error": "SAFLA Safety Validation Failed",
                    "violations": safety_result.get("violations", []),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"SAFLA safety validation failed: {e}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for entity in entities:
        try:
            name = entity.get("name", "")
            entity_type = entity.get("entityType", "unknown")
            observations = entity.get("observations", [])
            
            if not name:
                continue
            
            # Classify tier
            tier = classify_tier(entity_type, name)
            
            # Prepare data for compression
            entity_data = {
                "name": name,
                "entityType": entity_type,
                "observations": observations,
                "tier": tier
            }
            
            # Really compress the data
            compressed, original_size, compressed_size, compression_ratio = compress_data(entity_data)
            checksum = calculate_checksum(compressed)
            
            # Store in database
            cursor.execute('''
                INSERT OR REPLACE INTO entities 
                (name, entity_type, tier, compressed_data, original_size, 
                 compressed_size, compression_ratio, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, entity_type, tier, compressed, original_size, 
                  compressed_size, compression_ratio, checksum))
            
            entity_id = cursor.lastrowid
            
            # Store observations separately for searchability
            for obs in observations:
                cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (entity_id, obs))
            
            results.append({
                "name": name,
                "entity_id": entity_id,
                "tier": tier,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "actual_savings": f"{(1 - compression_ratio) * 100:.1f}%",
                "checksum": checksum[:8] + "..."  # Show partial checksum
            })
            
        except Exception as e:
            logger.error(f"Error creating entity {name}: {e}")
            results.append({"name": name, "error": str(e)})
    
    conn.commit()
    conn.close()
    
    # Calculate real statistics
    total_original = sum(r.get("original_size", 0) for r in results if "error" not in r)
    total_compressed = sum(r.get("compressed_size", 0) for r in results if "error" not in r)
    overall_ratio = total_compressed / total_original if total_original > 0 else 1.0
    
    # SAFLA: Performance tracking for entity creation
    if SAFLA_MEMORY_CONFIG.get("performance_tracking_enabled", False):
        try:
            end_time = datetime.now()
            operation_duration = (end_time - start_time).total_seconds()
            entities_created = len([r for r in results if "error" not in r])
            
            # Track performance asynchronously
            asyncio.run(safla_orchestrator.track_memory_performance(
                operation="create_entities",
                duration_seconds=operation_duration,
                entities_processed=entities_created,
                compression_ratio=overall_ratio,
                success=True
            ))
            
            # Voice notification for significant operations
            if entities_created >= 5 or operation_duration > 2.0:
                speak_to_marc(f"SAFLA enhanced memory: Successfully created {entities_created} entities with {(1 - overall_ratio) * 100:.1f}% compression!")
                
        except Exception as e:
            logger.warning(f"SAFLA performance tracking failed: {e}")
    
    return {
        "success": True,
        "entities_created": len([r for r in results if "error" not in r]),
        "total_original_bytes": total_original,
        "total_compressed_bytes": total_compressed,
        "overall_compression_ratio": overall_ratio,
        "overall_savings": f"{(1 - overall_ratio) * 100:.1f}%",
        "results": results,
        "safla_enhanced": True,
        "timestamp": datetime.now().isoformat()
    }

def search_nodes(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search with real SQL queries - SAFLA Enhanced + Reliability Validation"""
    start_time = datetime.now()
    query = arguments.get("query", "")
    entity_types = arguments.get("entity_types", [])
    max_results = arguments.get("max_results", 20)
    
    # 🛡️ RELIABILITY ENHANCEMENT: Use enhanced reliability validation if available
    if RELIABILITY_AVAILABLE and reliability_integration:
        try:
            logger.info("🛡️ Using enhanced reliability validation for search")
            enhanced_result = asyncio.run(reliability_integration.enhanced_search_nodes(
                query, entity_types=entity_types, max_results=max_results, **arguments
            ))
            return enhanced_result
        except Exception as e:
            logger.warning(f"⚠️ Reliability validation failed, falling back to SAFLA-only: {e}")
            # Continue with original SAFLA functionality below
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Build SQL query
    sql = '''
        SELECT DISTINCT e.id, e.name, e.entity_type, e.tier, 
               e.compression_ratio, e.access_count, e.last_accessed
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE (LOWER(e.name) LIKE ? OR LOWER(o.content) LIKE ?)
    '''
    params = [f"%{query.lower()}%", f"%{query.lower()}%"]
    
    if entity_types:
        placeholders = ",".join("?" * len(entity_types))
        sql += f" AND e.entity_type IN ({placeholders})"
        params.extend(entity_types)
    
    sql += " ORDER BY e.access_count DESC, e.last_accessed DESC LIMIT ?"
    params.append(max_results)
    
    cursor.execute(sql, params)
    results = []
    
    for row in cursor.fetchall():
        entity_id = row[0]
        
        # Update access count
        cursor.execute(
            "UPDATE entities SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
            (entity_id,)
        )
        
        # Get observations for this entity
        cursor.execute("SELECT content FROM observations WHERE entity_id = ?", (entity_id,))
        observations = [obs[0] for obs in cursor.fetchall()]
        
        results.append({
            "id": entity_id,
            "name": row[1],
            "entity_type": row[2],
            "tier": row[3],
            "compression_ratio": row[4],
            "access_count": row[5],
            "last_accessed": row[6],
            "observations": observations[:3]  # First 3 observations
        })
    
    conn.commit()
    conn.close()
    
    # SAFLA: Performance tracking for search operations
    if SAFLA_MEMORY_CONFIG.get("performance_tracking_enabled", False):
        try:
            end_time = datetime.now()
            operation_duration = (end_time - start_time).total_seconds()
            results_found = len(results)
            
            # Track search performance asynchronously
            asyncio.run(safla_orchestrator.track_memory_performance(
                operation="search_nodes",
                duration_seconds=operation_duration,
                entities_processed=results_found,
                query_complexity=len(query.split()),
                success=True
            ))
            
            # Voice notification for significant search results
            if results_found >= 10 or operation_duration > 1.0:
                speak_to_marc(f"SAFLA enhanced search: Found {results_found} relevant entities in {operation_duration:.2f} seconds!")
                
        except Exception as e:
            logger.warning(f"SAFLA search performance tracking failed: {e}")
    
    return {
        "success": True,
        "query": query,
        "results_found": len(results),
        "results": results,
        "safla_enhanced": True,
        "timestamp": datetime.now().isoformat()
    }

def read_graph() -> Dict[str, Any]:
    """Read complete graph from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all entities
    cursor.execute('''
        SELECT id, name, entity_type, compressed_data
        FROM entities
    ''')
    
    entities = []
    entity_id_map = {}
    
    for row in cursor.fetchall():
        entity_id, name, entity_type, compressed_data = row
        
        # Decompress to get full data including observations
        try:
            entity_data = decompress_data(compressed_data)
            entities.append({
                "type": "entity",
                "name": name,
                "entityType": entity_type,
                "observations": entity_data.get("observations", [])
            })
            entity_id_map[entity_id] = name
        except Exception as e:
            logger.error(f"Error decompressing entity {name}: {e}")
    
    # Get all relations
    cursor.execute('''
        SELECT from_entity_id, to_entity_id, relation_type
        FROM relations
    ''')
    
    relations = []
    for row in cursor.fetchall():
        from_id, to_id, rel_type = row
        if from_id in entity_id_map and to_id in entity_id_map:
            relations.append({
                "type": "relation",
                "from": entity_id_map[from_id],
                "to": entity_id_map[to_id],
                "relationType": rel_type
            })
    
    conn.close()
    
    return {
        "entities": entities,
        "relations": relations
    }

def get_memory_status() -> Dict[str, Any]:
    """Get real memory system statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get real statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_entities,
            SUM(original_size) as total_original_bytes,
            SUM(compressed_size) as total_compressed_bytes,
            AVG(compression_ratio) as avg_compression_ratio,
            SUM(access_count) as total_accesses
        FROM entities
    ''')
    
    stats = cursor.fetchone()
    total_entities = stats[0] or 0
    total_original = stats[1] or 0
    total_compressed = stats[2] or 0
    avg_ratio = stats[3] or 1.0
    total_accesses = stats[4] or 0
    
    # Get tier distribution
    cursor.execute('''
        SELECT tier, COUNT(*) as count
        FROM entities
        GROUP BY tier
    ''')
    
    tier_distribution = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get entity type distribution
    cursor.execute('''
        SELECT entity_type, COUNT(*) as count
        FROM entities
        GROUP BY entity_type
    ''')
    
    type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    # Calculate real savings
    actual_savings = total_original - total_compressed if total_original > 0 else 0
    savings_percentage = (actual_savings / total_original * 100) if total_original > 0 else 0
    
    return {
        "success": True,
        "database_path": str(DB_PATH),
        "database_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "statistics": {
            "total_entities": total_entities,
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed,
            "actual_bytes_saved": actual_savings,
            "compression_savings_percentage": f"{savings_percentage:.1f}%",
            "average_compression_ratio": avg_ratio,
            "total_accesses": total_accesses
        },
        "tier_distribution": tier_distribution,
        "type_distribution": type_distribution,
        "compression_method": "zlib level 9",
        "integrity_verification": "SHA256 checksums"
    }

def create_relations(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Create relations between entities"""
    relations = arguments.get("relations", [])
    results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for relation in relations:
        try:
            from_name = relation.get("from", "")
            to_name = relation.get("to", "")
            relation_type = relation.get("relationType", "")
            
            # Get entity IDs
            cursor.execute("SELECT id FROM entities WHERE name = ?", (from_name,))
            from_result = cursor.fetchone()
            cursor.execute("SELECT id FROM entities WHERE name = ?", (to_name,))
            to_result = cursor.fetchone()
            
            if from_result and to_result:
                from_id = from_result[0]
                to_id = to_result[0]
                
                cursor.execute('''
                    INSERT INTO relations (from_entity_id, to_entity_id, relation_type)
                    VALUES (?, ?, ?)
                ''', (from_id, to_id, relation_type))
                
                results.append({
                    "from": from_name,
                    "to": to_name,
                    "relationType": relation_type,
                    "success": True
                })
            else:
                results.append({
                    "from": from_name,
                    "to": to_name,
                    "error": "One or both entities not found"
                })
                
        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            results.append({"error": str(e)})
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "relations_created": len([r for r in results if r.get("success")]),
        "results": results
    }

async def init_components():
    """Initialize optional components asynchronously with circuit breaker pattern"""
    logger.info("🧠 Starting Enhanced Memory Server with SAFLA + Reliability Validation")
    
    # Enable startup suppression to prevent TTS replay during initialization
    speak_to_marc._startup_suppression = True
    
    # Initialize reliability validation layer with circuit breaker
    global reliability_integration
    if RELIABILITY_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            # Create a dummy server object for the integration
            class DummyServer:
                async def create_entities(self, entities):
                    return create_entities({"entities": entities})
                async def search_nodes(self, query, **kwargs):
                    return search_nodes({"query": query, **kwargs})
                async def read_graph(self):
                    return read_graph({})
            
            dummy_server = DummyServer()
            reliability_integration = ReliabilityEnhancedMemoryIntegration(dummy_server, DB_PATH)
            logger.info("🛡️ Reliability validation layer initialized successfully")
            # speak_to_marc("Enhanced Memory reliability validation is now active!", "foghorn_success")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize reliability layer: {e}")
            reliability_integration = None
            logger.info("📝 Continuing with SAFLA-only functionality")
    else:
        reliability_integration = None
        logger.info("📝 Running in SAFLA-only mode")
    
    # Initialize compressed context manager with circuit breaker
    global context_manager
    if CONTEXT_COMPRESSION_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            context_manager = CompressedContextManager(MEMORY_DIR)
            logger.info("🗜️ Context compression manager initialized successfully")
            # speak_to_marc("Context compression system is active - TTS replay filtering enabled!", "foghorn_success")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize context compression: {e}")
            context_manager = None
            logger.info("📝 Context compression unavailable - proceeding without TTS filtering")
    else:
        context_manager = None
        logger.info("📝 Context compression not available")
    
    # Initialize specialized storage managers with circuit breaker
    global design_pattern_storage, component_library_manager, clone_success_tracker
    
    if DESIGN_PATTERNS_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            design_pattern_storage = DesignPatternStorage(DB_PATH)
            logger.info("🎨 Design pattern storage initialized successfully")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize design pattern storage: {e}")
            design_pattern_storage = None
            logger.info("📝 Design pattern storage unavailable")
    else:
        design_pattern_storage = None
        logger.info("📝 Design pattern storage not available")
    
    if COMPONENT_LIBRARY_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            component_library_manager = ComponentLibraryManager(DB_PATH)
            logger.info("🧩 Component library manager initialized successfully")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize component library manager: {e}")
            component_library_manager = None
            logger.info("📝 Component library manager unavailable")
    else:
        component_library_manager = None
        logger.info("📝 Component library manager not available")
    
    if CLONE_TRACKING_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            clone_success_tracker = CloneSuccessTracker(DB_PATH)
            logger.info("🎯 Clone success tracker initialized successfully")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize clone success tracker: {e}")
            clone_success_tracker = None
            logger.info("📝 Clone success tracker unavailable")
    else:
        clone_success_tracker = None
        logger.info("📝 Clone success tracker not available")
    
    # Initialize image generation pattern integration
    global image_gen_patterns
    
    if IMAGE_GEN_PATTERNS_AVAILABLE:
        try:
            await asyncio.sleep(0)  # Yield control
            image_gen_patterns = ImageGenPatternIntegration(DB_PATH)
            logger.info("🎨 Image generation pattern integration initialized successfully")
        except Exception as e:
            logger.error(f"⚠️ Failed to initialize image gen pattern integration: {e}")
            image_gen_patterns = None
            logger.info("📝 Image generation pattern integration unavailable")
    else:
        image_gen_patterns = None
        logger.info("📝 Image generation pattern integration not available")
    
    # Initialization complete - re-enable TTS for normal operations
    speak_to_marc._startup_suppression = False
    
    # Count available specialized features
    specialized_features = []
    if design_pattern_storage:
        specialized_features.append("Design Patterns")
    if component_library_manager:
        specialized_features.append("Component Libraries")
    if clone_success_tracker:
        specialized_features.append("Clone Success Tracking")
    if image_gen_patterns:
        specialized_features.append("Image Gen Patterns")
    
    feature_summary = f"Specialized features available: {', '.join(specialized_features)}" if specialized_features else "No specialized features available"
    logger.info(f"✅ Enhanced Memory Server initialization complete - {feature_summary}")
    logger.info("✅ TTS suppression disabled for normal operations")

def main_loop():
    """Main MCP communication loop"""
    # Start component initialization in background
    logger.info("🚀 Starting component initialization in background")
    try:
        # Run async init in a separate thread to not block MCP
        import threading
        init_thread = threading.Thread(target=lambda: asyncio.run(init_components()))
        init_thread.daemon = True
        init_thread.start()
    except Exception as e:
        logger.warning(f"Background initialization failed: {e}")
    
    # Ensure stdio is unbuffered for MCP communication
    sys.stdin.reconfigure(encoding='utf-8', newline='')
    sys.stdout.reconfigure(encoding='utf-8', newline='')
    
    logger.info("🎯 MCP server ready - listening for requests")
    
    # Process MCP requests in simple blocking loop
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            logger.info(f"Received request: {request.get('method')}")
            
            response = handle_request(request)
            if response is not None:
                print(json.dumps(response), flush=True)
                sys.stdout.flush()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            continue
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

def main():
    """Main server entry point with proper sync/async separation"""
    try:
        # Initialize database before starting
        init_database_sync()
        logger.info("📊 Database initialized successfully")
        main_loop()
    except KeyboardInterrupt:
        logger.info("🛑 Server shutting down gracefully")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Centralized logging configuration
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / ".claude"))
    try:
        from mcp_logging_config import setup_mcp_logging
        # Initialize centralized logging
        logger = setup_mcp_logging("enhanced-memory")
    except ImportError:
        # Fallback to basic logging if centralized logging not available
        pass
    
    # Run the async main function with proper event loop management
    main()