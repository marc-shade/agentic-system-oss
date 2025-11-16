#!/usr/bin/env python3
"""
Enhanced Memory MCP - Reliability Validation Layer
Phase 1 Implementation - Day 1-2: Enhanced Memory MCP Reliability Upgrade

This module adds comprehensive reliability validation to the Enhanced Memory MCP
while preserving 100% of existing SAFLA autonomous learning capabilities.

Strategic Approach: Augment & Balance - No Deletions
Timeline: Days 1-2 of Phase 1 Implementation
"""

import json
import logging
import sqlite3
import hashlib
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import networkx as nx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced-memory-reliability")

@dataclass
class MemoryReliabilityScore:
    """Reliability assessment for memory content"""
    consistency_score: float  # 0.0 to 1.0
    reliability_confidence: float  # 0.0 to 1.0
    contradiction_risk: float  # 0.0 to 1.0 (lower is better)
    source_credibility: float  # 0.0 to 1.0
    logical_coherence: float  # 0.0 to 1.0
    timestamp: datetime
    validation_method: str

@dataclass
class ContradictionDetection:
    """Results of contradiction detection analysis"""
    contradictions_found: List[str]
    severity_levels: List[str]  # 'low', 'medium', 'high', 'critical'
    affected_entities: List[str]
    resolution_suggestions: List[str]
    confidence_level: float

