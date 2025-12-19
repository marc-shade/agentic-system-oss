#!/usr/bin/env python3
"""
Memory sync hook - Sync memory state after response.
"""
import sys
import json
import subprocess
from datetime import datetime

def sync_memory_state():
    """Sync memory state with enhanced-memory-mcp after response completion."""
    
    try:
        # Check if enhanced-memory-mcp is available
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'enhanced-memory-mcp' not in result.stdout:
            print("⚠️  Enhanced Memory MCP not running - skipping memory sync")
            return False
        
        # Create memory sync entry
        sync_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'response_completion',
            'sync_type': 'automatic',
            'status': 'initiated'
        }
        
        # Log memory sync
        with open('/Users/marc/.claude/.memory_sync.log', 'a') as f:
            f.write(json.dumps(sync_entry) + '\n')
        
        # Trigger memory consolidation (if needed)
        import os
        consolidation_trigger = '/Users/marc/.claude/.memory_consolidation_needed'
        if os.path.exists(consolidation_trigger):
            print("📚 Triggering memory consolidation...")
            
            # Use MCP to trigger consolidation
            try:
                consolidation_cmd = [
                    'python3', '-c',
                    '''
import sys
sys.path.append('/Users/marc/.claude')
try:
    from enhanced_memory_integration import trigger_memory_consolidation
    result = trigger_memory_consolidation()
    print(f"Memory consolidation: {result}")
except Exception as e:
    print(f"Consolidation error: {e}")
'''
                ]
                
                result = subprocess.run(consolidation_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ Memory consolidation completed")
                    os.remove(consolidation_trigger)
                else:
                    print(f"⚠️  Memory consolidation warning: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("⚠️  Memory consolidation timeout - will retry later")
            except Exception as e:
                print(f"⚠️  Memory consolidation error: {e}")
        
        # Update sync statistics
        stats_file = '/Users/marc/.claude/.memory_sync_stats.json'
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {'total_syncs': 0, 'successful_syncs': 0, 'last_sync': None}
        
        stats['total_syncs'] += 1
        stats['successful_syncs'] += 1
        stats['last_sync'] = datetime.now().isoformat()
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"🧠 Memory sync completed ({stats['successful_syncs']}/{stats['total_syncs']})")
        return True
        
    except Exception as e:
        print(f"Error in memory sync: {e}", file=sys.stderr)
        return False

def main():
    try:
        sync_memory_state()
        sys.exit(0)  # Always continue
        
    except Exception as e:
        print(f"Error in memory sync hook: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()