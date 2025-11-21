#!/usr/bin/env python3
"""
Content Creator MCP Server with OTEL Business Intelligence
OTEL-instrumented version with comprehensive observability and business intelligence tracking
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'mcp-otel-wrapper'))

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
import re
import random
from mcp_otel_wrapper import mcp_otel_trace

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

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="content_generation",
    revenue_attribution="content_creation_billable"
)
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
    """Generate AI-powered content with brand consistency and OTEL tracing.
    
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
        Generated content with SEO metrics and business intelligence
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
    
    # Calculate business value
    content_value = calculate_content_value(type, length, seo_analysis["overall_score"])
    
    result = {
        "content": content.get("text", ""),
        "metadata": content.get("metadata", {}),
        "seo_analysis": seo_analysis,
        "readability": readability,
        "content_id": content_record["id"],
        "suggestions": await generate_improvement_suggestions(content, seo_analysis, readability),
        "otel_metadata": {
            "content_type": "content",
            "business_function": "content_generation",
            "content_format": type,
            "word_count": length,
            "seo_score": seo_analysis["overall_score"],
            "readability_score": readability["score"],
            "content_value": content_value,
            "keywords_count": len(keywords),
            "billable_hours": calculate_billable_hours(type, length),
            "estimated_engagement": calculate_engagement_potential(type, seo_analysis["overall_score"])
        }
    }
    
    return result

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="seo_optimization",
    revenue_attribution="seo_consulting"
)
async def optimize_for_seo(
    content: str,
    target_keywords: List[str],
    content_type: ContentType
) -> Dict[str, Any]:
    """Optimize content for SEO with OTEL tracing.
    
    Args:
        content: Original content
        target_keywords: SEO keywords
        content_type: Type of content
        
    Returns:
        Optimized content with SEO score and business intelligence
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
    
    seo_improvement_value = (final_analysis["overall_score"] - current_analysis["overall_score"]) * 10
    
    return {
        "optimized_content": optimized_content,
        "meta_tags": meta_tags,
        "seo_improvements": {
            "before": current_analysis["overall_score"],
            "after": final_analysis["overall_score"],
            "improvement": final_analysis["overall_score"] - current_analysis["overall_score"]
        },
        "keyword_density": final_analysis["keyword_density"],
        "recommendations": final_analysis["recommendations"],
        "otel_metadata": {
            "content_type": "content",
            "business_function": "seo_optimization",
            "seo_improvement": final_analysis["overall_score"] - current_analysis["overall_score"],
            "keywords_optimized": len(target_keywords),
            "optimization_value": seo_improvement_value,
            "content_format": content_type,
            "billable_hours": 0.5,
            "seo_consulting_value": 150  # Base SEO optimization value
        }
    }

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="quality_assurance",
    revenue_attribution="content_validation"
)
async def check_plagiarism(content: str) -> Dict[str, Any]:
    """Check content for plagiarism with OTEL tracing.
    
    Args:
        content: Content to check
        
    Returns:
        Plagiarism report with similarity scores and business intelligence
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
    
    originality_score = round(100 - similarity_score, 1)
    quality_assurance_value = originality_score * 2  # $2 per percentage point of originality
    
    return {
        "originality_score": originality_score,
        "similarity_percentage": round(similarity_score, 1),
        "status": "pass" if similarity_score < 20 else "review",
        "matched_sources": sources,
        "checked_at": datetime.now().isoformat(),
        "recommendations": [
            "Content appears to be original" if similarity_score < 10 
            else "Consider rephrasing common phrases for better originality"
        ],
        "otel_metadata": {
            "content_type": "content",
            "business_function": "quality_assurance",
            "originality_score": originality_score,
            "similarity_percentage": round(similarity_score, 1),
            "quality_assurance_value": quality_assurance_value,
            "content_length": len(content),
            "validation_status": "pass" if similarity_score < 20 else "review",
            "billable_hours": 0.25
        }
    }

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="content_adaptation",
    revenue_attribution="content_strategy"
)
async def adapt_content(
    original_content: str,
    target_format: ContentType,
    maintain_message: bool = True,
    target_length: Optional[int] = None
) -> Dict[str, Any]:
    """Adapt content for different formats with OTEL tracing.
    
    Args:
        original_content: Source content
        target_format: Desired format
        maintain_message: Preserve core message
        target_length: Target length for new format
        
    Returns:
        Adapted content for new format with business intelligence
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
    
    adaptation_value = calculate_adaptation_value(len(original_content), target_length, target_format)
    
    return {
        "adapted_content": adapted_content,
        "format": target_format,
        "word_count": len(adapted_content.split()),
        "key_points_preserved": len(key_points),
        "adaptation_notes": f"Adapted from {len(original_content.split())} words to {target_format} format",
        "otel_metadata": {
            "content_type": "content",
            "business_function": "content_adaptation",
            "source_format": "text",
            "target_format": target_format,
            "original_length": len(original_content.split()),
            "adapted_length": len(adapted_content.split()),
            "key_points_preserved": len(key_points),
            "adaptation_value": adaptation_value,
            "billable_hours": 0.75,
            "content_strategy_value": 200
        }
    }

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="readability_analysis",
    revenue_attribution="content_optimization"
)
async def analyze_read(content: str) -> Dict[str, Any]:
    """Analyze content readability metrics with OTEL tracing.
    
    Args:
        content: Content to analyze
        
    Returns:
        Readability scores and improvements with business intelligence
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
    
    readability_value = readability_analysis["score"] * 3  # $3 per readability point
    
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
        "target_reading_level": target_levels.get("general", "8th-9th grade"),
        "otel_metadata": {
            "content_type": "content",
            "business_function": "readability_analysis",
            "readability_score": readability_analysis["score"],
            "reading_level": readability_analysis["reading_level"],
            "improvements_suggested": len(improvements),
            "readability_value": readability_value,
            "content_length": len(content.split()),
            "billable_hours": 0.33,
            "analysis_complexity": "high" if len(improvements) > 2 else "medium"
        }
    }

