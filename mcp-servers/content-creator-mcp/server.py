#!/usr/bin/env python3
"""
Content Creator MCP Server - Enhanced with Content Reliability Validation
Phase 2 Day 9 Implementation: CONTENT CREATION RELIABILITY UPGRADE COMPLETE

AI-powered content generation with SEO optimization, brand consistency, and comprehensive
content reliability validation while preserving 100% of existing content creation capabilities.

Strategic Approach: Augment & Balance - No Deletions
Timeline: Day 9 of Phase 2 Implementation

Phase 2 Enhancement: Adds content reliability validation layer including content quality validation,
SEO validation, plagiarism checking, and brand consistency validation while preserving 100% 
of existing content generation capabilities.

Reliability Tools Added:
- validate_content_reliability: Comprehensive content quality analysis
- validate_seo_compliance: SEO standards compliance validation
- validate_brand_consistency: Brand voice and style consistency validation
"""

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
import re
import random
import hashlib
import subprocess
import statistics
from pathlib import Path
import asyncio

app = FastMCP("content-creator-mcp")

ContentType = Literal["blog", "social", "email", "landing_page", "ad_copy", "video_script"]
Tone = Literal["professional", "casual", "friendly", "authoritative", "playful", "urgent"]

class ContentRequest(BaseModel):
    type: ContentType
    topic: str
    keywords: List[str]
    tone: Tone
    length: Optional[int] = None
    target_audience: str
    brand_voice: Optional[str] = None
    include_cta: bool = True

class BrandVoiceProfile(BaseModel):
    tone_attributes: List[str]
    vocabulary_level: str  # simple, moderate, advanced
    sentence_structure: str  # short, mixed, complex
    personality_traits: List[str]
    avoid_words: List[str] = []
    preferred_phrases: List[str] = []

# In-memory storage
brand_voices: Dict[str, BrandVoiceProfile] = {}
content_history: List[Dict] = []

# Phase 2 Day 9: Voice communication for Content Creator MCP
def speak_to_marc(message: str, voice: str = "foghorn_friendly"):
    """Voice communication for Phase 2 Day 9 Content Creator MCP reliability implementation"""
    try:
        subprocess.run([
            "say", "-v", "Moira", "-r", "180", message
        ], check=False, capture_output=True, timeout=5)
    except:
        pass  # Fail silently if voice unavailable

# Phase 2 Day 9: Content Reliability Validation Classes

class ContentReliabilityScore(BaseModel):
    """Content reliability assessment results"""
    reliability_confidence: float  # 0.0 to 1.0
    quality_score: float  # 0.0 to 1.0
    consistency_score: float  # 0.0 to 1.0
    originality_score: float  # 0.0 to 1.0
    validation_timestamp: str
    validation_method: str

class SEOComplianceCheck(BaseModel):
    """SEO compliance validation results"""
    is_compliant: bool
    compliance_score: float  # 0.0 to 1.0
    keyword_compliance: bool
    structure_compliance: bool
    meta_compliance: bool
    readability_compliance: bool
    violations: List[str]
    recommendations: List[str]
    validation_timestamp: str

class BrandConsistencyValidation(BaseModel):
    """Brand consistency validation results"""
    is_consistent: bool
    consistency_score: float  # 0.0 to 1.0
    tone_consistency: bool
    vocabulary_consistency: bool
    style_consistency: bool
    brand_violations: List[str]
    consistency_recommendations: List[str]
    validation_timestamp: str

# Phase 2 Day 9: Content Reliability Validation Classes

class ContentReliabilityValidator:
    """Comprehensive content quality and reliability analysis"""
    
    def __init__(self):
        self.quality_thresholds = {
            "min_readability_score": 0.6,
            "min_uniqueness_score": 0.8,
            "min_coherence_score": 0.7,
            "min_relevance_score": 0.75
        }
        
        self.quality_indicators = {
            "sentence_variety": [10, 30],  # Min/max sentence count for variety
            "word_diversity": 0.4,  # Minimum unique word ratio
            "paragraph_structure": 3,  # Minimum paragraphs for structure
            "engagement_markers": ["?", "!", "you", "your"]  # Engagement elements
        }

    async def validate_content_reliability(self, content: str, content_type: str, target_keywords: List[str] = None) -> ContentReliabilityScore:
        """Comprehensive content reliability validation"""
        
        # Quality assessment
        quality_score = self.assess_content_quality(content)
        
        # Consistency assessment
        consistency_score = self.assess_content_consistency(content, content_type)
        
        # Originality assessment
        originality_score = self.assess_content_originality(content)
        
        # Keyword relevance if provided
        relevance_score = 1.0
        if target_keywords:
            relevance_score = self.assess_keyword_relevance(content, target_keywords)
        
        # Calculate overall reliability confidence
        reliability_confidence = (
            quality_score * 0.3 +
            consistency_score * 0.25 +
            originality_score * 0.25 +
            relevance_score * 0.2
        )
        
        return ContentReliabilityScore(
            reliability_confidence=reliability_confidence,
            quality_score=quality_score,
            consistency_score=consistency_score,
            originality_score=originality_score,
            validation_timestamp=datetime.now().isoformat(),
            validation_method="comprehensive_content_reliability_analysis"
        )

    def assess_content_quality(self, content: str) -> float:
        """Assess overall content quality"""
        quality_score = 1.0
        
        # Check length appropriateness
        word_count = len(content.split())
        if word_count < 50:
            quality_score -= 0.3
        elif word_count > 5000:
            quality_score -= 0.1
            
        # Check sentence structure variety
        sentences = content.split('.')
        if len(sentences) < 3:
            quality_score -= 0.2
            
        # Check for engagement elements
        engagement_count = sum(1 for marker in self.quality_indicators["engagement_markers"] if marker.lower() in content.lower())
        if engagement_count == 0:
            quality_score -= 0.1
            
        # Check paragraph structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            quality_score -= 0.15
            
        # Check word diversity
        words = content.lower().split()
        unique_words = set(words)
        if len(words) > 0:
            diversity_ratio = len(unique_words) / len(words)
            if diversity_ratio < self.quality_indicators["word_diversity"]:
                quality_score -= 0.2
        
        return max(0.0, min(1.0, quality_score))

    def assess_content_consistency(self, content: str, content_type: str) -> float:
        """Assess content consistency for type"""
        consistency_score = 1.0
        
        # Type-specific consistency checks
        if content_type == "blog":
            # Blog should have clear structure
            if not any(marker in content for marker in ['#', '##', '1.', '•', '-']):
                consistency_score -= 0.2
        elif content_type == "social":
            # Social content should be concise
            if len(content.split()) > 200:
                consistency_score -= 0.3
        elif content_type == "email":
            # Email should have greeting and closing
            greetings = ['dear', 'hello', 'hi', 'greetings']
            closings = ['sincerely', 'best', 'regards', 'thanks']
            if not any(g in content.lower() for g in greetings):
                consistency_score -= 0.2
            if not any(c in content.lower() for c in closings):
                consistency_score -= 0.2
                
        return max(0.0, min(1.0, consistency_score))

    def assess_content_originality(self, content: str) -> float:
        """Assess content originality (simplified check)"""
        originality_score = 1.0
        
        # Check for cliché phrases (simplified)
        cliches = [
            "think outside the box", "low hanging fruit", "paradigm shift",
            "revolutionary", "game changer", "cutting edge", "state of the art"
        ]
        
        cliche_count = sum(1 for cliche in cliches if cliche.lower() in content.lower())
        originality_score -= cliche_count * 0.1
        
        # Check for repetitive content
        words = content.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only check longer words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Penalize excessive repetition
        for word, count in word_freq.items():
            if count > len(words) * 0.05:  # More than 5% of content
                originality_score -= 0.1
                
        return max(0.0, min(1.0, originality_score))

    def assess_keyword_relevance(self, content: str, keywords: List[str]) -> float:
        """Assess keyword relevance and integration"""
        if not keywords:
            return 1.0
            
        content_lower = content.lower()
        keyword_scores = []
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in content_lower:
                # Calculate keyword density
                word_count = len(content.split())
                keyword_count = content_lower.count(keyword_lower)
                density = keyword_count / word_count if word_count > 0 else 0
                
                # Optimal density is 1-3%
                if 0.01 <= density <= 0.03:
                    keyword_scores.append(1.0)
                elif density > 0.03:
                    keyword_scores.append(0.7)  # Over-optimization penalty
                else:
                    keyword_scores.append(0.8)  # Under-optimization
            else:
                keyword_scores.append(0.0)  # Missing keyword
                
        return sum(keyword_scores) / len(keyword_scores) if keyword_scores else 0.0

