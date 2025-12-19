#!/usr/bin/env python3
"""
Environmental Awareness Hook - Sonnet 4.5 Optimization
Runs on Claude Code startup to provide complete situational awareness
Stores system state in enhanced-memory-mcp for persistent awareness
"""

import json
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

def run_command(cmd):
    """Execute shell command and return output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

def check_running_services():
    """Check what services are currently running"""
    services = {
        "kokoro_tts": run_command("ps aux | grep '[k]okoro' | head -1"),
        "temporal": run_command("ps aux | grep '[t]emporal' | head -1"),
        "autokitteh": run_command("ps aux | grep '[a]utokitteh' | head -1"),
        "whisper": run_command("ps aux | grep '[w]hisper' | head -1"),
        "mcp_servers": run_command("ps aux | grep '[m]cp' | wc -l"),
    }

    running = []
    for service, output in services.items():
        if output and "ERROR" not in output and output != "0":
            running.append(service)

    return {
        "running_services": running,
        "total_mcp_processes": services["mcp_servers"]
    }

def check_mcp_configuration():
    """Check MCP configuration status"""
    home = os.path.expanduser("~")
    config_paths = [
        f"{home}/.claude.json",
        f"{home}/.config/claude-code/mcp-override.json",
        f"{home}/Documents/Cline/MCP/optimized-mcp-config.json"
    ]

    configs = {}
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    if "mcpServers" in data:
                        configs[Path(path).name] = {
                            "servers_count": len([k for k in data["mcpServers"].keys() if not k.startswith("_")]),
                            "path": path,
                            "size_kb": os.path.getsize(path) // 1024
                        }
            except:
                pass

    return configs

def check_voice_system():
    """Check voice system status"""
    voice_status = {
        "kokoro_running": bool(run_command("ps aux | grep '[k]okoro' | head -1")),
        "voicemode_dir": os.path.exists(os.path.expanduser("~/.voicemode")),
        "voice_mode_mcp": os.path.exists("/opt/homebrew/lib/python3.10/site-packages/voice_mode"),
    }
    return voice_status

def check_disk_space():
    """Check available disk space"""
    output = run_command("df -h / | tail -1 | awk '{print $4}'")
    return output

def check_git_status():
    """Check git repository status"""
    cwd = os.getcwd()
    git_status = run_command("git status --short 2>/dev/null | wc -l")
    current_branch = run_command("git branch --show-current 2>/dev/null")

    return {
        "working_directory": cwd,
        "modified_files": git_status if git_status else "0",
        "branch": current_branch if current_branch else "N/A"
    }

def check_sensory_consciousness():
    """Check sensory consciousness system status"""
    import sqlite3

    # Check FILES drive location first, then fall back to old location
    sensory_db = Path("/Volumes/FILES/agentic-system/data/sensory/sensory_memory.db")
    if not sensory_db.exists():
        sensory_db = Path.home() / ".voicemode" / "sensory" / "sensory_memory.db"

    if not sensory_db.exists():
        return {
            "status": "not_initialized",
            "note": "Run sensory consciousness daemon to initialize"
        }

    try:
        conn = sqlite3.connect(str(sensory_db))
        cursor = conn.cursor()

        # Get total events
        cursor.execute("SELECT COUNT(*) FROM sensory_events")
        total = cursor.fetchone()[0]

        # Get recent screenshots
        cursor.execute("""
            SELECT COUNT(*) FROM sensory_events
            WHERE event_type = 'vision_screenshot'
            AND timestamp > datetime('now', '-1 hour')
        """)
        recent_screenshots = cursor.fetchone()[0]

        # Get recent system state captures
        cursor.execute("""
            SELECT COUNT(*) FROM sensory_events
            WHERE event_type = 'system_state'
            AND timestamp > datetime('now', '-1 hour')
        """)
        recent_states = cursor.fetchone()[0]

        # Get latest vision timestamp
        cursor.execute("""
            SELECT timestamp FROM sensory_events
            WHERE event_type = 'vision_screenshot'
            ORDER BY timestamp DESC LIMIT 1
        """)
        result = cursor.fetchone()
        latest_vision = result[0] if result else "never"

        conn.close()

        return {
            "status": "active",
            "total_events": total,
            "recent_screenshots_1h": recent_screenshots,
            "recent_states_1h": recent_states,
            "latest_vision": latest_vision,
            "database_path": str(sensory_db)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def generate_awareness_report():
    """Generate complete environmental awareness report"""

    report = {
        "timestamp": datetime.now().isoformat(),
        "model": "claude-sonnet-4-5-20250929",
        "system_state": {
            "services": check_running_services(),
            "mcp_configs": check_mcp_configuration(),
            "voice_system": check_voice_system(),
            "sensory_consciousness": check_sensory_consciousness(),
            "disk_available": check_disk_space(),
            "git": check_git_status(),
        },
        "capabilities_available": [
            "enhanced-memory-mcp",
            "voice-mode",
            "claude-flow",
            "sequential-thinking",
            "image-gen (if configured)",
            "meta-cognition (if configured)",
            "agent-runtime (if configured)",
            "task-manager (if configured)",
        ],
        "sonnet_45_features": {
            "30_hour_focus": True,
            "parallel_tool_execution": True,
            "native_memory": True,
            "tool_use_clearing": True,
            "token_tracking": True,
            "reduced_sycophancy": True,
            "osworld_score": 0.614
        }
    }

    return report

def main():
    """Main hook execution"""
    try:
        report = generate_awareness_report()

        # Save to file for reference
        output_path = os.path.expanduser("~/.claude/environmental-awareness.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary to stdout (visible to Claude)
        print(f"\n🌍 Environmental Awareness Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📍 Location: {report['system_state']['git']['working_directory']}")
        print(f"🚀 Running Services: {', '.join(report['system_state']['services']['running_services']) or 'None detected'}")
        print(f"🔧 MCP Configs: {len(report['system_state']['mcp_configs'])} found")
        print(f"💾 Disk Available: {report['system_state']['disk_available']}")
        print(f"🎤 Voice System: {'✅ Active' if report['system_state']['voice_system']['kokoro_running'] else '⚠️  Inactive'}")

        # Sensory consciousness status
        sensory = report['system_state']['sensory_consciousness']
        if sensory['status'] == 'active':
            print(f"👁️  Sensory System: ✅ Active ({sensory['total_events']} total events, {sensory['recent_screenshots_1h']} screenshots last hour)")
        elif sensory['status'] == 'not_initialized':
            print(f"👁️  Sensory System: ⚠️  Not initialized")
        else:
            print(f"👁️  Sensory System: ❌ Error: {sensory.get('error', 'unknown')}")

        print(f"📊 Git Status: {report['system_state']['git']['branch']} ({report['system_state']['git']['modified_files']} modified)")
        print(f"🧠 Model: Sonnet 4.5 (30hr focus, parallel execution, 61.4% OSWorld)")
        print(f"📄 Full report: {output_path}\n")

        return 0

    except Exception as e:
        print(f"❌ Environmental awareness hook failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