@app.tool()
@mcp_otel_trace(
    mcp_server="content-creator-mcp",
    content_type="content",
    business_function="ab_testing",
    revenue_attribution="content_optimization"
)
async def create_variations(
    base_content: str,
    num_variations: int = 3,
    variation_type: str = "tone"  # tone, length, audience
) -> List[Dict[str, Any]]:
    """Create content variations for A/B testing with OTEL tracing.
    
    Args:
        base_content: Original content
        num_variations: Number of variations to create
        variation_type: Type of variation
        
    Returns:
        List of content variations with business intelligence
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
    
    ab_testing_value = len(variations) * 50  # $50 per variation for A/B testing
    
    # Add OTEL metadata to result
    result = {
        "variations": variations,
        "base_content_length": len(base_content.split()),
        "variation_type": variation_type,
        "total_variations": len(variations),
        "otel_metadata": {
            "content_type": "content",
            "business_function": "ab_testing",
            "variations_created": len(variations),
            "variation_type": variation_type,
            "base_content_length": len(base_content.split()),
            "ab_testing_value": ab_testing_value,
            "billable_hours": len(variations) * 0.25,
            "testing_strategy_value": 300,
            "optimization_potential": "high"
        }
    }
    
    return result

# Helper functions for content generation
async def generate_blog_post(topic: str, keywords: List[str], tone: str, length: int, audience: str) -> Dict[str, str]:
    """Generate a blog post."""
    title = f"Understanding {topic}: A Comprehensive Guide"
    
    content = f"""# {title}

In today's rapidly evolving landscape, {topic} has become increasingly important for {audience}. This comprehensive guide explores the key aspects of {keywords[0] if keywords else topic} and provides valuable insights.

## Key Benefits of {topic}

- Enhanced efficiency and productivity
- Improved user experience
- Cost-effective solutions
- Scalable implementation

## Understanding {keywords[0] if keywords else topic}

{keywords[0] if keywords else topic} represents a fundamental shift in how we approach modern challenges. By leveraging innovative approaches, organizations can achieve significant improvements.

## Best Practices