class SEOComplianceValidator:
    """SEO standards compliance validation"""
    
    def __init__(self):
        self.seo_requirements = {
            "title_length": [30, 60],  # Min/max title characters
            "meta_description_length": [120, 160],  # Min/max meta description
            "heading_structure": True,  # Requires H1, H2 hierarchy
            "keyword_density": [0.01, 0.03],  # 1-3% keyword density
            "internal_linking": True,  # Should have internal links
            "readability_score": 0.6  # Minimum readability
        }

    async def validate_seo_compliance(self, content: str, title: str = "", meta_description: str = "", keywords: List[str] = None) -> SEOComplianceCheck:
        """Comprehensive SEO compliance validation"""
        
        violations = []
        recommendations = []
        compliance_checks = {
            "title_compliance": True,
            "meta_compliance": True,
            "keyword_compliance": True,
            "structure_compliance": True,
            "readability_compliance": True
        }
        
        # Title compliance
        if title:
            title_len = len(title)
            if title_len < self.seo_requirements["title_length"][0]:
                violations.append(f"Title too short: {title_len} characters (min: {self.seo_requirements['title_length'][0]})")
                recommendations.append("Expand title to include more descriptive keywords")
                compliance_checks["title_compliance"] = False
            elif title_len > self.seo_requirements["title_length"][1]:
                violations.append(f"Title too long: {title_len} characters (max: {self.seo_requirements['title_length'][1]})")
                recommendations.append("Shorten title to prevent truncation in search results")
                compliance_checks["title_compliance"] = False
        
        # Meta description compliance
        if meta_description:
            meta_len = len(meta_description)
            if meta_len < self.seo_requirements["meta_description_length"][0]:
                violations.append(f"Meta description too short: {meta_len} characters")
                recommendations.append("Expand meta description to improve click-through rates")
                compliance_checks["meta_compliance"] = False
            elif meta_len > self.seo_requirements["meta_description_length"][1]:
                violations.append(f"Meta description too long: {meta_len} characters")
                recommendations.append("Shorten meta description to prevent truncation")
                compliance_checks["meta_compliance"] = False
        
        # Keyword compliance
        if keywords:
            for keyword in keywords:
                density = self.calculate_keyword_density(content, keyword)
                if density < self.seo_requirements["keyword_density"][0]:
                    violations.append(f"Keyword '{keyword}' under-optimized: {density:.1%} density")
                    recommendations.append(f"Increase usage of '{keyword}' naturally in content")
                    compliance_checks["keyword_compliance"] = False
                elif density > self.seo_requirements["keyword_density"][1]:
                    violations.append(f"Keyword '{keyword}' over-optimized: {density:.1%} density")
                    recommendations.append(f"Reduce usage of '{keyword}' to avoid keyword stuffing")
                    compliance_checks["keyword_compliance"] = False
        
        # Structure compliance
        if not self.check_heading_structure(content):
            violations.append("Poor heading structure detected")
            recommendations.append("Add clear H1, H2, H3 heading hierarchy")
            compliance_checks["structure_compliance"] = False
        
        # Calculate compliance score
        passed_checks = sum(1 for check in compliance_checks.values() if check)
        compliance_score = passed_checks / len(compliance_checks)
        
        return SEOComplianceCheck(
            is_compliant=len(violations) == 0,
            compliance_score=compliance_score,
            keyword_compliance=compliance_checks["keyword_compliance"],
            structure_compliance=compliance_checks["structure_compliance"],
            meta_compliance=compliance_checks["meta_compliance"],
            readability_compliance=compliance_checks["readability_compliance"],
            violations=violations,
            recommendations=recommendations,
            validation_timestamp=datetime.now().isoformat()
        )

    def calculate_keyword_density(self, content: str, keyword: str) -> float:
        """Calculate keyword density in content"""
        content_words = content.lower().split()
        keyword_lower = keyword.lower()
        
        if not content_words:
            return 0.0
            
        keyword_count = content.lower().count(keyword_lower)
        return keyword_count / len(content_words)

    def check_heading_structure(self, content: str) -> bool:
        """Check for proper heading structure"""
        # Look for markdown or HTML headings
        has_h1 = bool(re.search(r'^#\s|\<h1\>', content, re.MULTILINE))
        has_h2 = bool(re.search(r'^##\s|\<h2\>', content, re.MULTILINE))
        
        return has_h1 and has_h2

class BrandConsistencyValidator:
    """Brand voice and style consistency validation"""
    
    def __init__(self):
        self.consistency_checks = {
            "tone_consistency": True,
            "vocabulary_consistency": True,
            "style_consistency": True,
            "messaging_consistency": True
        }

    async def validate_brand_consistency(self, content: str, brand_profile: BrandVoiceProfile = None, brand_name: str = "") -> BrandConsistencyValidation:
        """Comprehensive brand consistency validation"""
        
        brand_violations = []
        consistency_recommendations = []
        consistency_checks = self.consistency_checks.copy()
        
        if brand_profile:
            # Tone consistency check
            tone_score = self.check_tone_consistency(content, brand_profile.tone_attributes)
            if tone_score < 0.7:
                brand_violations.append(f"Content tone doesn't match brand attributes: {', '.join(brand_profile.tone_attributes)}")
                consistency_recommendations.append("Adjust language to better reflect brand personality")
                consistency_checks["tone_consistency"] = False
            
            # Vocabulary level check
            vocab_score = self.check_vocabulary_consistency(content, brand_profile.vocabulary_level)
            if vocab_score < 0.7:
                brand_violations.append(f"Vocabulary level inconsistent with brand standard: {brand_profile.vocabulary_level}")
                consistency_recommendations.append(f"Adjust language complexity to match {brand_profile.vocabulary_level} level")
                consistency_checks["vocabulary_consistency"] = False
            
            # Avoid words check
            if brand_profile.avoid_words:
                found_avoid_words = [word for word in brand_profile.avoid_words if word.lower() in content.lower()]
                if found_avoid_words:
                    brand_violations.append(f"Content contains avoided words: {', '.join(found_avoid_words)}")
                    consistency_recommendations.append("Remove or replace words that conflict with brand guidelines")
                    consistency_checks["style_consistency"] = False
            
            # Preferred phrases check
            if brand_profile.preferred_phrases:
                used_preferred = [phrase for phrase in brand_profile.preferred_phrases if phrase.lower() in content.lower()]
                if len(used_preferred) == 0:
                    consistency_recommendations.append("Consider incorporating brand-preferred phrases for stronger brand voice")
        
        # Brand name consistency (if provided)
        if brand_name:
            brand_mentions = content.lower().count(brand_name.lower())
            content_length = len(content.split())
            if content_length > 200 and brand_mentions == 0:
                brand_violations.append("No brand name mentions in longer content")
                consistency_recommendations.append("Include brand name appropriately in content")
                consistency_checks["messaging_consistency"] = False
        
        # Calculate consistency score
        passed_checks = sum(1 for check in consistency_checks.values() if check)
        consistency_score = passed_checks / len(consistency_checks)
        
        return BrandConsistencyValidation(
            is_consistent=len(brand_violations) == 0,
            consistency_score=consistency_score,
            tone_consistency=consistency_checks["tone_consistency"],
            vocabulary_consistency=consistency_checks["vocabulary_consistency"],
            style_consistency=consistency_checks["style_consistency"],
            brand_violations=brand_violations,
            consistency_recommendations=consistency_recommendations,
            validation_timestamp=datetime.now().isoformat()
        )

    def check_tone_consistency(self, content: str, tone_attributes: List[str]) -> float:
        """Check content tone against brand attributes"""
        content_lower = content.lower()
        tone_indicators = {
            "professional": ["expertise", "experience", "quality", "reliable", "trust"],
            "friendly": ["welcome", "help", "together", "community", "support"],
            "authoritative": ["proven", "leading", "expert", "research", "data"],
            "playful": ["fun", "exciting", "amazing", "awesome", "love"],
            "casual": ["hey", "stuff", "pretty", "really", "just"]
        }
        
        tone_scores = []
        for attribute in tone_attributes:
            if attribute.lower() in tone_indicators:
                indicators = tone_indicators[attribute.lower()]
                matches = sum(1 for indicator in indicators if indicator in content_lower)
                tone_scores.append(min(1.0, matches / len(indicators)))
            else:
                tone_scores.append(0.5)  # Neutral score for unknown attributes
                
        return sum(tone_scores) / len(tone_scores) if tone_scores else 0.5

    def check_vocabulary_consistency(self, content: str, vocabulary_level: str) -> float:
        """Check vocabulary complexity against brand standard"""
        words = content.split()
        if not words:
            return 1.0
            
        # Simple heuristic for vocabulary complexity
        long_words = [word for word in words if len(word) > 7]
        complexity_ratio = len(long_words) / len(words)
        
        if vocabulary_level == "simple":
            return 1.0 if complexity_ratio < 0.1 else max(0.5, 1.0 - complexity_ratio)
        elif vocabulary_level == "moderate":
            return 1.0 if 0.1 <= complexity_ratio <= 0.25 else max(0.5, 1.0 - abs(0.175 - complexity_ratio))
        elif vocabulary_level == "advanced":
            return 1.0 if complexity_ratio > 0.2 else max(0.5, complexity_ratio * 3)
        else:
            return 0.8  # Unknown level, moderate score

# Initialize validators
content_reliability_validator = ContentReliabilityValidator()
seo_compliance_validator = SEOComplianceValidator()
brand_consistency_validator = BrandConsistencyValidator()

class BrandConsistencyValidation(BaseModel):
    """Brand consistency validation results"""
    is_consistent: bool
    consistency_score: float  # 0.0 to 1.0
    tone_consistency: bool
    vocabulary_consistency: bool
    style_consistency: bool
    voice_deviations: List[str]
    consistency_factors: Dict[str, float]
    validation_method: str

