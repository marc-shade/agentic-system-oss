#!/usr/bin/env python3
"""
Image Generation Pattern Integration Examples
Shows how the enhanced Image-Gen-MCP integrates with Enhanced-Memory-MCP
"""

# Example 1: Store successful design pattern from Image-Gen-MCP
design_pattern_data = {
    "design_tokens": {
        "colors": {
            "palette": {
                "primary": "#2563eb",
                "secondary": "#7c3aed",
                "accent": "#f59e0b",
                "background": "#ffffff",
                "text": "#1f2937"
            },
            "color_categories": {
                "primary_colors": ["#2563eb", "#7c3aed"],
                "neutral_colors": ["#ffffff", "#f3f4f6", "#e5e7eb"]
            }
        },
        "typography": {
            "font_families": {
                "heading": "Inter, sans-serif",
                "body": "Inter, sans-serif"
            },
            "font_sizes": {
                "h1": "2.5rem",
                "h2": "2rem",
                "body": "1rem"
            }
        },
        "spacing": {
            "margins": {"small": "0.5rem", "medium": "1rem", "large": "2rem"},
            "paddings": {"small": "0.5rem", "medium": "1rem", "large": "2rem"}
        }
    },
    "asset_type": "hero_image",
    "generation_quality": "premium",
    "prompt_template": "Modern tech startup hero section with {color_scheme} color scheme",
    "style_characteristics": {
        "visual_style": "modern",
        "complexity": "minimal",
        "mood": "professional",
        "aesthetic": "clean"
    },
    "success_metrics": {
        "generation_time": 3.2,
        "quality_rating": 0.92,
        "user_satisfaction": 0.95
    },
    "provider_preferences": {
        "local_sdxl": 0.9,
        "openai_dalle3": 0.8,
        "stability_ai": 0.7
    },
    "quality_score": 0.92
}

# Store the pattern
result = mcp__enhanced-memory-mcp__store_image_gen_pattern(design_pattern_data)
print(f"Stored pattern ID: {result['pattern_id']}")

# Example 2: Find best patterns for generating a specific asset type
search_params = {
    "asset_type": "hero_image",
    "design_tokens": {
        "colors": {
            "palette": {
                "primary": "#3b82f6"  # Similar blue tone
            }
        }
    },
    "max_results": 5
}

best_patterns = mcp__enhanced-memory-mcp__get_best_patterns_for_asset_type(**search_params)
print(f"Found {len(best_patterns['patterns'])} matching patterns")

# Example 3: Track component generation results
component_tracking = {
    "component_type": "button",
    "design_pattern_id": result['pattern_id'],
    "dimensions": [120, 40],
    "variants": ["primary", "secondary", "outline"],
    "states": ["normal", "hover", "active", "disabled"],
    "generation_results": {
        "total_assets": 12,
        "successful": 12,
        "failed": 0,
        "generation_time": 45.2
    },
    "quality_metrics": {
        "overall_score": 0.88,
        "consistency_score": 0.92,
        "accessibility_score": 0.85
    }
}

tracking_result = mcp__enhanced-memory-mcp__track_component_generation(component_tracking)
print(f"Tracked component generation: {tracking_result['history_id']}")

# Example 4: Store style transfer mapping
style_mapping = {
    "source_style": "minimal_modern",
    "target_aesthetic": "professional",
    "transfer_intensity": 0.75,
    "enhancement_prompts": [
        "clean lines",
        "sophisticated typography",
        "subtle gradients",
        "corporate color scheme"
    ],
    "success_rate": 0.89,
    "metadata": {
        "projects_used": ["tech_startup", "saas_landing", "corporate_site"],
        "average_quality": 0.87
    }
}

mapping_result = mcp__enhanced-memory-mcp__store_style_transfer_mapping(style_mapping)
print(f"Stored style transfer mapping: {mapping_result['mapping_id']}")

# Example 5: Get optimization recommendations
optimization_context = {
    "asset_type": "hero_image",
    "target_format": "web",
    "quality_requirements": "high",
    "performance_critical": True
}

recommendations = mcp__enhanced-memory-mcp__get_optimization_recommendations(
    context=optimization_context
)
print(f"Got {len(recommendations['recommendations'])} optimization recommendations")

# Example 6: Analyze generation trends
trends = mcp__enhanced-memory-mcp__analyze_generation_trends()
print("Generation Trends Analysis:")
print(f"- Top asset type: {trends['asset_type_performance'][0]['asset_type']}")
print(f"- Best provider: {trends['provider_performance'][0]['provider']}")
print(f"- Most successful style transfer: {trends['style_transfer_performance'][0]['target_aesthetic']}")