1. Start with clear objectives
2. Implement gradually
3. Monitor and measure results
4. Continuously optimize

## Conclusion

Understanding {topic} is essential for success in today's competitive environment. By following these guidelines and best practices, you can achieve your objectives effectively.
"""
    
    return {"text": content, "metadata": {"title": title, "word_count": len(content.split())}}

async def generate_social_post(topic: str, keywords: List[str], tone: str, audience: str) -> Dict[str, str]:
    """Generate a social media post."""
    if tone == "casual":
        content = f"Just discovered something amazing about {topic}! 🚀 Who else is exploring {keywords[0] if keywords else topic}? #innovation"
    elif tone == "professional":
        content = f"Exploring the latest developments in {topic}. Key insights on {keywords[0] if keywords else topic} for {audience}."
    else:
        content = f"Exciting developments in {topic}! Learn more about {keywords[0] if keywords else topic}. What's your experience?"
    
    return {"text": content, "metadata": {"platform": "general", "character_count": len(content)}}

async def generate_email(topic: str, keywords: List[str], tone: str, length: int, audience: str, include_cta: bool) -> Dict[str, str]:
    """Generate an email."""
    subject = f"Important Update: {topic}"
    
    content = f"""Subject: {subject}

Dear {audience},

I hope this email finds you well. I wanted to share some important insights about {topic} that could benefit your current projects.

Recent developments in {keywords[0] if keywords else topic} have shown significant potential for improving efficiency and results. Our analysis indicates that organizations implementing these approaches see an average improvement of 30% in key metrics.

Key highlights:
- Enhanced performance capabilities
- Streamlined processes
- Cost-effective implementation
- Proven results across industries

"""
    
    if include_cta:
        content += """
Ready to learn more? Click here to schedule a consultation and discover how these insights can benefit your specific situation.

Best regards,
Your Content Team"""
    
    return {"text": content, "metadata": {"subject": subject, "word_count": len(content.split())}}

async def generate_landing_page(topic: str, keywords: List[str], tone: str, audience: str, include_cta: bool) -> Dict[str, str]:
    """Generate a landing page."""
    title = f"Transform Your {topic} Strategy"
    
    content = f"""# {title}

## Revolutionize Your Approach to {keywords[0] if keywords else topic}

Discover the proven strategies that industry leaders use to achieve exceptional results with {topic}. Our comprehensive solution is designed specifically for {audience} who demand excellence.

### Why Choose Our {topic} Solution?

✓ **Proven Results**: 95% client satisfaction rate
✓ **Expert Team**: Industry-leading specialists
✓ **Comprehensive Support**: End-to-end assistance
✓ **Scalable Solutions**: Grows with your business

### What You'll Get

- Complete {keywords[0] if keywords else topic} analysis
- Custom implementation strategy
- Ongoing support and optimization
- Measurable results within 30 days

"""
    
    if include_cta:
        content += """
### Ready to Get Started?

Don't wait another day to transform your {topic} approach. Our experts are standing by to help you achieve your goals.

**[Get Started Today - Free Consultation]**

*Limited time offer - Schedule your consultation this week and receive a complimentary strategy assessment.*"""
    
    return {"text": content, "metadata": {"title": title, "conversion_focus": "high"}}

async def generate_ad_copy(topic: str, keywords: List[str], tone: str, audience: str) -> Dict[str, str]:
    """Generate ad copy."""
    headline = f"Master {topic} in 30 Days"
    
    content = f"""**{headline}**

Transform your {keywords[0] if keywords else topic} approach with our proven system. Join thousands of satisfied {audience} who've achieved remarkable results.

🎯 Guaranteed results or money back
🚀 Expert-led training program  
💪 Complete support system

Limited time: 50% off for new customers!

*[Click to Learn More]*"""
    
    return {"text": content, "metadata": {"headline": headline, "character_count": len(content)}}

async def generate_video_script(topic: str, keywords: List[str], tone: str, length: int, audience: str) -> Dict[str, str]:
    """Generate a video script."""
    content = f"""VIDEO SCRIPT: Understanding {topic}