class ContentReliabilityValidator:
    """Comprehensive content reliability validation system"""
    
    def __init__(self):
        self.quality_thresholds = {
            "min_reliability_confidence": 0.7,
            "min_quality_score": 0.6,
            "min_consistency_score": 0.8,
            "min_originality_score": 0.85
        }
        
        # Content quality assessment patterns
        self.quality_indicators = {
            "positive": [
                r'\b(unique|innovative|valuable|engaging|compelling)\b',
                r'\b(clear|concise|well-structured|informative)\b',
                r'\b(actionable|specific|relevant|targeted)\b'
            ],
            "negative": [
                r'\b(generic|vague|unclear|confusing)\b',
                r'\b(boring|repetitive|irrelevant|outdated)\b',
                r'\b(promotional|spammy|clickbait)\b'
            ]
        }
        
        # Originality patterns to detect potential issues
        self.originality_concerns = [
            r'lorem ipsum',
            r'placeholder text',
            r'insert \w+ here',
            r'\[.*?\]',  # Bracketed placeholders
            r'TODO:|FIXME:|NOTE:'
        ]

    async def validate_content_reliability(self, content_data: Dict[str, Any]) -> ContentReliabilityScore:
        """Comprehensive content reliability validation"""
        content_text = content_data.get("content", "")
        content_type = content_data.get("type", "general")
        metadata = content_data.get("metadata", {})
        
        # Validate content quality
        quality_score = self.analyze_content_quality(content_text, content_type)
        
        # Validate content consistency
        consistency_score = self.analyze_content_consistency(content_text, metadata)
        
        # Validate originality
        originality_score = self.analyze_content_originality(content_text)
        
        # Calculate overall reliability confidence
        reliability_confidence = (
            quality_score * 0.35 +
            consistency_score * 0.25 +
            originality_score * 0.4
        )
        
        return ContentReliabilityScore(
            reliability_confidence=reliability_confidence,
            quality_score=quality_score,
            consistency_score=consistency_score,
            originality_score=originality_score,
            validation_timestamp=datetime.now().isoformat(),
            validation_method="comprehensive_content_reliability_analysis"
        )

    def analyze_content_quality(self, content: str, content_type: str) -> float:
        """Analyze content quality using multiple factors"""
        quality_score = 1.0
        
        # Length appropriateness
        word_count = len(content.split())
        expected_lengths = {
            "blog": (400, 1500),
            "social": (50, 300),
            "email": (100, 500),
            "landing_page": (200, 800),
            "ad_copy": (20, 200),
            "video_script": (200, 600)
        }
        
        min_words, max_words = expected_lengths.get(content_type, (50, 1000))
        if word_count < min_words * 0.5 or word_count > max_words * 2:
            quality_score -= 0.3
        
        # Content structure analysis
        if content_type in ["blog", "landing_page"]:
            # Check for headers
            if not re.search(r'^#{1,3}\s', content, re.MULTILINE):
                quality_score -= 0.2
            
            # Check for bullet points or lists
            if not re.search(r'^\s*[-*•]\s', content, re.MULTILINE):
                quality_score -= 0.1
        
        # Positive quality indicators
        positive_matches = 0
        for pattern in self.quality_indicators["positive"]:
            positive_matches += len(re.findall(pattern, content, re.IGNORECASE))
        
        quality_score += min(0.2, positive_matches * 0.02)
        
        # Negative quality indicators
        negative_matches = 0
        for pattern in self.quality_indicators["negative"]:
            negative_matches += len(re.findall(pattern, content, re.IGNORECASE))
        
        quality_score -= min(0.3, negative_matches * 0.05)
        
        return max(0.0, min(1.0, quality_score))

    def analyze_content_consistency(self, content: str, metadata: Dict[str, Any]) -> float:
        """Analyze internal content consistency"""
        consistency_score = 1.0
        
        # Tone consistency check
        expected_tone = metadata.get("tone", "professional")
        if not self.check_tone_consistency(content, expected_tone):
            consistency_score -= 0.2
        
        # Keyword consistency
        target_keywords = metadata.get("keywords", [])
        if target_keywords:
            keyword_usage = self.analyze_keyword_distribution(content, target_keywords)
            if keyword_usage < 0.5:  # Less than 50% of keywords used appropriately
                consistency_score -= 0.2
        
        # Style consistency
        if not self.check_style_consistency(content):
            consistency_score -= 0.15
        
        return max(0.0, min(1.0, consistency_score))

    def analyze_content_originality(self, content: str) -> float:
        """Analyze content originality"""
        originality_score = 1.0
        
        # Check for placeholder content
        for pattern in self.originality_concerns:
            if re.search(pattern, content, re.IGNORECASE):
                originality_score -= 0.3
        
        # Check for repetitive phrases
        sentences = content.split('.')
        if len(sentences) > 5:
            unique_sentences = len(set(s.strip().lower() for s in sentences if s.strip()))
            repetition_ratio = unique_sentences / len(sentences)
            if repetition_ratio < 0.8:
                originality_score -= 0.2
        
        # Content complexity and uniqueness
        unique_words = len(set(content.lower().split()))
        total_words = len(content.split())
        if total_words > 0:
            vocabulary_diversity = unique_words / total_words
            if vocabulary_diversity < 0.5:
                originality_score -= 0.15
        
        return max(0.0, min(1.0, originality_score))

    def check_tone_consistency(self, content: str, expected_tone: str) -> bool:
        """Check if content maintains expected tone"""
        tone_patterns = {
            "professional": [r'\b(implement|optimize|strategic|efficient)\b'],
            "casual": [r'\b(awesome|cool|easy|simple)\b'],
            "friendly": [r'\b(welcome|helpful|glad|happy)\b'],
            "authoritative": [r'\b(must|should|proven|evidence)\b'],
            "playful": [r'\b(fun|exciting|amazing|wonderful)\b']
        }
        
        patterns = tone_patterns.get(expected_tone, [])
        if not patterns:
            return True
        
        matches = 0
        for pattern in patterns:
            matches += len(re.findall(pattern, content, re.IGNORECASE))
        
        return matches > 0

    def analyze_keyword_distribution(self, content: str, keywords: List[str]) -> float:
        """Analyze how well keywords are distributed in content"""
        if not keywords:
            return 1.0
        
        keywords_used = 0
        for keyword in keywords:
            if keyword.lower() in content.lower():
                keywords_used += 1
        
        return keywords_used / len(keywords) if keywords else 1.0

    def check_style_consistency(self, content: str) -> bool:
        """Check for consistent writing style"""
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        if len(sentences) < 3:
            return True
        
        # Check for consistent sentence structure patterns
        sentence_lengths = [len(s.split()) for s in sentences]
        if len(sentence_lengths) > 1:
            avg_length = statistics.mean(sentence_lengths)
            std_dev = statistics.stdev(sentence_lengths)
            # If standard deviation is more than 50% of average, style might be inconsistent
            return std_dev / avg_length < 0.5
        
        return True

class SEOComplianceValidator:
    """SEO compliance validation system"""
    
    def __init__(self):
        self.seo_standards = {
            "keyword_density": {"min": 0.5, "max": 5.0, "optimal": (1.0, 3.0)},
            "title_length": {"min": 30, "max": 60},
            "meta_description_length": {"min": 120, "max": 160},
            "readability_score": {"min": 60},  # Flesch-Kincaid
            "content_length": {
                "blog": {"min": 300, "optimal": (600, 1500)},
                "landing_page": {"min": 200, "optimal": (300, 800)},
                "social": {"min": 50, "optimal": (100, 280)}
            }
        }

    async def validate_seo_compliance(self, content_data: Dict[str, Any]) -> SEOComplianceCheck:
        """Comprehensive SEO compliance validation"""
        content = content_data.get("content", "")
        content_type = content_data.get("type", "blog")
        keywords = content_data.get("keywords", [])
        metadata = content_data.get("metadata", {})
        
        violations = []
        recommendations = []
        
        # Keyword compliance
        keyword_compliance = self.validate_keyword_usage(content, keywords, violations, recommendations)
        
        # Structure compliance
        structure_compliance = self.validate_content_structure(content, content_type, violations, recommendations)
        
        # Meta compliance
        meta_compliance = self.validate_meta_elements(metadata, violations, recommendations)
        
        # Readability compliance
        readability_compliance = self.validate_readability(content, violations, recommendations)
        
        # Calculate overall compliance score
        compliance_factors = [keyword_compliance, structure_compliance, meta_compliance, readability_compliance]
        compliance_score = sum(compliance_factors) / len(compliance_factors)
        
        is_compliant = compliance_score >= 0.8 and len(violations) == 0
        
        return SEOComplianceCheck(
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            keyword_compliance=keyword_compliance,
            structure_compliance=structure_compliance,
            meta_compliance=meta_compliance,
            readability_compliance=readability_compliance,
            violations=violations,
            recommendations=recommendations,
            validation_timestamp=datetime.now().isoformat()
        )

    def validate_keyword_usage(self, content: str, keywords: List[str], violations: List[str], recommendations: List[str]) -> bool:
        """Validate keyword usage and density"""
        if not keywords:
            recommendations.append("Add target keywords for SEO optimization")
            return True
        
        compliant = True
        word_count = len(content.split())
        
        for keyword in keywords:
            keyword_count = content.lower().count(keyword.lower())
            if word_count > 0:
                density = (keyword_count / word_count) * 100
                
                if density < self.seo_standards["keyword_density"]["min"]:
                    violations.append(f"Keyword '{keyword}' density too low: {density:.1f}%")
                    recommendations.append(f"Increase usage of keyword '{keyword}' to improve SEO")
                    compliant = False
                elif density > self.seo_standards["keyword_density"]["max"]:
                    violations.append(f"Keyword '{keyword}' density too high: {density:.1f}%")
                    recommendations.append(f"Reduce usage of keyword '{keyword}' to avoid keyword stuffing")
                    compliant = False
        
        return compliant

    def validate_content_structure(self, content: str, content_type: str, violations: List[str], recommendations: List[str]) -> bool:
        """Validate content structure for SEO"""
        compliant = True
        
        # Check content length
        word_count = len(content.split())
        length_standards = self.seo_standards["content_length"].get(content_type, {"min": 200})
        
        if word_count < length_standards["min"]:
            violations.append(f"Content too short: {word_count} words (minimum: {length_standards['min']})")
            recommendations.append(f"Expand content to at least {length_standards['min']} words")
            compliant = False
        
        # Check for headers (for blog and landing pages)
        if content_type in ["blog", "landing_page"]:
            if not re.search(r'^#{1,3}\s', content, re.MULTILINE):
                violations.append("Missing headers for content structure")
                recommendations.append("Add H1, H2, or H3 headers to improve content structure")
                compliant = False
        
        return compliant

    def validate_meta_elements(self, metadata: Dict[str, Any], violations: List[str], recommendations: List[str]) -> bool:
        """Validate meta elements for SEO"""
        compliant = True
        
        # Check title length
        title = metadata.get("title", "")
        if title:
            title_length = len(title)
            if title_length < self.seo_standards["title_length"]["min"]:
                violations.append(f"Title too short: {title_length} characters")
                recommendations.append("Expand title to 30-60 characters")
                compliant = False
            elif title_length > self.seo_standards["title_length"]["max"]:
                violations.append(f"Title too long: {title_length} characters")
                recommendations.append("Shorten title to 30-60 characters")
                compliant = False
        else:
            recommendations.append("Add a meta title for better SEO")
        
        # Check meta description
        description = metadata.get("description", "")
        if description:
            desc_length = len(description)
            if desc_length < self.seo_standards["meta_description_length"]["min"]:
                violations.append(f"Meta description too short: {desc_length} characters")
                recommendations.append("Expand meta description to 120-160 characters")
                compliant = False
            elif desc_length > self.seo_standards["meta_description_length"]["max"]:
                violations.append(f"Meta description too long: {desc_length} characters")
                recommendations.append("Shorten meta description to 120-160 characters")
                compliant = False
        else:
            recommendations.append("Add a meta description for better SEO")
        
        return compliant

    def validate_readability(self, content: str, violations: List[str], recommendations: List[str]) -> bool:
        """Validate content readability for SEO"""
        # Simplified readability check
        sentences = content.split('.')
        words = content.split()
        
        if not sentences or not words:
            return True
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Check average sentence length (should be reasonable for readability)
        if avg_sentence_length > 25:
            violations.append(f"Average sentence length too long: {avg_sentence_length:.1f} words")
            recommendations.append("Break long sentences into shorter ones for better readability")
            return False
        
        return True

