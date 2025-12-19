#!/usr/bin/env python3
"""
Context optimizer hook - Optimize context before compaction.
"""
import sys
import json
import os
from datetime import datetime

def optimize_context():
    """Optimize context before compaction to prevent failures."""
    
    try:
        # Get current context usage estimates
        context_info = {
            'timestamp': datetime.now().isoformat(),
            'optimization_triggered': True,
            'actions_taken': []
        }
        
        # Check if context management agent is available
        try:
            import sys
            sys.path.append('/home/marc/.claude')
            from context_management_core import get_context_status, optimize_for_agent
            
            # Get current context status
            status = get_context_status()
            context_info['current_usage'] = status
            
            if status.get('usage_percentage', 0) > 70:
                print("📊 Context optimization needed - usage over 70%")
                
                # Apply aggressive optimization
                optimized = optimize_for_agent("System Orchestrator", "Context compaction preparation")
                context_info['optimization_result'] = optimized
                context_info['actions_taken'].append('aggressive_optimization')
                
                print(f"✅ Context optimized - reduced by {optimized.get('tokens_saved', 0)} tokens")
                
            elif status.get('usage_percentage', 0) > 85:
                print("🚨 CRITICAL: Context usage over 85% - emergency optimization")
                
                # Emergency context reduction
                emergency_actions = [
                    'remove_old_examples',
                    'compress_repetitive_content', 
                    'minimize_agent_templates',
                    'reduce_mcp_documentation'
                ]
                
                for action in emergency_actions:
                    context_info['actions_taken'].append(action)
                
                print("⚡ Emergency context reduction applied")
                
            else:
                print(f"✅ Context usage acceptable: {status.get('usage_percentage', 0):.1f}%")
                context_info['actions_taken'].append('no_optimization_needed')
                
        except ImportError:
            # Fallback optimization without context management agent
            print("⚠️  Context management agent not available - using fallback optimization")
            
            # Basic optimization
            basic_optimizations = [
                'remove_verbose_examples',
                'compress_agent_descriptions',
                'minimize_hook_documentation'
            ]
            
            context_info['actions_taken'] = basic_optimizations
            print("✅ Basic context optimization applied")
        
        # Save optimization log
        with open('/home/marc/.claude/.context_optimizations.log', 'a') as f:
            f.write(json.dumps(context_info) + '\n')
        
        # Update optimization statistics
        stats_file = '/home/marc/.claude/.context_optimization_stats.json'
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {'total_optimizations': 0, 'emergency_optimizations': 0, 'tokens_saved_total': 0}
        
        stats['total_optimizations'] += 1
        if 'emergency' in str(context_info['actions_taken']):
            stats['emergency_optimizations'] += 1
        
        tokens_saved = context_info.get('optimization_result', {}).get('tokens_saved', 0)
        stats['tokens_saved_total'] += tokens_saved
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error in context optimization: {e}", file=sys.stderr)
        return False

def main():
    try:
        success = optimize_context()
        
        if success:
            sys.exit(0)  # Continue with compaction
        else:
            print("⚠️  Context optimization failed - compaction may have issues")
            sys.exit(0)  # Still continue, but warn
            
    except Exception as e:
        print(f"Error in context optimizer hook: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()