class MemoryReliabilityValidator:
    """
    Reliability validation layer for Enhanced Memory MCP
    
    Adds consistency validation, contradiction detection, and reliability scoring
    without disrupting existing SAFLA autonomous learning capabilities.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.reliability_graph = nx.DiGraph()
        self.contradiction_patterns = self._load_contradiction_patterns()
        self.consistency_cache = {}
        
    def _load_contradiction_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns that commonly indicate logical contradictions"""
        return [
            {
                "pattern": r"not\s+.+\s+but\s+.+",
                "type": "direct_contradiction",
                "severity": "high"
            },
            {
                "pattern": r"never\s+.+\s+always",
                "type": "absolute_contradiction", 
                "severity": "critical"
            },
            {
                "pattern": r"impossible\s+.+\s+achieved",
                "type": "logical_impossibility",
                "severity": "high"
            },
            {
                "pattern": r"(\d+)%\s+.+\s+(\d+)%",
                "type": "numerical_inconsistency",
                "severity": "medium"
            }
        ]
    
    async def validate_memory_consistency(self, new_memory: Dict[str, Any], 
                                        existing_memories: List[Dict[str, Any]]) -> MemoryReliabilityScore:
        """
        Validate consistency of new memory against existing knowledge
        
        Args:
            new_memory: New memory to be stored
            existing_memories: Existing memories to validate against
            
        Returns:
            MemoryReliabilityScore with comprehensive reliability assessment
        """
        logger.info(f"Validating consistency for memory: {new_memory.get('name', 'unknown')}")
        
        # Extract content for analysis
        memory_content = self._extract_memory_content(new_memory)
        existing_content = [self._extract_memory_content(mem) for mem in existing_memories]
        
        # Perform multiple validation checks
        consistency_score = await self._calculate_consistency_score(memory_content, existing_content)
        contradiction_risk = await self._assess_contradiction_risk(memory_content, existing_content)
        logical_coherence = await self._evaluate_logical_coherence(memory_content)
        source_credibility = await self._assess_source_credibility(new_memory)
        
        # Calculate overall reliability confidence
        reliability_confidence = (
            consistency_score * 0.3 +
            (1.0 - contradiction_risk) * 0.3 +
            logical_coherence * 0.25 +
            source_credibility * 0.15
        )
        
        return MemoryReliabilityScore(
            consistency_score=consistency_score,
            reliability_confidence=reliability_confidence,
            contradiction_risk=contradiction_risk,
            source_credibility=source_credibility,
            logical_coherence=logical_coherence,
            timestamp=datetime.now(),
            validation_method="comprehensive_reliability_analysis"
        )
    
    async def detect_memory_contradictions(self, memory_graph: List[Dict[str, Any]]) -> ContradictionDetection:
        """
        Detect contradictions across entire memory graph
        
        Args:
            memory_graph: Complete memory graph to analyze
            
        Returns:
            ContradictionDetection with detailed contradiction analysis
        """
        logger.info("Performing comprehensive contradiction detection across memory graph")
        
        contradictions = []
        severity_levels = []
        affected_entities = []
        resolution_suggestions = []
        
        # Build relationship graph for analysis
        graph = self._build_memory_relationship_graph(memory_graph)
        
        # Detect direct contradictions
        direct_contradictions = await self._detect_direct_contradictions(memory_graph)
        contradictions.extend(direct_contradictions["contradictions"])
        severity_levels.extend(direct_contradictions["severities"])
        affected_entities.extend(direct_contradictions["entities"])
        
        # Detect implicit contradictions through graph analysis
        implicit_contradictions = await self._detect_implicit_contradictions(graph)
        contradictions.extend(implicit_contradictions["contradictions"])
        severity_levels.extend(implicit_contradictions["severities"])
        affected_entities.extend(implicit_contradictions["entities"])
        
        # Generate resolution suggestions
        resolution_suggestions = await self._generate_resolution_suggestions(
            contradictions, affected_entities
        )
        
        # Calculate confidence level based on analysis depth
        confidence_level = min(0.95, len(memory_graph) * 0.01 + 0.7)
        
        return ContradictionDetection(
            contradictions_found=contradictions,
            severity_levels=severity_levels,
            affected_entities=list(set(affected_entities)),
            resolution_suggestions=resolution_suggestions,
            confidence_level=confidence_level
        )
    
    async def calculate_memory_reliability_score(self, memory_content: str, 
                                               context: Dict[str, Any] = None) -> float:
        """
        Calculate comprehensive reliability score for memory content
        
        Args:
            memory_content: Text content to analyze
            context: Optional context for enhanced analysis
            
        Returns:
            Float reliability score from 0.0 to 1.0
        """
        # Multiple reliability factors
        factors = []
        
        # Content quality analysis
        content_quality = await self._analyze_content_quality(memory_content)
        factors.append(content_quality)
        
        # Logical structure analysis
        logical_structure = await self._analyze_logical_structure(memory_content)
        factors.append(logical_structure)
        
        # Factual consistency analysis
        factual_consistency = await self._analyze_factual_consistency(memory_content)
        factors.append(factual_consistency)
        
        # Temporal consistency analysis
        temporal_consistency = await self._analyze_temporal_consistency(memory_content)
        factors.append(temporal_consistency)
        
        # Calculate weighted average
        weights = [0.3, 0.25, 0.25, 0.2]
        reliability_score = sum(f * w for f, w in zip(factors, weights))
        
        logger.info(f"Calculated reliability score: {reliability_score:.3f}")
        return reliability_score
    
    def add_reliability_metadata(self, memory: Dict[str, Any], 
                               reliability_score: MemoryReliabilityScore) -> Dict[str, Any]:
        """
        Add reliability metadata to memory without disrupting existing structure
        
        Args:
            memory: Original memory object
            reliability_score: Calculated reliability assessment
            
        Returns:
            Enhanced memory with reliability metadata
        """
        # Preserve all existing memory structure
        enhanced_memory = memory.copy()
        
        # Add reliability metadata as new field
        enhanced_memory["reliability_metadata"] = {
            "consistency_score": reliability_score.consistency_score,
            "reliability_confidence": reliability_score.reliability_confidence,
            "contradiction_risk": reliability_score.contradiction_risk,
            "source_credibility": reliability_score.source_credibility,
            "logical_coherence": reliability_score.logical_coherence,
            "validation_timestamp": reliability_score.timestamp.isoformat(),
            "validation_method": reliability_score.validation_method,
            "validated_by": "enhanced_memory_reliability_validator_v1.0"
        }
        
        return enhanced_memory
    
    # Private helper methods
    
    def _extract_memory_content(self, memory: Dict[str, Any]) -> str:
        """Extract text content from memory object for analysis"""
        content_parts = []
        
        if "observations" in memory:
            content_parts.extend(memory["observations"])
        
        if "description" in memory:
            content_parts.append(memory["description"])
            
        if "content" in memory:
            content_parts.append(str(memory["content"]))
            
        return " ".join(content_parts)
    
    async def _calculate_consistency_score(self, new_content: str, 
                                         existing_content: List[str]) -> float:
        """Calculate consistency score against existing memories"""
        if not existing_content:
            return 0.8  # Default score for first memory
            
        # Analyze semantic similarity and logical consistency
        consistency_scores = []
        
        for existing in existing_content:
            # Simple keyword overlap analysis
            new_words = set(new_content.lower().split())
            existing_words = set(existing.lower().split())
            
            if new_words and existing_words:
                overlap = len(new_words.intersection(existing_words))
                total = len(new_words.union(existing_words))
                similarity = overlap / total if total > 0 else 0
                
                # Check for explicit contradictions
                contradiction_score = self._check_explicit_contradictions(new_content, existing)
                
                # Combined consistency score
                consistency = similarity * (1.0 - contradiction_score)
                consistency_scores.append(consistency)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.8
    
    async def _assess_contradiction_risk(self, new_content: str, 
                                       existing_content: List[str]) -> float:
        """Assess risk of contradictions with existing memories"""
        contradiction_indicators = 0
        total_checks = 0
        
        for pattern in self.contradiction_patterns:
            if re.search(pattern["pattern"], new_content, re.IGNORECASE):
                contradiction_indicators += 1
            total_checks += 1
        
        # Check against existing content for contradictions
        for existing in existing_content:
            if self._contains_contradiction(new_content, existing):
                contradiction_indicators += 1
            total_checks += 1
        
        return contradiction_indicators / max(total_checks, 1)
    
    async def _evaluate_logical_coherence(self, content: str) -> float:
        """Evaluate logical coherence of content"""
        coherence_score = 1.0
        
        # Check for logical inconsistencies
        if re.search(r"always\s+.+\s+never", content, re.IGNORECASE):
            coherence_score -= 0.3
            
        if re.search(r"all\s+.+\s+none", content, re.IGNORECASE):
            coherence_score -= 0.3
            
        # Check for temporal inconsistencies
        if re.search(r"before\s+.+\s+after\s+.+\s+before", content, re.IGNORECASE):
            coherence_score -= 0.2
            
        return max(0.0, coherence_score)
    
    async def _assess_source_credibility(self, memory: Dict[str, Any]) -> float:
        """Assess credibility of memory source"""
        # Default credibility based on entity type
        entity_type = memory.get("entityType", "unknown")
        
        credibility_map = {
            "system_role": 0.95,
            "core_system": 0.9,
            "orchestrator": 0.9,
            "project_outcome": 0.85,
            "validated_result": 0.9,
            "user_input": 0.8,
            "external_source": 0.7,
            "generated_content": 0.6,
            "unknown": 0.5
        }
        
        return credibility_map.get(entity_type, 0.5)
    
    def _build_memory_relationship_graph(self, memories: List[Dict[str, Any]]) -> nx.DiGraph:
        """Build NetworkX graph of memory relationships"""
        graph = nx.DiGraph()
        
        for memory in memories:
            memory_id = memory.get("name", str(id(memory)))
            graph.add_node(memory_id, **memory)
            
        # Add relationships based on content similarity and references
        # This is a simplified implementation - could be enhanced with NLP
        for i, mem1 in enumerate(memories):
            for j, mem2 in enumerate(memories[i+1:], i+1):
                content1 = self._extract_memory_content(mem1)
                content2 = self._extract_memory_content(mem2)
                
                # Simple relationship detection
                if self._has_semantic_relationship(content1, content2):
                    graph.add_edge(mem1.get("name"), mem2.get("name"))
                    
        return graph
    
    async def _detect_direct_contradictions(self, memories: List[Dict[str, Any]]) -> Dict[str, List]:
        """Detect direct contradictions in memory content"""
        contradictions = []
        severities = []
        entities = []
        
        for memory in memories:
            content = self._extract_memory_content(memory)
            
            for pattern in self.contradiction_patterns:
                if re.search(pattern["pattern"], content, re.IGNORECASE):
                    contradictions.append(f"Pattern '{pattern['type']}' found in {memory.get('name')}")
                    severities.append(pattern["severity"])
                    entities.append(memory.get("name", "unknown"))
        
        return {
            "contradictions": contradictions,
            "severities": severities,
            "entities": entities
        }
    
    async def _detect_implicit_contradictions(self, graph: nx.DiGraph) -> Dict[str, List]:
        """Detect implicit contradictions through graph analysis"""
        contradictions = []
        severities = []
        entities = []
        
        # Detect cycles that might indicate contradictions
        try:
            cycles = list(nx.simple_cycles(graph))
            for cycle in cycles:
                if len(cycle) > 2:  # Non-trivial cycles
                    contradictions.append(f"Potential logical cycle detected: {' -> '.join(cycle)}")
                    severities.append("medium")
                    entities.extend(cycle)
        except:
            pass  # Graph analysis can fail on complex graphs
            
        return {
            "contradictions": contradictions,
            "severities": severities,
            "entities": entities
        }
    
    async def _generate_resolution_suggestions(self, contradictions: List[str], 
                                             entities: List[str]) -> List[str]:
        """Generate suggestions for resolving contradictions"""
        suggestions = []
        
        if contradictions:
            suggestions.append("Review and validate conflicting information")
            suggestions.append("Consider temporal context - information may be valid at different times")
            suggestions.append("Check source credibility and update reliability scores")
            
        if len(contradictions) > 5:
            suggestions.append("Consider memory consolidation to reduce contradiction complexity")
            
        return suggestions
    
    async def _analyze_content_quality(self, content: str) -> float:
        """Analyze overall quality of content"""
        quality_score = 1.0
        
        # Basic quality indicators
        if len(content) < 10:
            quality_score -= 0.3
            
        if not any(c.isalpha() for c in content):
            quality_score -= 0.4
            
        # Check for structure
        if "." in content or "!" in content or "?" in content:
            quality_score += 0.1
            
        return max(0.0, min(1.0, quality_score))
    
    async def _analyze_logical_structure(self, content: str) -> float:
        """Analyze logical structure of content"""
        structure_score = 0.7  # Base score
        
        # Look for logical connectors
        logical_connectors = ["because", "therefore", "however", "although", "since"]
        for connector in logical_connectors:
            if connector in content.lower():
                structure_score += 0.05
                
        return min(1.0, structure_score)
    
    async def _analyze_factual_consistency(self, content: str) -> float:
        """Analyze factual consistency of content"""
        # Simplified factual analysis
        # In a full implementation, this would use external fact-checking
        
        consistency_score = 0.8  # Default neutral score
        
        # Check for obvious factual inconsistencies
        if re.search(r"impossible|never|always", content, re.IGNORECASE):
            consistency_score -= 0.1
            
        return max(0.0, consistency_score)
    
    async def _analyze_temporal_consistency(self, content: str) -> float:
        """Analyze temporal consistency of content"""
        temporal_score = 0.9  # Default high score
        
        # Look for temporal inconsistencies
        if re.search(r"before\s+\d{4}.+after\s+\d{4}", content):
            # Extract years and check order
            years = re.findall(r"\d{4}", content)
            if len(years) >= 2:
                try:
                    if int(years[0]) > int(years[1]):
                        temporal_score -= 0.3
                except ValueError:
                    pass
                    
        return temporal_score
    
    def _check_explicit_contradictions(self, content1: str, content2: str) -> float:
        """Check for explicit contradictions between two pieces of content"""
        contradiction_score = 0.0
        
        # Simple contradiction detection
        content1_words = set(content1.lower().split())
        content2_words = set(content2.lower().split())
        
        # Check for opposing terms
        opposing_pairs = [
            ("yes", "no"), ("true", "false"), ("always", "never"),
            ("all", "none"), ("increase", "decrease"), ("up", "down")
        ]
        
        for pos, neg in opposing_pairs:
            if pos in content1_words and neg in content2_words:
                contradiction_score += 0.2
            elif neg in content1_words and pos in content2_words:
                contradiction_score += 0.2
                
        return min(1.0, contradiction_score)
    
    def _contains_contradiction(self, content1: str, content2: str) -> bool:
        """Simple check if two contents contain contradictions"""
        return self._check_explicit_contradictions(content1, content2) > 0.3
    
    def _has_semantic_relationship(self, content1: str, content2: str) -> bool:
        """Simple check for semantic relationship between contents"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return False
            
        overlap = len(words1.intersection(words2))
        min_length = min(len(words1), len(words2))
        
        return overlap / min_length > 0.3 if min_length > 0 else False


class ReliabilityEnhancedMemoryIntegration:
    """
    Integration layer that adds reliability validation to Enhanced Memory MCP
    without disrupting existing SAFLA autonomous learning capabilities.
    """
    
    def __init__(self, original_memory_server, db_path: Path):
        self.original_server = original_memory_server
        self.reliability_validator = MemoryReliabilityValidator(db_path)
        self.validation_enabled = True
        
    async def enhanced_create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enhanced entity creation with reliability validation
        
        Preserves all original functionality while adding reliability validation.
        """
        if not self.validation_enabled:
            # Fallback to original functionality if validation disabled
            return await self.original_server.create_entities(entities)
        
        # Get existing memories for consistency validation
        existing_memories = await self.original_server.read_graph()
        
        validated_entities = []
        reliability_reports = []
        
        for entity in entities:
            # Validate reliability
            reliability_score = await self.reliability_validator.validate_memory_consistency(
                entity, existing_memories
            )
            
            # Add reliability metadata
            enhanced_entity = self.reliability_validator.add_reliability_metadata(
                entity, reliability_score
            )
            
            validated_entities.append(enhanced_entity)
            reliability_reports.append({
                "entity_name": entity.get("name", "unknown"),
                "reliability_confidence": reliability_score.reliability_confidence,
                "consistency_score": reliability_score.consistency_score,
                "validation_status": "validated"
            })
        
        # Call original create_entities with enhanced entities
        result = await self.original_server.create_entities(validated_entities)
        
        # Enhance result with reliability information
        result["reliability_validation"] = {
            "validation_performed": True,
            "entities_validated": len(validated_entities),
            "average_reliability": sum(r["reliability_confidence"] for r in reliability_reports) / len(reliability_reports),
            "validation_reports": reliability_reports,
            "validation_timestamp": datetime.now().isoformat()
        }
        
        return result
    
    async def enhanced_search_nodes(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Enhanced search with reliability-aware results
        
        Preserves all original search functionality while adding reliability scoring.
        """
        # Call original search functionality
        search_results = await self.original_server.search_nodes(query, **kwargs)
        
        if not self.validation_enabled:
            return search_results
        
        # Enhance results with reliability information
        enhanced_results = []
        
        for result in search_results.get("results", []):
            # Calculate reliability score for result
            content = self.reliability_validator._extract_memory_content(result)
            reliability_score = await self.reliability_validator.calculate_memory_reliability_score(content)
            
            # Add reliability metadata to result
            enhanced_result = result.copy()
            enhanced_result["reliability_score"] = reliability_score
            enhanced_result["reliability_confidence"] = reliability_score
            
            enhanced_results.append(enhanced_result)
        
        # Sort by reliability if requested
        if kwargs.get("sort_by_reliability", False):
            enhanced_results.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
        
        # Update search results
        search_results["results"] = enhanced_results
        search_results["reliability_enhancement"] = {
            "reliability_scoring_applied": True,
            "results_enhanced": len(enhanced_results),
            "average_reliability": sum(r.get("reliability_score", 0) for r in enhanced_results) / len(enhanced_results) if enhanced_results else 0
        }
        
        return search_results
    
    async def perform_system_wide_consistency_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive consistency check across entire memory system
        
        This is a new capability added by the reliability enhancement.
        """
        logger.info("Performing system-wide consistency check")
        
        # Get all memories
        all_memories = await self.original_server.read_graph()
        
        # Detect contradictions across entire system
        contradiction_detection = await self.reliability_validator.detect_memory_contradictions(all_memories)
        
        # Calculate overall system reliability
        if all_memories:
            reliability_scores = []
            for memory in all_memories:
                content = self.reliability_validator._extract_memory_content(memory)
                score = await self.reliability_validator.calculate_memory_reliability_score(content)
                reliability_scores.append(score)
            
            average_reliability = sum(reliability_scores) / len(reliability_scores)
            min_reliability = min(reliability_scores)
            max_reliability = max(reliability_scores)
        else:
            average_reliability = min_reliability = max_reliability = 0.0
        
        return {
            "system_consistency_check": {
                "total_memories_analyzed": len(all_memories),
                "contradictions_found": len(contradiction_detection.contradictions_found),
                "critical_contradictions": sum(1 for s in contradiction_detection.severity_levels if s == "critical"),
                "average_system_reliability": average_reliability,
                "minimum_reliability": min_reliability,
                "maximum_reliability": max_reliability,
                "consistency_confidence": contradiction_detection.confidence_level,
                "affected_entities": len(contradiction_detection.affected_entities),
                "resolution_suggestions": contradiction_detection.resolution_suggestions,
                "analysis_timestamp": datetime.now().isoformat(),
                "system_status": "reliable" if average_reliability > 0.8 and len(contradiction_detection.contradictions_found) < 5 else "needs_attention"
            }
        }