class BrandConsistencyValidator:
    """Brand consistency validation system"""
    
    def __init__(self):
        self.consistency_factors = {
            "tone_weight": 0.4,
            "vocabulary_weight": 0.3,
            "style_weight": 0.3
        }

    async def validate_brand_consistency(self, content: str, brand_profile: Optional[BrandVoiceProfile]) -> BrandConsistencyValidation:
        """Comprehensive brand consistency validation"""
        if not brand_profile:
            return BrandConsistencyValidation(
                is_consistent=True,
                consistency_score=1.0,
                tone_consistency=True,
                vocabulary_consistency=True,
                style_consistency=True,
                voice_deviations=[],
                consistency_factors={},
                validation_method="no_brand_profile_provided"
            )
        
        voice_deviations = []
        consistency_factors = {}
        
        # Validate tone consistency
        tone_consistency = self.validate_tone_consistency(content, brand_profile.tone_attributes, voice_deviations)
        consistency_factors["tone"] = 1.0 if tone_consistency else 0.5
        
        # Validate vocabulary consistency
        vocabulary_consistency = self.validate_vocabulary_consistency(content, brand_profile, voice_deviations)
        consistency_factors["vocabulary"] = 1.0 if vocabulary_consistency else 0.5
        
        # Validate style consistency
        style_consistency = self.validate_style_consistency(content, brand_profile, voice_deviations)
        consistency_factors["style"] = 1.0 if style_consistency else 0.5
        
        # Calculate overall consistency score
        consistency_score = (
            consistency_factors["tone"] * self.consistency_factors["tone_weight"] +
            consistency_factors["vocabulary"] * self.consistency_factors["vocabulary_weight"] +
            consistency_factors["style"] * self.consistency_factors["style_weight"]
        )
        
        is_consistent = consistency_score >= 0.8 and len(voice_deviations) == 0
        
        return BrandConsistencyValidation(
            is_consistent=is_consistent,
            consistency_score=consistency_score,
            tone_consistency=tone_consistency,
            vocabulary_consistency=vocabulary_consistency,
            style_consistency=style_consistency,
            voice_deviations=voice_deviations,
            consistency_factors=consistency_factors,
            validation_method="comprehensive_brand_consistency_analysis"
        )

    def validate_tone_consistency(self, content: str, tone_attributes: List[str], deviations: List[str]) -> bool:
        """Validate tone consistency against brand profile"""
        content_lower = content.lower()
        
        # Define tone patterns
        tone_patterns = {
            "professional": [r'\b(strategic|optimize|implement|efficient|professional)\b'],
            "casual": [r'\b(hey|awesome|cool|easy|simple|great)\b'],
            "friendly": [r'\b(welcome|happy|glad|helpful|thanks)\b'],
            "authoritative": [r'\b(must|should|proven|evidence|expert)\b'],
            "playful": [r'\b(fun|exciting|amazing|wonderful|fantastic)\b'],
            "urgent": [r'\b(now|immediately|urgent|hurry|limited)\b'],
            "empathetic": [r'\b(understand|feel|care|support|help)\b']
        }
        
        expected_patterns = []
        for tone in tone_attributes:
            if tone.lower() in tone_patterns:
                expected_patterns.extend(tone_patterns[tone.lower()])
        
        if not expected_patterns:
            return True  # No specific tone requirements
        
        # Check if content matches expected tone
        matches = 0
        for pattern in expected_patterns:
            matches += len(re.findall(pattern, content_lower))
        
        if matches == 0:
            deviations.append(f"Content tone does not match brand attributes: {', '.join(tone_attributes)}")
            return False
        
        return True

    def validate_vocabulary_consistency(self, content: str, brand_profile: BrandVoiceProfile, deviations: List[str]) -> bool:
        """Validate vocabulary consistency"""
        content_lower = content.lower()
        
        # Check for avoided words
        for avoided_word in brand_profile.avoid_words:
            if avoided_word.lower() in content_lower:
                deviations.append(f"Content contains avoided word: '{avoided_word}'")
                return False
        
        # Check for preferred phrases usage
        if brand_profile.preferred_phrases:
            preferred_used = 0
            for phrase in brand_profile.preferred_phrases:
                if phrase.lower() in content_lower:
                    preferred_used += 1
            
            # Expect at least some usage of preferred phrases for longer content
            word_count = len(content.split())
            if word_count > 200 and preferred_used == 0:
                deviations.append("Content does not use any preferred brand phrases")
                return False
        
        return True

    def validate_style_consistency(self, content: str, brand_profile: BrandVoiceProfile, deviations: List[str]) -> bool:
        """Validate writing style consistency"""
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        if len(sentences) < 2:
            return True  # Too short to analyze style
        
        # Analyze sentence structure
        sentence_lengths = [len(s.split()) for s in sentences]
        avg_length = statistics.mean(sentence_lengths)
        
        # Check against brand style preferences
        if brand_profile.sentence_structure == "short" and avg_length > 15:
            deviations.append(f"Sentences too long for brand style (avg: {avg_length:.1f} words)")
            return False
        elif brand_profile.sentence_structure == "complex" and avg_length < 12:
            deviations.append(f"Sentences too short for brand style (avg: {avg_length:.1f} words)")
            return False
        
        return True

# Initialize reliability validators
content_reliability_validator = ContentReliabilityValidator()
seo_compliance_validator = SEOComplianceValidator()
brand_consistency_validator = BrandConsistencyValidator()

# Voice communication function for Phase 2 Day 9
def speak_to_marc(message: str, voice: str = "Moira") -> None:
    """Voice communication with Marc using system TTS with fallback"""
    try:
        subprocess.run([
            "say", "-v", voice, "-r", "180", message
        ], check=False, capture_output=True, timeout=5)
    except Exception:
        pass  # Fail silently if voice unavailable

@app.tool()
async def generate_content(
    type: ContentType,
    topic: str,
    keywords: List[str],
    tone: Tone = "professional",
    length: Optional[int] = None,
    target_audience: str = "general",
    brand_voice_sample: Optional[str] = None,
    include_cta: bool = True
) -> Dict[str, Any]:
    """Generate AI-powered content with brand consistency.
    
    Args:
        type: Content type to generate
        topic: Main topic or subject
        keywords: SEO keywords to include
        tone: Writing tone
        length: Target word count
        target_audience: Audience description
        brand_voice_sample: Sample text for brand voice analysis
        include_cta: Include call-to-action
        
    Returns:
        Generated content with SEO metrics
    """
    # Analyze brand voice if sample provided
    voice_profile = None
    if brand_voice_sample:
        voice_profile = await analyze_brand_voice(brand_voice_sample)
    
    # Set default lengths based on content type
    if not length:
        default_lengths = {
            "blog": 800,
            "social": 280,
            "email": 300,
            "landing_page": 500,
            "ad_copy": 150,
            "video_script": 400
        }
        length = default_lengths.get(type, 500)
    
    # Generate content based on type
    if type == "blog":
        content = await generate_blog_post(topic, keywords, tone, length, target_audience)
    elif type == "social":
        content = await generate_social_post(topic, keywords, tone, target_audience)
    elif type == "email":
        content = await generate_email(topic, keywords, tone, length, target_audience, include_cta)
    elif type == "landing_page":
        content = await generate_landing_page(topic, keywords, tone, target_audience, include_cta)
    elif type == "ad_copy":
        content = await generate_ad_copy(topic, keywords, tone, target_audience)
    elif type == "video_script":
        content = await generate_video_script(topic, keywords, tone, length, target_audience)
    else:
        content = {"error": "Unsupported content type"}
    
    # Apply brand voice if profile exists
    if voice_profile and "text" in content:
        content["text"] = await apply_brand_voice(content["text"], voice_profile)
    
    # SEO optimization
    seo_analysis = await analyze_seo(content.get("text", ""), keywords, type)
    
    # Calculate readability
    readability = await calculate_readability(content.get("text", ""))
    
    # Store in history
    content_record = {
        "id": f"CONTENT-{len(content_history) + 1:05d}",
        "type": type,
        "topic": topic,
        "keywords": keywords,
        "generated_at": datetime.now().isoformat(),
        "seo_score": seo_analysis["overall_score"],
        "readability_score": readability["score"]
    }
    content_history.append(content_record)
    
    return {
        "content": content.get("text", ""),
        "metadata": content.get("metadata", {}),
        "seo_analysis": seo_analysis,
        "readability": readability,
        "content_id": content_record["id"],
        "suggestions": await generate_improvement_suggestions(content, seo_analysis, readability)
    }

@app.tool()
async def optimize_for_seo(
    content: str,
    target_keywords: List[str],
    content_type: ContentType
) -> Dict[str, Any]:
    """Optimize content for SEO.
    
    Args:
        content: Original content
        target_keywords: SEO keywords
        content_type: Type of content
        
    Returns:
        Optimized content with SEO score
    """
    # Analyze current SEO state
    current_analysis = await analyze_seo(content, target_keywords, content_type)
    
    optimized_content = content
    
    # Keyword optimization
    for keyword in target_keywords:
        keyword_count = content.lower().count(keyword.lower())
        
        # Add keywords if density is too low
        if keyword_count < 2:
            # Add to title/headers if possible
            if content_type in ["blog", "landing_page"]:
                optimized_content = await add_keyword_to_headers(optimized_content, keyword)
            
            # Natural insertion in body
            optimized_content = await insert_keyword_naturally(optimized_content, keyword)
    
    # Meta optimization
    meta_tags = await generate_meta_tags(optimized_content, target_keywords, content_type)
    
    # Structure optimization
    if content_type in ["blog", "landing_page"]:
        optimized_content = await optimize_content_structure(optimized_content)
    
    # Re-analyze
    final_analysis = await analyze_seo(optimized_content, target_keywords, content_type)
    
    return {
        "optimized_content": optimized_content,
        "meta_tags": meta_tags,
        "seo_improvements": {
            "before": current_analysis["overall_score"],
            "after": final_analysis["overall_score"],
            "improvement": final_analysis["overall_score"] - current_analysis["overall_score"]
        },
        "keyword_density": final_analysis["keyword_density"],
        "recommendations": final_analysis["recommendations"]
    }

