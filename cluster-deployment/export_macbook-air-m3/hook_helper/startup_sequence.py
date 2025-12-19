#!/usr/bin/env python3
"""
Startup Sequence Hook
Initializes all core systems at session start
"""
import sys
import subprocess
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def run_command(cmd):
    """Run a command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        return None

def initialize_systems():
    """Initialize all core systems"""
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "systems": {}
    }
    
    # 1. Voice System - Test unified voice MCP
    voice_check = run_command("""python3 -c "
import subprocess
import sys
try:
    # Test unified voice MCP availability
    result = subprocess.run([
        'python3', '/Users/marc/.claude/voice_test_script.py'
    ], capture_output=True, text=True, timeout=30)
    if 'Audio playback successful' in result.stdout:
        print('VOICE_RESULT:active')
    else:
        print('VOICE_RESULT:partial')
except:
    print('VOICE_RESULT:failed')
" 2>/dev/null | grep 'VOICE_RESULT:' | cut -d: -f2""")
    results["systems"]["voice"] = voice_check == "active"
    
    # 2. Timestamp Verification
    timestamp_check = run_command("""python3 -c "
from datetime import datetime
import sys
print('TIMESTAMP_RESULT:Date: ' + datetime.now().strftime('%Y-%m-%d') + ' Time: ' + datetime.now().strftime('%H:%M:%S'))
" | grep 'TIMESTAMP_RESULT:' | cut -d: -f2-""")
    results["systems"]["timestamp"] = bool(timestamp_check) and "Date:" in str(timestamp_check)
    
    # 3. Principle 0 Enforcement
    p0_check = run_command("""python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
try:
    from principle_0_orchestrator_hook import PRINCIPLE_0_ENFORCER, p0_stats
    stats = p0_stats()
    print('P0_RESULT:Score: ' + str(stats.get('score', 0)) + '/100')
except Exception as e:
    print('P0_RESULT:failed')
" 2>/dev/null | grep 'P0_RESULT:' | cut -d: -f2-""")
    results["systems"]["principle_0"] = "Score:" in str(p0_check)
    
    # 4. Privacy Detection
    privacy_check = run_command("""python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
try:
    from privacy_detection_hook import check_privacy_requirement
    print('active')
except:
    print('failed')"
""")
    results["systems"]["privacy_detection"] = privacy_check == "active"
    
    # 5. Enhanced Delegation
    delegation_check = run_command("""python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
try:
    from enhanced_delegation_hooks import setup_enhanced_delegation_system
    result = setup_enhanced_delegation_system()
    test_results = result.get('test_results', {})
    print('active' if test_results.get('system_functional', False) else 'failed')
except Exception as e:
    print('failed')
" 2>/dev/null""")
    results["systems"]["delegation_enforcement"] = delegation_check == "active"
    
    # 6. Darwin Gödel Machine
    dgm_check = run_command("""python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
try:
    from start_autonomous_dgm import dgm_startup_check
    success = dgm_startup_check()
    print('active' if success else 'failed')
except:
    print('failed')"
""")
    results["systems"]["dgm"] = dgm_check == "active"
    
    # 7. Health Monitor
    health_check = run_command("python3 /Users/marc/.claude/health-monitor-simple.py 2>/dev/null | grep -c 'HEALTHY'")
    results["systems"]["health_monitor"] = bool(health_check) and (health_check.strip() == "1" or "HEALTHY" in str(health_check))

    # 8. Local System Agent status
    agent_status_path = Path("/Users/marc/.claude/system_agent_status.json")
    agent_ok = False
    if agent_status_path.exists():
        try:
            agent_status = json.loads(agent_status_path.read_text(encoding="utf-8"))
            timestamp_str = agent_status.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - timestamp
                agent_ok = age.total_seconds() < 600 and bool(agent_status.get("analysis"))
        except Exception:
            agent_ok = False
    results["systems"]["local_system_agent"] = agent_ok
    
    # Calculate overall status
    total_systems = len(results["systems"])
    active_systems = sum(1 for v in results["systems"].values() if v)
    results["overall_status"] = f"{active_systems}/{total_systems} systems active"
    results["ready"] = active_systems >= total_systems * 0.8  # 80% threshold
    
    return results

def main():
    """Main execution"""
    results = initialize_systems()
    
    if results["ready"]:
        response = {
            "allow": True,
            "message": f"✅ System initialized: {results['overall_status']}"
        }
    else:
        failed_systems = [k for k, v in results["systems"].items() if not v]
        response = {
            "allow": True,  # Still allow but warn
            "message": f"⚠️ Partial initialization: {results['overall_status']}\n" +
                      f"Failed systems: {', '.join(failed_systems)}"
        }
    
    # Log results
    log_file = "/Users/marc/.claude/startup_log.json"
    try:
        with open(log_file, "w") as f:
            json.dump(results, f, indent=2)
    except:
        pass
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()