[INTRO - 0:00-0:15]
HOST: "Welcome back to our channel! Today we're diving deep into {topic} - something that's absolutely essential for {audience}."

[HOOK - 0:15-0:30]
HOST: "If you've been struggling with {keywords[0] if keywords else topic}, you're not alone. But what if I told you there's a better way?"

[MAIN CONTENT - 0:30-2:00]
HOST: "Let me break down the three key principles of {topic}:

First, understanding the fundamentals of {keywords[0] if keywords else topic}. This is crucial because...

Second, implementing best practices that actually work in real-world scenarios...

Third, measuring and optimizing your results for continuous improvement..."

[CALL TO ACTION - 2:00-2:15]
HOST: "If you found this helpful, make sure to subscribe and hit that notification bell. What's your experience with {topic}? Let me know in the comments!"

[END SCREEN - 2:15-2:30]
HOST: "Thanks for watching, and I'll see you in the next video!"

TOTAL DURATION: ~2:30"""
    
    return {"text": content, "metadata": {"duration": "2:30", "format": "educational"}}

# Business intelligence calculation functions
def calculate_content_value(content_type: str, length: int, seo_score: float) -> float:
    """Calculate business value of generated content."""
    base_rates = {
        "blog": 0.15,      # $0.15 per word
        "social": 2.0,     # $2.0 per post
        "email": 0.20,     # $0.20 per word
        "landing_page": 0.25,  # $0.25 per word
        "ad_copy": 1.0,    # $1.0 per word
        "video_script": 0.30   # $0.30 per word
    }
    
    base_rate = base_rates.get(content_type, 0.10)
    if content_type in ["social"]:
        return base_rate * (seo_score / 100)  # Flat rate for social
    else:
        return length * base_rate * (seo_score / 100)

def calculate_billable_hours(content_type: str, length: int) -> float:
    """Calculate billable hours for content creation."""
    base_hours = {
        "blog": 2.0,
        "social": 0.25,
        "email": 1.0,
        "landing_page": 1.5,
        "ad_copy": 0.5,
        "video_script": 1.5
    }
    
    return base_hours.get(content_type, 1.0)

def calculate_engagement_potential(content_type: str, seo_score: float) -> str:
    """Calculate engagement potential based on content type and SEO score."""
    if seo_score > 80:
        return "high"
    elif seo_score > 60:
        return "medium"
    else:
        return "low"

def calculate_adaptation_value(original_length: int, target_length: int, target_format: str) -> float:
    """Calculate value of content adaptation."""
    base_value = 50  # Base adaptation value
    complexity_multiplier = abs(original_length - target_length) / max(original_length, target_length)
    format_multiplier = {"social": 1.2, "ad_copy": 1.5, "email": 1.3}.get(target_format, 1.0)
    
    return base_value * (1 + complexity_multiplier) * format_multiplier

# Additional helper functions (simplified versions)
async def analyze_brand_voice(sample: str) -> BrandVoiceProfile:
    """Analyze brand voice from sample text."""
    return BrandVoiceProfile(
        tone_attributes=["professional", "friendly"],
        vocabulary_level="moderate",
        sentence_structure="mixed",
        personality_traits=["helpful", "knowledgeable"]
    )

async def apply_brand_voice(content: str, profile: BrandVoiceProfile) -> str:
    """Apply brand voice to content."""
    return content  # Simplified implementation

async def analyze_seo(content: str, keywords: List[str], content_type: str) -> Dict[str, Any]:
    """Analyze SEO metrics."""
    keyword_density = {}
    for keyword in keywords:
        count = content.lower().count(keyword.lower())
        density = (count / len(content.split())) * 100 if content else 0
        keyword_density[keyword] = round(density, 2)
    
    overall_score = min(100, sum(keyword_density.values()) * 10 + random.uniform(60, 90))
    
    return {
        "overall_score": round(overall_score, 1),
        "keyword_density": keyword_density,
        "recommendations": ["Optimize keyword placement", "Improve meta descriptions"]
    }

async def calculate_readability(content: str) -> Dict[str, Any]:
    """Calculate readability metrics."""
    words = content.split()
    sentences = content.split('.')
    
    avg_sentence_length = len(words) / max(len(sentences), 1)
    avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
    
    score = max(0, 100 - (avg_sentence_length * 2) - (avg_word_length * 10))
    
    return {
        "score": round(score, 1),
        "reading_level": "8th grade" if score > 60 else "12th grade",
        "average_sentence_length": round(avg_sentence_length, 1),
        "average_word_length": round(avg_word_length, 1),
        "complex_word_percentage": random.uniform(5, 20),
        "passive_voice_percentage": random.uniform(0, 15)
    }

async def generate_improvement_suggestions(content: Dict, seo: Dict, readability: Dict) -> List[str]:
    """Generate improvement suggestions."""
    suggestions = []
    
    if seo["overall_score"] < 70:
        suggestions.append("Improve keyword optimization")
    
    if readability["score"] < 60:
        suggestions.append("Simplify sentence structure")
    
    return suggestions

async def extract_key_points(content: str) -> List[str]:
    """Extract key points from content."""
    sentences = [s.strip() for s in content.split('.') if s.strip()]
    return sentences[:3]  # Return first 3 sentences as key points

# Content adaptation helper functions (simplified)
async def create_social_version(key_points: List[str], target_length: int) -> str:
    """Create social media version of content."""
    return f"Key insight: {key_points[0][:200] if key_points else 'Content insight'} #socialmedia"

async def create_email_version(key_points: List[str], original: str, target_length: int) -> str:
    """Create email version of content."""
    return f"Email: {key_points[0] if key_points else 'Key information'}"

async def create_ad_copy_version(key_points: List[str], target_length: int) -> str:
    """Create ad copy version of content."""
    return f"Transform your approach! {key_points[0][:100] if key_points else 'Key benefit'}"

async def expand_to_blog_post(key_points: List[str], original: str, target_length: int) -> str:
    """Expand content to blog post."""
    return f"# Blog Post\n\n{'. '.join(key_points)}"

async def create_landing_page_version(key_points: List[str], original: str) -> str:
    """Create landing page version."""
    return f"# Landing Page\n\n{key_points[0] if key_points else 'Main benefit'}"

async def create_video_script_version(key_points: List[str], target_length: int) -> str:
    """Create video script version."""
    return f"VIDEO SCRIPT:\n\nIntro: {key_points[0] if key_points else 'Welcome'}"

async def adjust_content_tone(content: str, tone: str) -> str:
    """Adjust content tone."""
    return f"[{tone.upper()} TONE] {content}"

async def adjust_content_length(content: str, target_length: int) -> str:
    """Adjust content length."""
    words = content.split()
    if target_length > len(words):
        return content + " Additional content to reach target length."
    else:
        return ' '.join(words[:target_length])

async def adjust_for_audience(content: str, audience: str) -> str:
    """Adjust content for specific audience."""
    return f"[FOR {audience.upper()}] {content}"

async def add_keyword_to_headers(content: str, keyword: str) -> str:
    """Add keyword to headers."""
    return content.replace("##", f"## {keyword} -", 1) if "##" in content else content

async def insert_keyword_naturally(content: str, keyword: str) -> str:
    """Insert keyword naturally into content."""
    if keyword.lower() not in content.lower():
        sentences = content.split('.')
        if len(sentences) > 2:
            sentences.insert(2, f" {keyword} is an important consideration")
            return '.'.join(sentences)
    return content

async def generate_meta_tags(content: str, keywords: List[str], content_type: str) -> Dict[str, str]:
    """Generate SEO meta tags."""
    title = content.split('\n')[0].replace('#', '').strip() if content.startswith('#') else "Content Title"
    description = content[:160].replace('\n', ' ').strip()
    
    return {
        "title": title,
        "description": description,
        "keywords": ", ".join(keywords),
        "og:title": title,
        "og:description": description
    }

async def optimize_content_structure(content: str) -> str:
    """Optimize content structure for SEO."""
    return content  # Simplified implementation

# Run the server
if __name__ == "__main__":
    app.run()