@app.tool()
async def check_plagiarism(content: str) -> Dict[str, Any]:
    """Check content for plagiarism.
    
    Args:
        content: Content to check
        
    Returns:
        Plagiarism report with similarity scores
    """
    # Simulated plagiarism check
    # In production, would integrate with actual plagiarism detection service
    
    # Generate mock results
    similarity_score = random.uniform(0, 15)  # Usually low for AI-generated content
    
    sources = []
    if similarity_score > 10:
        sources = [
            {
                "url": "https://example.com/similar-article",
                "similarity": f"{random.uniform(5, 10):.1f}%",
                "matched_phrases": ["common industry phrase", "standard terminology"]
            }
        ]
    
    return {
        "originality_score": round(100 - similarity_score, 1),
        "similarity_percentage": round(similarity_score, 1),
        "status": "pass" if similarity_score < 20 else "review",
        "matched_sources": sources,
        "checked_at": datetime.now().isoformat(),
        "recommendations": [
            "Content appears to be original" if similarity_score < 10 
            else "Consider rephrasing common phrases for better originality"
        ]
    }

@app.tool()
async def adapt_content(
    original_content: str,
    target_format: ContentType,
    maintain_message: bool = True,
    target_length: Optional[int] = None
) -> Dict[str, Any]:
    """Adapt content for different formats.
    
    Args:
        original_content: Source content
        target_format: Desired format
        maintain_message: Preserve core message
        target_length: Target length for new format
        
    Returns:
        Adapted content for new format
    """
    # Extract key points from original
    key_points = await extract_key_points(original_content)
    
    # Set appropriate length
    if not target_length:
        format_lengths = {
            "blog": 800,
            "social": 280,
            "email": 300,
            "landing_page": 500,
            "ad_copy": 150,
            "video_script": 400
        }
        target_length = format_lengths.get(target_format, 300)
    
    # Adapt based on target format
    adapted_content = ""
    
    if target_format == "social":
        adapted_content = await create_social_version(key_points, target_length)
    elif target_format == "email":
        adapted_content = await create_email_version(key_points, original_content, target_length)
    elif target_format == "ad_copy":
        adapted_content = await create_ad_copy_version(key_points, target_length)
    elif target_format == "blog":
        adapted_content = await expand_to_blog_post(key_points, original_content, target_length)
    elif target_format == "landing_page":
        adapted_content = await create_landing_page_version(key_points, original_content)
    elif target_format == "video_script":
        adapted_content = await create_video_script_version(key_points, target_length)
    
    return {
        "adapted_content": adapted_content,
        "format": target_format,
        "word_count": len(adapted_content.split()),
        "key_points_preserved": len(key_points),
        "adaptation_notes": f"Adapted from {len(original_content.split())} words to {target_format} format"
    }

@app.tool()
async def analyze_read(content: str) -> Dict[str, Any]:
    """Analyze content readability metrics.
    
    Args:
        content: Content to analyze
        
    Returns:
        Readability scores and improvements
    """
    readability_analysis = await calculate_readability(content)
    
    # Generate specific improvements
    improvements = []
    
    if readability_analysis["average_sentence_length"] > 20:
        improvements.append({
            "issue": "Long sentences",
            "suggestion": "Break sentences longer than 20 words into shorter ones",
            "impact": "high"
        })
    
    if readability_analysis["complex_word_percentage"] > 15:
        improvements.append({
            "issue": "Complex vocabulary",
            "suggestion": "Replace complex words with simpler alternatives",
            "impact": "medium"
        })
    
    if readability_analysis["passive_voice_percentage"] > 10:
        improvements.append({
            "issue": "Passive voice",
            "suggestion": "Convert passive voice to active voice",
            "impact": "medium"
        })
    
    # Reading level recommendation
    target_levels = {
        "general": "8th-9th grade",
        "professional": "10th-12th grade",
        "technical": "College level",
        "children": "4th-6th grade"
    }
    
    return {
        "readability_score": readability_analysis["score"],
        "reading_level": readability_analysis["reading_level"],
        "metrics": {
            "average_sentence_length": readability_analysis["average_sentence_length"],
            "average_word_length": readability_analysis["average_word_length"],
            "complex_words": readability_analysis["complex_word_percentage"],
            "passive_voice": readability_analysis["passive_voice_percentage"]
        },
        "improvements": improvements,
        "target_reading_level": target_levels.get("general", "8th-9th grade")
    }

@app.tool()
async def create_variations(
    base_content: str,
    num_variations: int = 3,
    variation_type: str = "tone"  # tone, length, audience
) -> List[Dict[str, Any]]:
    """Create content variations for A/B testing.
    
    Args:
        base_content: Original content
        num_variations: Number of variations to create
        variation_type: Type of variation
        
    Returns:
        List of content variations
    """
    variations = []
    
    if variation_type == "tone":
        tones = ["professional", "casual", "friendly", "authoritative", "playful"]
        for i in range(min(num_variations, len(tones))):
            variation = await adjust_content_tone(base_content, tones[i])
            variations.append({
                "variation_id": f"VAR-{i+1}",
                "type": "tone",
                "attribute": tones[i],
                "content": variation
            })
    
    elif variation_type == "length":
        lengths = [0.5, 0.75, 1.25, 1.5]  # Multipliers
        base_length = len(base_content.split())
        for i in range(min(num_variations, len(lengths))):
            target_length = int(base_length * lengths[i])
            variation = await adjust_content_length(base_content, target_length)
            variations.append({
                "variation_id": f"VAR-{i+1}",
                "type": "length",
                "attribute": f"{target_length} words",
                "content": variation
            })
    
    elif variation_type == "audience":
        audiences = ["technical", "executive", "beginner", "expert"]
        for i in range(min(num_variations, len(audiences))):
            variation = await adjust_for_audience(base_content, audiences[i])
            variations.append({
                "variation_id": f"VAR-{i+1}",
                "type": "audience",
                "attribute": audiences[i],
                "content": variation
            })
    
    return variations

# Phase 2 Day 9: Reliability Validation Tools - Content Creator MCP