# Example 7: Complete workflow - Website cloning with pattern learning
async def clone_website_with_learning(url: str):
    """
    Complete workflow showing how Image-Gen-MCP uses Enhanced-Memory-MCP
    for intelligent pattern-based asset generation
    """
    
    # 1. Extract design tokens from website (via Website-Scraper-MCP)
    design_tokens = await mcp__website-scraper-mcp__extract_design_tokens(url)
    
    # 2. Check if we have similar patterns stored
    similar_patterns = await mcp__enhanced-memory-mcp__get_best_patterns_for_asset_type(
        asset_type="hero_image",
        design_tokens=design_tokens['design_tokens'],
        max_results=3
    )
    
    if similar_patterns['patterns']:
        # 3. Use the best matching pattern as a template
        best_pattern = similar_patterns['patterns'][0]
        
        # 4. Generate hero image using stored pattern knowledge
        hero_result = await mcp__image-gen__generate_design_system_asset(
            design_tokens=design_tokens['design_tokens'],
            asset_type="hero_image",
            description="Professional hero section matching website style",
            quality="premium"
        )
        
        # 5. Store the successful generation pattern
        if hero_result['success']:
            pattern_data = {
                "design_tokens": design_tokens['design_tokens'],
                "asset_type": "hero_image",
                "generation_quality": "premium",
                "prompt_template": hero_result.get('enhanced_prompt', ''),
                "style_characteristics": design_tokens.get('style_analysis', {}),
                "success_metrics": {
                    "generation_time": hero_result.get('generation_time', 0),
                    "quality_rating": hero_result.get('quality_score', 0)
                },
                "provider_preferences": {
                    hero_result.get('provider_used', 'unknown'): 1.0
                },
                "quality_score": hero_result.get('quality_score', 0.8)
            }
            
            await mcp__enhanced-memory-mcp__store_image_gen_pattern(pattern_data)
    
    # 6. Generate missing icons with learning
    icon_list = ["search", "menu", "user", "settings"]
    
    # Check for similar icon patterns
    icon_patterns = await mcp__enhanced-memory-mcp__get_best_patterns_for_asset_type(
        asset_type="icon",
        design_tokens=design_tokens['design_tokens'],
        max_results=5
    )
    
    # Generate icons using best practices from memory
    icons_result = await mcp__image-gen__create_missing_icons(
        icon_list=icon_list,
        design_tokens=design_tokens['design_tokens'],
        quality="premium"
    )
    
    # 7. Track component generation success
    if icons_result['success']:
        await mcp__enhanced-memory-mcp__track_component_generation({
            "component_type": "icon",
            "dimensions": [32, 32],
            "variants": icon_list,
            "states": ["normal"],
            "generation_results": {
                "total_assets": len(icon_list),
                "successful": len(icons_result.get('generated_icons', [])),
                "generation_time": icons_result.get('total_time', 0)
            },
            "quality_metrics": {
                "overall_score": icons_result.get('average_quality', 0),
                "consistency_score": icons_result.get('consistency_score', 0)
            }
        })
    
    # 8. Analyze trends to improve future generations
    trends = await mcp__enhanced-memory-mcp__analyze_generation_trends()
    
    return {
        "design_tokens": design_tokens,
        "hero_image": hero_result,
        "icons": icons_result,
        "patterns_used": similar_patterns['patterns_found'],
        "trends": trends['insights']
    }

# Example 8: Pattern-based optimization workflow
def optimize_assets_with_memory(asset_paths: list, context: dict):
    """
    Use stored optimization patterns to intelligently optimize assets
    """
    
    # 1. Get optimization recommendations based on context
    recommendations = mcp__enhanced-memory-mcp__get_optimization_recommendations(
        context=context
    )
    
    if recommendations['recommendations']:
        # 2. Use the best recommendation
        best_preset = recommendations['recommendations'][0]
        
        # 3. Apply optimization with recommended settings
        optimization_result = mcp__image-gen__optimize_assets_for_web(
            asset_paths=asset_paths,
            optimization_preset=best_preset['preset_name'],
            custom_settings=best_preset.get('configuration', {})
        )
        
        # 4. Store successful optimization pattern
        if optimization_result['success']:
            new_preset_data = {
                "preset_name": f"custom_{context.get('asset_type', 'general')}_{int(time.time())}",
                "preset_type": context.get('target_format', 'web'),
                "configuration": best_preset.get('configuration', {}),
                "performance_metrics": optimization_result.get('performance_metrics', {}),
                "use_cases": [context.get('asset_type', 'general')],
                "success_rate": optimization_result.get('compression_ratio', 0) / 100
            }
            
            # This would be stored in the optimization_presets table
            # (implementation would be added to image_gen_pattern_integration.py)
        
        return optimization_result
    
    # Fallback to default optimization
    return mcp__image-gen__optimize_assets_for_web(
        asset_paths=asset_paths,
        optimization_preset="web_performance"
    )

# Example 9: Learning from successful clones
async def learn_from_clone_success(clone_operation_id: int):
    """
    Extract patterns from a successful clone operation and store for future use
    """
    
    # 1. Get clone operation details
    clone_data = await mcp__enhanced-memory-mcp__get_clone_operation_details(
        clone_operation_id=clone_operation_id
    )
    
    if clone_data['success'] and clone_data['quality_score'] > 0.8:
        # 2. Extract design patterns used
        design_patterns = clone_data.get('design_patterns_used', [])
        
        for pattern in design_patterns:
            # 3. Update pattern success metrics
            await mcp__enhanced-memory-mcp__track_pattern_usage(
                pattern_id=pattern['id'],
                usage_data={
                    "usage_type": "clone_operation",
                    "project_context": clone_data.get('target_description', ''),
                    "success_rating": clone_data['quality_score'],
                    "performance_metrics": {
                        "clone_time": clone_data.get('total_time', 0),
                        "asset_count": clone_data.get('assets_generated', 0)
                    },
                    "user_feedback": clone_data.get('user_feedback', '')
                }
            )
        
        # 4. Extract and store any new patterns discovered
        if clone_data.get('new_patterns_discovered'):
            for new_pattern in clone_data['new_patterns_discovered']:
                await mcp__enhanced-memory-mcp__store_design_pattern(new_pattern)
    
    return {
        "patterns_updated": len(design_patterns),
        "new_patterns_stored": len(clone_data.get('new_patterns_discovered', [])),
        "learning_complete": True
    }

print("\n🎨 Image Generation Pattern Integration configured successfully!")
print("The Enhanced-Memory-MCP now provides intelligent pattern storage and retrieval")
print("for the enhanced Image-Gen-MCP, enabling continuous learning and improvement.")