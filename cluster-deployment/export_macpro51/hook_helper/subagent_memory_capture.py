#!/usr/bin/env python3
"""
Subagent memory capture hook - Capture subagent results to memory.
"""
import sys
import json
import re
from datetime import datetime

def capture_subagent_memory(subagent_type, result):
    """Capture subagent results and learnings to memory system."""
    
    try:
        # Parse subagent type
        if not subagent_type:
            return False
        
        # Extract agent name and specialization
        agent_match = re.match(r'([🎯🏗️🐨🐸🐻🦉🔒🦋🐢🎨🦆🐙🪶🔧📱💻]+)\s*(.*)', subagent_type)
        if agent_match:
            agent_emoji = agent_match.group(1)
            agent_name = agent_match.group(2).strip()
        else:
            agent_emoji = "🤖"
            agent_name = subagent_type
        
        # Analyze result for key learnings
        result_str = str(result)
        
        # Extract key information
        memory_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_type': subagent_type,
            'agent_emoji': agent_emoji,
            'agent_name': agent_name,
            'result_length': len(result_str),
            'success_indicators': [],
            'learnings': [],
            'patterns': [],
            'errors': []
        }
        
        # Analyze for success patterns
        success_patterns = [
            r'✅|✓|completed successfully|task completed',
            r'implemented|created|built|deployed',
            r'working correctly|functioning as expected',
            r'tests passing|validation successful'
        ]
        
        for pattern in success_patterns:
            matches = re.findall(pattern, result_str, re.IGNORECASE)
            if matches:
                memory_entry['success_indicators'].extend(matches)
        
        # Extract error patterns for learning
        error_patterns = [
            r'error:|exception:|failed:|❌',
            r'could not|unable to|cannot',
            r'timeout|connection refused|not found'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, result_str, re.IGNORECASE)
            if matches:
                memory_entry['errors'].extend(matches)
        
        # Extract learning patterns
        learning_patterns = [
            r'learned that|discovered|found that|realized',
            r'improved by|optimized by|enhanced by',
            r'best practice|recommendation|suggestion',
            r'pattern identified|approach used|method applied'
        ]
        
        for pattern in learning_patterns:
            matches = re.findall(pattern, result_str, re.IGNORECASE)
            if matches:
                memory_entry['learnings'].extend(matches)
        
        # Determine performance metrics
        performance_score = 0.5  # Default
        
        if memory_entry['success_indicators']:
            performance_score += 0.3
        if memory_entry['learnings']:
            performance_score += 0.2
        if memory_entry['errors']:
            performance_score -= 0.3
        
        memory_entry['performance_score'] = max(0.0, min(1.0, performance_score))
        
        # Save to subagent memory log
        memory_log = '/home/marc/.claude/.subagent_memory.log'
        with open(memory_log, 'a') as f:
            f.write(json.dumps(memory_entry) + '\n')
        
        # Try to integrate with enhanced-memory-mcp if available
        try:
            import sys
            sys.path.append('/home/marc/.claude')
            
            # Create memory entity for the subagent result
            entity_data = {
                'name': f"SubagentResult-{agent_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'entityType': 'subagent_result',
                'observations': [
                    f"Agent: {subagent_type}",
                    f"Performance: {performance_score:.2f}",
                    f"Success indicators: {len(memory_entry['success_indicators'])}",
                    f"Learnings: {len(memory_entry['learnings'])}",
                    f"Result length: {memory_entry['result_length']} chars"
                ]
            }
            
            # If there are specific learnings, add them
            if memory_entry['learnings']:
                entity_data['observations'].extend(memory_entry['learnings'][:3])  # Top 3 learnings
            
            print(f"🧠 Captured {agent_name} memory:")
            print(f"   Performance: {performance_score:.2f}")
            print(f"   Success indicators: {len(memory_entry['success_indicators'])}")
            print(f"   Learnings: {len(memory_entry['learnings'])}")
            print(f"   Entity created for memory integration")
            
        except Exception as e:
            print(f"⚠️  Memory integration error: {e}")
        
        # Update subagent statistics
        stats_file = '/home/marc/.claude/.subagent_stats.json'
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {'agents': {}, 'total_completions': 0, 'average_performance': 0.5}
        
        # Update agent-specific stats
        if agent_name not in stats['agents']:
            stats['agents'][agent_name] = {
                'completions': 0,
                'total_performance': 0,
                'average_performance': 0.5,
                'success_rate': 0.5
            }
        
        agent_stats = stats['agents'][agent_name]
        agent_stats['completions'] += 1
        agent_stats['total_performance'] += performance_score
        agent_stats['average_performance'] = agent_stats['total_performance'] / agent_stats['completions']
        
        # Update global stats
        stats['total_completions'] += 1
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error capturing subagent memory: {e}", file=sys.stderr)
        return False

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(0)
            
        subagent_type = sys.argv[1]
        result = sys.argv[2]
        
        capture_subagent_memory(subagent_type, result)
        sys.exit(0)  # Always continue
        
    except Exception as e:
        print(f"Error in subagent memory capture hook: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()