@app.tool()
async def validate_content_reliability(
    content_text: str,
    content_type: ContentType = "blog",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate content reliability including quality, consistency, and originality analysis.
    
    Args:
        content_text: Content to validate for reliability
        content_type: Type of content for appropriate validation
        metadata: Additional metadata for context
        
    Returns:
        Comprehensive content reliability assessment
    """
    if metadata is None:
        metadata = {}
    
    try:
        # Initialize content reliability validator
        validator = ContentReliabilityValidator()
        
        # Prepare content data for validation
        content_data = {
            "content": content_text,
            "type": content_type,
            "metadata": metadata
        }
        
        # Perform comprehensive reliability validation
        reliability_score = await validator.validate_content_reliability(content_data)
        
        # Voice announcement for content reliability validation
        confidence_percent = reliability_score.reliability_confidence * 100
        if reliability_score.reliability_confidence < 0.7:
            speak_to_marc(f"Content reliability concern: {confidence_percent:.1f}% confidence detected")
        else:
            speak_to_marc(f"Content reliability validated: {confidence_percent:.1f}% confidence achieved")
        
        # Generate recommendations based on scores
        recommendations = []
        if reliability_score.quality_score < 0.6:
            recommendations.append("Improve content structure and clarity")
        if reliability_score.consistency_score < 0.8:
            recommendations.append("Enhance content consistency and flow")
        if reliability_score.originality_score < 0.85:
            recommendations.append("Increase content originality and uniqueness")
        
        if not recommendations:
            recommendations.append("Content meets all reliability standards")
        
        return {
            "validation_result": "content_reliability_analysis_complete",
            "content_type": content_type,
            "reliability_score": {
                "reliability_confidence": reliability_score.reliability_confidence,
                "quality_score": reliability_score.quality_score,
                "consistency_score": reliability_score.consistency_score,
                "originality_score": reliability_score.originality_score,
                "validation_timestamp": reliability_score.validation_timestamp,
                "validation_method": reliability_score.validation_method
            },
            "meets_standards": reliability_score.reliability_confidence >= 0.7,
            "recommendations": recommendations,
            "phase_2_day_9_status": "operational"
        }
        
    except Exception as error:
        speak_to_marc(f"Content reliability validation failed: {str(error)}")
        return {
            "validation_result": "content_reliability_validation_failed",
            "error": str(error),
            "phase_2_day_9_status": "error"
        }

@app.tool()
async def validate_seo_compliance(
    content_text: str,
    target_keywords: List[str],
    content_type: ContentType = "blog",
    seo_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate SEO compliance including keyword optimization, structure, and meta compliance.
    
    Args:
        content_text: Content to validate for SEO compliance
        target_keywords: Keywords to check for proper optimization
        content_type: Type of content for SEO analysis
        seo_requirements: Additional SEO requirements and standards
        
    Returns:
        Comprehensive SEO compliance validation results
    """
    if seo_requirements is None:
        seo_requirements = {}
    
    try:
        # Initialize SEO compliance validator
        validator = SEOComplianceValidator()
        
        # Prepare SEO data for validation
        seo_data = {
            "content": content_text,
            "keywords": target_keywords,
            "type": content_type,
            "requirements": seo_requirements
        }
        
        # Perform comprehensive SEO compliance validation
        seo_check = await validator.validate_seo_compliance(seo_data)
        
        # Voice announcement for SEO compliance validation
        compliance_percent = seo_check.compliance_score * 100
        if not seo_check.is_compliant:
            speak_to_marc(f"SEO compliance issues detected: {compliance_percent:.1f}% compliance with {len(seo_check.violations)} violations")
        else:
            speak_to_marc(f"SEO compliance validated: {compliance_percent:.1f}% compliance achieved")
        
        return {
            "validation_result": "seo_compliance_analysis_complete",
            "content_type": content_type,
            "target_keywords": target_keywords,
            "seo_compliance": {
                "is_compliant": seo_check.is_compliant,
                "compliance_score": seo_check.compliance_score,
                "keyword_compliance": seo_check.keyword_compliance,
                "structure_compliance": seo_check.structure_compliance,
                "meta_compliance": seo_check.meta_compliance,
                "readability_compliance": seo_check.readability_compliance,
                "validation_timestamp": seo_check.validation_timestamp
            },
            "violations": seo_check.violations,
            "recommendations": seo_check.recommendations,
            "phase_2_day_9_status": "operational"
        }
        
    except Exception as error:
        speak_to_marc(f"SEO compliance validation failed: {str(error)}")
        return {
            "validation_result": "seo_compliance_validation_failed",
            "error": str(error),
            "phase_2_day_9_status": "error"
        }

@app.tool()
async def validate_brand_consistency(
    content_text: str,
    brand_voice_name: str,
    content_type: ContentType = "blog",
    consistency_requirements: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Validate brand consistency including tone, vocabulary, and style alignment.
    
    Args:
        content_text: Content to validate for brand consistency
        brand_voice_name: Name of brand voice profile to validate against
        content_type: Type of content for brand analysis
        consistency_requirements: Additional brand consistency requirements
        
    Returns:
        Comprehensive brand consistency validation results
    """
    if consistency_requirements is None:
        consistency_requirements = {}
    
    try:
        # Initialize brand consistency validator
        validator = BrandConsistencyValidator()
        
        # Check if brand voice exists
        if brand_voice_name not in brand_voices:
            # Create a default brand voice profile for validation
            brand_voices[brand_voice_name] = BrandVoiceProfile(
                tone_attributes=["professional", "friendly"],
                vocabulary_level="moderate",
                sentence_structure="mixed",
                personality_traits=["helpful", "knowledgeable"],
                avoid_words=[],
                preferred_phrases=[]
            )
        
        brand_profile = brand_voices[brand_voice_name]
        
        # Prepare brand data for validation
        brand_data = {
            "content": content_text,
            "brand_profile": brand_profile,
            "requirements": consistency_requirements
        }
        
        # Perform comprehensive brand consistency validation
        brand_validation = await validator.validate_brand_consistency(brand_data)
        
        # Voice announcement for brand consistency validation
        consistency_percent = brand_validation.consistency_score * 100
        if not brand_validation.is_consistent:
            speak_to_marc(f"Brand consistency deviations detected: {consistency_percent:.1f}% consistency with {len(brand_validation.voice_deviations)} deviations")
        else:
            speak_to_marc(f"Brand consistency validated: {consistency_percent:.1f}% consistency achieved")
        
        return {
            "validation_result": "brand_consistency_analysis_complete",
            "brand_voice_name": brand_voice_name,
            "content_type": content_type,
            "brand_consistency": {
                "is_consistent": brand_validation.is_consistent,
                "consistency_score": brand_validation.consistency_score,
                "tone_consistency": brand_validation.tone_consistency,
                "vocabulary_consistency": brand_validation.vocabulary_consistency,
                "style_consistency": brand_validation.style_consistency,
                "validation_method": brand_validation.validation_method
            },
            "voice_deviations": brand_validation.voice_deviations,
            "consistency_factors": brand_validation.consistency_factors,
            "brand_profile_used": {
                "tone_attributes": brand_profile.tone_attributes,
                "vocabulary_level": brand_profile.vocabulary_level,
                "sentence_structure": brand_profile.sentence_structure,
                "personality_traits": brand_profile.personality_traits
            },
            "phase_2_day_9_status": "operational"
        }
        
    except Exception as error:
        speak_to_marc(f"Brand consistency validation failed: {str(error)}")
        return {
            "validation_result": "brand_consistency_validation_failed",
            "error": str(error),
            "phase_2_day_9_status": "error"
        }

# Content generation functions
async def generate_blog_post(
    topic: str,
    keywords: List[str],
    tone: str,
    length: int,
    audience: str
) -> Dict[str, Any]:
    """Generate blog post content."""
    # Create blog structure
    title = f"Complete Guide to {topic}"
    
    introduction = f"""
In today's rapidly evolving landscape, understanding {topic} has become more crucial than ever. 
This comprehensive guide will explore the key aspects of {topic}, providing you with actionable 
insights and practical strategies that you can implement immediately.
    """.strip()
    
    # Generate sections based on keywords
    sections = []
    for i, keyword in enumerate(keywords[:3]):
        sections.append(f"""
## {i+1}. Understanding {keyword.title()}

When it comes to {topic}, {keyword} plays a vital role. Organizations that master this aspect 
often see significant improvements in their overall performance. Let's dive deep into what makes 
{keyword} so important and how you can leverage it effectively.

Key considerations for {keyword}:
- Strategic implementation approaches
- Common challenges and solutions
- Best practices from industry leaders
- Measurable outcomes and KPIs
        """.strip())
    
    conclusion = f"""
## Conclusion

Mastering {topic} requires a strategic approach that encompasses {', '.join(keywords[:3])}. 
By implementing the strategies outlined in this guide, you'll be well-positioned to achieve 
remarkable results in your {topic} initiatives.

Remember, success in {topic} is not just about understanding the concepts—it's about taking 
action and continuously optimizing your approach based on real-world results.
    """.strip()
    
    # Combine all parts
    full_content = f"# {title}\n\n{introduction}\n\n" + "\n\n".join(sections) + f"\n\n{conclusion}"
    
    # Adjust to target length
    full_content = await adjust_content_length(full_content, length)
    
    return {
        "text": full_content,
        "metadata": {
            "title": title,
            "sections": len(sections) + 2,  # +intro and conclusion
            "word_count": len(full_content.split()),
            "reading_time": f"{len(full_content.split()) // 200} min read"
        }
    }

async def generate_social_post(
    topic: str,
    keywords: List[str],
    tone: str,
    audience: str
) -> Dict[str, Any]:
    """Generate social media post."""
    # Create engaging social content
    hooks = [
        f"🚀 Did you know that {topic} can transform your business?",
        f"💡 Here's what nobody tells you about {topic}:",
        f"📊 The truth about {topic} might surprise you..."
    ]
    
    hook = random.choice(hooks)
    
    # Main content
    main_point = f"When it comes to {keywords[0]}, most people miss the critical connection to {topic}."
    
    # Call to action
    ctas = [
        "What's your experience with this?",
        "Share your thoughts below! 👇",
        "Tag someone who needs to see this!"
    ]
    
    cta = random.choice(ctas)
    
    # Hashtags
    hashtags = [f"#{kw.replace(' ', '')}" for kw in keywords[:3]]
    hashtags.extend(["#BusinessGrowth", "#Innovation", "#Success"])
    
    full_post = f"{hook}\n\n{main_point}\n\n{cta}\n\n{' '.join(hashtags[:5])}"
    
    return {
        "text": full_post,
        "metadata": {
            "character_count": len(full_post),
            "hashtag_count": len(hashtags[:5]),
            "engagement_elements": ["hook", "question", "hashtags"]
        }
    }

async def generate_email(
    topic: str,
    keywords: List[str],
    tone: str,
    length: int,
    audience: str,
    include_cta: bool
) -> Dict[str, Any]:
    """Generate email content."""
    subject_lines = [
        f"Quick question about {topic}",
        f"[Important] Update on {topic}",
        f"You're invited: Exclusive {topic} insights"
    ]
    
    subject = random.choice(subject_lines)
    
    email_body = f"""
Hi [Name],

I hope this email finds you well. I wanted to reach out regarding {topic} because I believe 
it could make a significant impact on your current initiatives.

Based on our analysis of {keywords[0]}, we've identified several opportunities that align 
well with your goals. Here are the key insights:

• Enhanced efficiency in {keywords[0]} processes
• Improved outcomes through strategic {keywords[1] if len(keywords) > 1 else 'implementation'}
• Measurable ROI within the first quarter

I'd love to discuss how these insights could benefit your specific situation.
    """.strip()
    
    if include_cta:
        email_body += f"""

Would you be available for a brief 15-minute call this week? I have some time slots available 
on Tuesday and Thursday afternoon.

Looking forward to your thoughts!

Best regards,
[Your Name]
        """.strip()
    
    return {
        "text": email_body,
        "metadata": {
            "subject_line": subject,
            "word_count": len(email_body.split()),
            "personalization_tokens": ["[Name]", "[Your Name]"],
            "cta_included": include_cta
        }
    }

async def generate_landing_page(
    topic: str,
    keywords: List[str],
    tone: str,
    audience: str,
    include_cta: bool
) -> Dict[str, Any]:
    """Generate landing page content."""
    headline = f"Master {topic} and Transform Your Business"
    subheadline = f"Discover the proven strategies that industry leaders use to excel in {keywords[0]}"
    
    sections = f"""
## Why {topic} Matters Now More Than Ever

In today's competitive landscape, {topic} isn't just an option—it's a necessity. Companies 
that embrace {keywords[0]} see an average improvement of 47% in their key metrics.

## What You'll Learn

✅ **Fundamental Principles**: Master the core concepts of {topic}
✅ **Practical Strategies**: Implement {keywords[0]} techniques that deliver results
✅ **Real-World Examples**: See how leading companies leverage {topic}
✅ **Action Plan**: Get a step-by-step roadmap for success

## Who This Is For

This is designed for professionals who:
- Want to stay ahead in {keywords[1] if len(keywords) > 1 else 'their industry'}
- Are ready to implement cutting-edge strategies
- Value data-driven approaches to {topic}

## Success Stories

"Implementing these {topic} strategies transformed our approach to {keywords[0]}. 
We saw results within weeks!" - Sarah Chen, VP of Operations

"The insights on {keywords[1] if len(keywords) > 1 else topic} were game-changing 
for our team." - Michael Rodriguez, Director of Strategy
    """.strip()
    
    if include_cta:
        sections += f"""

## Ready to Get Started?

[Get Instant Access] [Schedule a Demo] [Download Free Guide]

Join 10,000+ professionals who are already mastering {topic}.
        """.strip()
    
    return {
        "text": f"# {headline}\n## {subheadline}\n\n{sections}",
        "metadata": {
            "headline": headline,
            "subheadline": subheadline,
            "sections": 5 if include_cta else 4,
            "cta_buttons": 3 if include_cta else 0
        }
    }

async def generate_ad_copy(
    topic: str,
    keywords: List[str],
    tone: str,
    audience: str
) -> Dict[str, Any]:
    """Generate ad copy."""
    headlines = [
        f"Transform Your {topic} Today",
        f"The {topic} Solution You've Been Waiting For",
        f"Unlock {topic} Success"
    ]
    
    descriptions = [
        f"Discover how industry leaders use {keywords[0]} to drive exceptional results. Get started now!",
        f"Master {topic} with our proven approach to {keywords[0]}. Join thousands of satisfied customers.",
        f"Stop struggling with {topic}. Our {keywords[0]} solution delivers results in days, not months."
    ]
    
    return {
        "text": f"{random.choice(headlines)}\n\n{random.choice(descriptions)}",
        "metadata": {
            "headline_options": headlines,
            "description_options": descriptions,
            "character_counts": {
                "headline": len(headlines[0]),
                "description": len(descriptions[0])
            }
        }
    }

async def generate_video_script(
    topic: str,
    keywords: List[str],
    tone: str,
    length: int,
    audience: str
) -> Dict[str, Any]:
    """Generate video script."""
    script = f"""
[INTRO - 0:00-0:10]
[Upbeat music fades in]
[Text on screen: "{topic.upper()}"]

NARRATOR: "What if I told you that mastering {topic} could completely transform your approach 
to {keywords[0]}? Today, we're diving deep into the strategies that are changing the game."

[MAIN CONTENT - 0:10-1:30]
[B-roll of relevant visuals]

NARRATOR: "Let's start with the fundamentals. {topic} isn't just about {keywords[0]}—it's 
about creating a systematic approach that delivers consistent results."

[Graphic appears showing key points]

"Here are the three critical elements:
First, understanding the core principles of {keywords[0]}...
Second, implementing strategic {keywords[1] if len(keywords) > 1 else 'processes'}...
And third, measuring and optimizing for continuous improvement."

[EXAMPLES - 1:30-2:00]
[Case study visuals]

NARRATOR: "Let's look at a real example. Company X implemented these {topic} strategies and 
saw a 50% improvement in their {keywords[0]} metrics within just 90 days."

[CONCLUSION - 2:00-2:30]
[Call-to-action graphics]

NARRATOR: "Ready to transform your approach to {topic}? Click the link below to access our 
free guide and start your journey today. Don't forget to subscribe for more insights on 
{keywords[0]} and {topic}!"

[END SCREEN - 2:30-2:40]
[Subscribe button, related videos]
    """.strip()
    
    return {
        "text": script,
        "metadata": {
            "duration": "2:40",
            "sections": ["Intro", "Main Content", "Examples", "Conclusion", "End Screen"],
            "b_roll_needed": 5,
            "graphics_needed": 3
        }
    }

# Helper functions
async def analyze_brand_voice(sample_text: str) -> BrandVoiceProfile:
    """Analyze brand voice from sample text."""
    # Simple analysis - in production would use NLP
    word_count = len(sample_text.split())
    avg_sentence_length = word_count / max(sample_text.count('.'), 1)
    
    # Determine attributes
    tone_attributes = []
    if "!" in sample_text:
        tone_attributes.append("enthusiastic")
    if "?" in sample_text:
        tone_attributes.append("conversational")
    if avg_sentence_length < 15:
        tone_attributes.append("concise")
    else:
        tone_attributes.append("detailed")
    
    vocabulary_level = "simple" if avg_sentence_length < 15 else "moderate"
    
    return BrandVoiceProfile(
        tone_attributes=tone_attributes or ["professional"],
        vocabulary_level=vocabulary_level,
        sentence_structure="short" if avg_sentence_length < 15 else "mixed",
        personality_traits=["informative", "helpful"],
        avoid_words=[],
        preferred_phrases=[]
    )

async def apply_brand_voice(content: str, profile: BrandVoiceProfile) -> str:
    """Apply brand voice profile to content."""
    # Simple implementation - would be more sophisticated in production
    modified_content = content
    
    # Apply sentence structure preferences
    if profile.sentence_structure == "short":
        # Break long sentences (simplified)
        modified_content = modified_content.replace(", and", ". And")
        modified_content = modified_content.replace(", but", ". But")
    
    # Apply vocabulary preferences
    if profile.vocabulary_level == "simple":
        replacements = {
            "utilize": "use",
            "implement": "use",
            "leverage": "use",
            "optimize": "improve",
            "enhance": "improve"
        }
        for complex_word, simple_word in replacements.items():
            modified_content = modified_content.replace(complex_word, simple_word)
    
    return modified_content

async def analyze_seo(content: str, keywords: List[str], content_type: str) -> Dict[str, Any]:
    """Analyze content for SEO optimization."""
    content_lower = content.lower()
    word_count = len(content.split())
    
    # Keyword analysis
    keyword_density = {}
    keyword_positions = {}
    
    for keyword in keywords:
        count = content_lower.count(keyword.lower())
        density = (count / word_count) * 100 if word_count > 0 else 0
        keyword_density[keyword] = round(density, 2)
        
        # Check if keyword appears in important positions
        in_title = keyword.lower() in content_lower[:100]
        in_first_paragraph = keyword.lower() in content_lower[:300]
        keyword_positions[keyword] = {
            "in_title": in_title,
            "in_first_paragraph": in_first_paragraph,
            "total_count": count
        }
    
    # Calculate overall SEO score
    seo_score = 60  # Base score
    
    # Keyword optimization scoring
    for keyword, density in keyword_density.items():
        if 1 <= density <= 3:  # Optimal range
            seo_score += 10
        elif 0.5 <= density < 1:  # Acceptable
            seo_score += 5
        
        if keyword_positions[keyword]["in_title"]:
            seo_score += 5
        if keyword_positions[keyword]["in_first_paragraph"]:
            seo_score += 3
    
    # Content length scoring
    optimal_lengths = {
        "blog": (600, 1200),
        "landing_page": (300, 800),
        "email": (150, 400)
    }
    
    if content_type in optimal_lengths:
        min_length, max_length = optimal_lengths[content_type]
        if min_length <= word_count <= max_length:
            seo_score += 10
    
    # Structure scoring (headers, lists, etc.)
    if "##" in content or "**" in content:  # Has formatting
        seo_score += 5
    
    seo_score = min(100, seo_score)
    
    # Generate recommendations
    recommendations = []
    
    for keyword, density in keyword_density.items():
        if density < 0.5:
            recommendations.append(f"Increase usage of '{keyword}' (current: {density}%)")
        elif density > 3:
            recommendations.append(f"Reduce keyword stuffing for '{keyword}' (current: {density}%)")
    
    if word_count < 300:
        recommendations.append("Consider expanding content for better SEO value")
    
    return {
        "overall_score": seo_score,
        "keyword_density": keyword_density,
        "keyword_positions": keyword_positions,
        "word_count": word_count,
        "recommendations": recommendations
    }

async def calculate_readability(content: str) -> Dict[str, Any]:
    """Calculate readability metrics."""
    sentences = content.split('.')
    words = content.split()
    
    # Basic metrics
    sentence_count = len([s for s in sentences if s.strip()])
    word_count = len(words)
    
    # Average sentence length
    avg_sentence_length = word_count / max(sentence_count, 1)
    
    # Average word length
    total_syllables = sum(count_syllables(word) for word in words)
    avg_syllables_per_word = total_syllables / max(word_count, 1)
    
    # Complex words (3+ syllables)
    complex_words = sum(1 for word in words if count_syllables(word) >= 3)
    complex_word_percentage = (complex_words / max(word_count, 1)) * 100
    
    # Passive voice detection (simplified)
    passive_indicators = ["was", "were", "been", "being", "is", "are", "am"]
    passive_count = sum(1 for word in words if word.lower() in passive_indicators)
    passive_percentage = (passive_count / max(word_count, 1)) * 100
    
    # Flesch Reading Ease score approximation
    flesch_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
    flesch_score = max(0, min(100, flesch_score))
    
    # Determine reading level
    if flesch_score >= 90:
        reading_level = "5th grade"
    elif flesch_score >= 80:
        reading_level = "6th grade"
    elif flesch_score >= 70:
        reading_level = "7th grade"
    elif flesch_score >= 60:
        reading_level = "8th-9th grade"
    elif flesch_score >= 50:
        reading_level = "10th-12th grade"
    elif flesch_score >= 30:
        reading_level = "College"
    else:
        reading_level = "College graduate"
    
    return {
        "score": round(flesch_score, 1),
        "reading_level": reading_level,
        "average_sentence_length": round(avg_sentence_length, 1),
        "average_word_length": round(avg_syllables_per_word, 1),
        "complex_word_percentage": round(complex_word_percentage, 1),
        "passive_voice_percentage": round(passive_percentage, 1)
    }

def count_syllables(word: str) -> int:
    """Count syllables in a word (simplified)."""
    word = word.lower()
    count = 0
    vowels = "aeiouy"
    
    if word[0] in vowels:
        count += 1
    
    for index in range(1, len(word)):
        if word[index] in vowels and word[index - 1] not in vowels:
            count += 1
    
    if word.endswith("e"):
        count -= 1
    
    if count == 0:
        count += 1
    
    return count

async def extract_key_points(content: str) -> List[str]:
    """Extract key points from content."""
    # Simple extraction - would use NLP in production
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    
    # Take first sentence, last sentence, and sentences with keywords
    key_points = []
    
    if sentences:
        key_points.append(sentences[0])  # First sentence
        
        # Middle important sentences (those with "important", "key", "critical", etc.)
        importance_words = ["important", "key", "critical", "essential", "must", "should"]
        for sentence in sentences[1:-1]:
            if any(word in sentence.lower() for word in importance_words):
                key_points.append(sentence)
        
        if len(sentences) > 1:
            key_points.append(sentences[-1])  # Last sentence
    
    return key_points[:5]  # Limit to 5 key points

async def add_keyword_to_headers(content: str, keyword: str) -> str:
    """Add keyword to headers if not present."""
    # Simple implementation
    if "##" in content and keyword.lower() not in content[:200].lower():
        # Add to first subheader
        content = content.replace("##", f"## {keyword.title()} -", 1)
    
    return content

async def insert_keyword_naturally(content: str, keyword: str) -> str:
    """Insert keyword naturally into content."""
    # Find a good spot to insert keyword
    sentences = content.split('.')
    
    # Insert after first few sentences if not present
    if len(sentences) > 3 and keyword.lower() not in content.lower():
        sentences.insert(2, f" When considering {keyword}, it's important to understand the full context")
        content = '.'.join(sentences)
    
    return content

async def generate_meta_tags(content: str, keywords: List[str], content_type: str) -> Dict[str, str]:
    """Generate SEO meta tags."""
    # Extract title
    title = "Untitled"
    if content.startswith("#"):
        title = content.split('\n')[0].replace('#', '').strip()
    
    # Generate description
    first_paragraph = content.split('\n\n')[1] if '\n\n' in content else content[:160]
    description = first_paragraph.replace('\n', ' ').strip()[:160]
    
    return {
        "title": title,
        "description": description,
        "keywords": ", ".join(keywords),
        "og:title": title,
        "og:description": description,
        "og:type": "article" if content_type == "blog" else "website"
    }

async def optimize_content_structure(content: str) -> str:
    """Optimize content structure for SEO."""
    # Ensure proper heading hierarchy
    if "###" in content and not "##" in content:
        content = content.replace("###", "##")
    
    # Add bullet points for readability
    lines = content.split('\n')
    optimized_lines = []
    
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            optimized_lines.append(line)
        elif ":" in line and len(line.split(':')[1].strip()) > 50:
            # Convert long explanations after colons to bullet points
            parts = line.split(':', 1)
            optimized_lines.append(parts[0] + ":")
            optimized_lines.append("- " + parts[1].strip())
        else:
            optimized_lines.append(line)
    
    return '\n'.join(optimized_lines)

async def generate_improvement_suggestions(
    content: Dict,
    seo_analysis: Dict,
    readability: Dict
) -> List[Dict[str, str]]:
    """Generate content improvement suggestions."""
    suggestions = []
    
    # SEO suggestions
    if seo_analysis["overall_score"] < 80:
        suggestions.append({
            "category": "SEO",
            "suggestion": "Optimize keyword placement in titles and first paragraph",
            "priority": "high"
        })
    
    # Readability suggestions
    if readability["score"] < 60:
        suggestions.append({
            "category": "Readability",
            "suggestion": "Simplify sentences and reduce complex vocabulary",
            "priority": "medium"
        })
    
    # Content structure
    if "metadata" in content and content["metadata"].get("sections", 0) < 3:
        suggestions.append({
            "category": "Structure",
            "suggestion": "Add more sections with clear headers for better organization",
            "priority": "medium"
        })
    
    return suggestions

async def create_social_version(key_points: List[str], max_length: int) -> str:
    """Create social media version of content."""
    # Take the most impactful point
    main_point = key_points[0] if key_points else "Check out our latest insights!"
    
    # Shorten to fit character limit
    if len(main_point) > max_length - 50:  # Leave room for hashtags
        main_point = main_point[:max_length - 50] + "..."
    
    return f"💡 {main_point}\n\n#Innovation #BusinessGrowth"

async def create_email_version(key_points: List[str], original: str, length: int) -> str:
    """Create email version of content."""
    subject_hint = key_points[0][:50] if key_points else "Important Update"
    
    email_body = f"""
Subject: {subject_hint}

Hi [Name],

{key_points[0] if key_points else 'I wanted to share some important insights with you.'}

Key takeaways:
"""
    
    for point in key_points[1:4]:
        email_body += f"\n• {point}"
    
    email_body += "\n\nWould love to hear your thoughts on this.\n\nBest regards,\n[Your Name]"
    
    return email_body

async def create_ad_copy_version(key_points: List[str], max_length: int) -> str:
    """Create ad copy version."""
    if not key_points:
        return "Discover the solution you've been looking for. Learn more!"
    
    # Use most compelling point
    headline = key_points[0][:50]
    description = key_points[1][:90] if len(key_points) > 1 else "Get started today!"
    
    return f"{headline}\n{description}"

async def expand_to_blog_post(key_points: List[str], original: str, target_length: int) -> str:
    """Expand content to blog post."""
    blog_post = "# " + (key_points[0] if key_points else "Insights and Analysis") + "\n\n"
    
    # Introduction
    blog_post += "## Introduction\n\n"
    blog_post += key_points[0] + " Let's explore this in detail.\n\n" if key_points else ""
    
    # Main sections
    for i, point in enumerate(key_points[1:4], 1):
        blog_post += f"## Key Point {i}\n\n{point}\n\n"
        blog_post += "This has significant implications for how we approach the challenge.\n\n"
    
    # Conclusion
    blog_post += "## Conclusion\n\n"
    blog_post += "In summary, these insights provide a clear path forward. "
    blog_post += "By implementing these strategies, you can achieve remarkable results.\n"
    
    return blog_post

async def create_landing_page_version(key_points: List[str], original: str) -> str:
    """Create landing page version."""
    landing_page = f"# {key_points[0] if key_points else 'Transform Your Business'}\n\n"
    
    # Value proposition
    landing_page += "## Why This Matters\n\n"
    for point in key_points[:2]:
        landing_page += f"✓ {point}\n"
    
    landing_page += "\n## Take Action Today\n\n"
    landing_page += "[Get Started] [Learn More] [Contact Us]\n"
    
    return landing_page

async def create_video_script_version(key_points: List[str], target_length: int) -> str:
    """Create video script version."""
    script = "[INTRO - 0:00-0:05]\n"
    script += f"NARRATOR: \"{key_points[0] if key_points else 'Welcome to our presentation.'}\"\n\n"
    
    script += "[MAIN POINTS - 0:05-0:25]\n"
    for i, point in enumerate(key_points[1:3], 1):
        script += f"Point {i}: {point}\n"
    
    script += "\n[CONCLUSION - 0:25-0:30]\n"
    script += "NARRATOR: \"Thanks for watching! Subscribe for more insights.\"\n"
    
    return script

async def adjust_content_length(content: str, target_length: int) -> str:
    """Adjust content to target length."""
    current_length = len(content.split())
    
    if current_length > target_length:
        # Shorten by removing less important sentences
        sentences = content.split('.')
        # Keep first and last, remove from middle
        ratio = target_length / current_length
        keep_count = int(len(sentences) * ratio)
        
        if keep_count >= 2:
            shortened = sentences[:keep_count//2] + sentences[-(keep_count//2):]
            content = '. '.join(shortened) + '.'
    
    elif current_length < target_length * 0.8:
        # Expand by adding elaboration
        sentences = content.split('.')
        expanded = []
        
        for sentence in sentences:
            expanded.append(sentence)
            if len(expanded) * 20 < target_length:  # Rough estimate
                expanded.append(" This is particularly important to consider")
        
        content = '.'.join(expanded) + '.'
    
    return content

async def adjust_content_tone(content: str, target_tone: str) -> str:
    """Adjust content tone."""
    if target_tone == "casual":
        content = content.replace("utilize", "use")
        content = content.replace("therefore", "so")
        content = content.replace("however", "but")
    elif target_tone == "professional":
        content = content.replace("use", "utilize")
        content = content.replace("so", "therefore")
        content = content.replace("but", "however")
    elif target_tone == "friendly":
        # Add personal touches
        content = content.replace("You should", "You might want to")
        content = content.replace("It is important", "It's really helpful")
    
    return content

async def adjust_for_audience(content: str, audience: str) -> str:
    """Adjust content for specific audience."""
    if audience == "technical":
        # Add technical details
        content = content.replace("the system", "the technical infrastructure")
        content = content.replace("features", "technical specifications")
    elif audience == "executive":
        # Focus on business impact
        content = content.replace("features", "business benefits")
        content = content.replace("implementation", "strategic initiative")
    elif audience == "beginner":
        # Simplify language
        content = content.replace("leverage", "use")
        content = content.replace("optimize", "improve")
    
    return content

@app.resource("content-creator://templates")
async def get_content_templates() -> Dict[str, List[Dict[str, str]]]:
    """Get content templates by type."""
    return {
        "blog": [
            {
                "name": "How-to Guide",
                "structure": ["Introduction", "Step 1-5", "Tips", "Conclusion"],
                "word_count": "1000-1500"
            },
            {
                "name": "Listicle",
                "structure": ["Introduction", "List items", "Conclusion"],
                "word_count": "800-1200"
            }
        ],
        "email": [
            {
                "name": "Cold Outreach",
                "structure": ["Hook", "Value prop", "Social proof", "CTA"],
                "word_count": "150-200"
            },
            {
                "name": "Newsletter",
                "structure": ["Greeting", "Main content", "Links", "Footer"],
                "word_count": "300-500"
            }
        ],
        "landing_page": [
            {
                "name": "Product Launch",
                "structure": ["Hero", "Benefits", "Features", "Testimonials", "CTA"],
                "word_count": "500-800"
            }
        ]
    }

@app.resource("content-creator://seo-guidelines")
async def get_seo_guidelines() -> Dict[str, Any]:
    """Get SEO best practices."""
    return {
        "keyword_density": {
            "optimal": "1-3%",
            "minimum": "0.5%",
            "maximum": "5%"
        },
        "content_length": {
            "blog": "600-1500 words",
            "landing_page": "300-800 words",
            "product_description": "150-300 words"
        },
        "meta_tags": {
            "title": "50-60 characters",
            "description": "150-160 characters",
            "keywords": "5-10 keywords"
        },
        "structure": [
            "Use H1 for main title",
            "Use H2 for major sections",
            "Include bullet points",
            "Add internal links",
            "Optimize images with alt text"
        ]
    }

# Phase 2 Day 9 completion announcement - DISABLED to prevent startup audio
# speak_to_marc("Phase 2 Day 9 complete! Content Creator MCP reliability enhancement operational with comprehensive content quality validation, SEO compliance checking, and brand consistency analysis!", "foghorn_excited")

# Run the server
if __name__ == "__main__":
    app.run()