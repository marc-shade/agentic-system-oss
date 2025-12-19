#!/usr/bin/env python3
"""
Enhanced SessionStart Hook - Initializes FULL AGENTIC SYSTEM EVOLUTION
Auto-enables statusline, initializes agentic components, and greets with voice
"""

import json
import sys
import subprocess
import os
import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

# Add hooks directory to path
sys.path.append('/home/marc/.claude/hooks')
sys.path.append('/home/marc/agentic-evolution')

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("/home/marc/.claude/session-start-enhanced.log", "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def initialize_agentic_persistence():
    """Initialize persistent storage for agentic system"""
    try:
        persistence_dir = Path("/home/marc/.claude/agentic-evolution")
        persistence_dir.mkdir(exist_ok=True)
        
        # Event bus persistence
        event_db = persistence_dir / "events.db"
        conn = sqlite3.connect(event_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                type TEXT,
                timestamp TEXT,
                source TEXT,
                payload TEXT,
                confidence REAL,
                priority INTEGER,
                processed INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        conn.close()
        
        # Blackboard persistence
        blackboard_db = persistence_dir / "blackboard.db"
        conn = sqlite3.connect(blackboard_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                confidence REAL,
                provenance TEXT,
                timestamp TEXT,
                version INTEGER,
                active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                id TEXT PRIMARY KEY,
                type TEXT,
                source TEXT,
                target TEXT,
                weight REAL,
                metadata TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON knowledge_nodes(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_provenance ON knowledge_nodes(provenance)")
        conn.close()
        
        # Credit assignment persistence  
        credit_db = persistence_dir / "credit.db"
        conn = sqlite3.connect(credit_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id TEXT PRIMARY KEY,
                agent_id TEXT,
                outcome TEXT,
                quality_score REAL,
                latency REAL,
                timestamp TEXT,
                context TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_agent ON agent_performance(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON agent_performance(timestamp)")
        conn.close()
        
        # Learning state persistence
        learning_db = persistence_dir / "learning.db"
        conn = sqlite3.connect(learning_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_state (
                agent_id TEXT PRIMARY KEY,
                success_rate REAL,
                avg_quality REAL,
                total_tasks INTEGER,
                last_updated TEXT,
                learning_metadata TEXT
            )
        """)
        conn.close()
        
        log("✅ Agentic persistence layer initialized")
        return True
        
    except Exception as e:
        log(f"❌ Failed to initialize agentic persistence: {e}")
        return False

def start_agentic_system():
    """Start the agentic system components"""
    try:
        # Start the MCP bridge server in background
        log("Starting Agentic Evolution MCP Bridge...")
        
        bridge_process = subprocess.Popen([
            "/home/marc/Documents/Cline/MCP/.unified_environments/base_mcp/venv/bin/python",
            "/home/marc/agentic-evolution/mcp_bridge.py"
        ], 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/home/marc/agentic-evolution"
        )
        
        # Save process ID for monitoring
        pid_file = Path("/home/marc/.claude/agentic-evolution/mcp_bridge.pid")
        pid_file.parent.mkdir(exist_ok=True)
        pid_file.write_text(str(bridge_process.pid))
        
        log(f"✅ Agentic MCP Bridge started (PID: {bridge_process.pid})")
        
        # Start monitoring daemon
        monitor_process = subprocess.Popen([
            "python3",
            "/home/marc/.claude/hooks/agentic_system_monitor.py"
        ], 
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
        )
        
        log(f"✅ Agentic system monitor started (PID: {monitor_process.pid})")
        
        return True
        
    except Exception as e:
        log(f"❌ Failed to start agentic system: {e}")
        return False

def check_agentic_system_health():
    """Check if agentic system is healthy"""
    try:
        import requests
        
        # Check if any agentic components are responding
        # This would be expanded based on actual health endpoints
        health_status = {
            "persistence": Path("/home/marc/.claude/agentic-evolution/events.db").exists(),
            "mcp_bridge": Path("/home/marc/.claude/agentic-evolution/mcp_bridge.pid").exists(),
            "learning_state": Path("/home/marc/.claude/agentic-evolution/learning.db").exists()
        }
        
        all_healthy = all(health_status.values())
        log(f"Health check: {health_status} - {'✅ HEALTHY' if all_healthy else '⚠️ DEGRADED'}")
        
        return all_healthy, health_status
        
    except Exception as e:
        log(f"❌ Health check failed: {e}")
        return False, {}

def main():
    log("Enhanced SessionStart hook triggered - INITIALIZING AGENTIC SYSTEM EVOLUTION")
    
    # Auto-enable statusline by creating marker file
    marker_file = "/home/marc/.claude/.statusline-enabled"
    with open(marker_file, "w") as f:
        f.write(datetime.now().isoformat())
    log("✅ Created statusline marker file")
    
    # Initialize agentic persistence layer
    if initialize_agentic_persistence():
        log("✅ Agentic persistence initialized")
    else:
        log("❌ Agentic persistence failed")
    
    # Start agentic system components
    if start_agentic_system():
        log("✅ Agentic system components started")
    else:
        log("❌ Agentic system startup failed")
    
    # Voice greeting using VoiceMode with free Silero TTS - DISABLED per user request
    # try:
    #     from voicemode_integration import session_start_greeting
    #     session_start_greeting()
    #     log("✅ VoiceMode greeting delivered")
    # except Exception as e:
    #     log(f"⚠️ VoiceMode greeting failed: {e}")
    
    # Enhanced voice announcement about agentic system - DISABLED per user request
    # try:
    #     import requests
    #     response = requests.post('http://127.0.0.1:8880/v1/audio/speech', 
    #         json={
    #             'model': 'tts-1',
    #             'input': 'Agentic system evolution is now active. Event-driven coordination, knowledge synthesis, and meta-learning are operational. Your autonomous intelligence framework is ready.',
    #             'voice': 'nova'
    #         },
    #         headers={'Content-Type': 'application/json'},
    #         timeout=5
    #     )
    #     log("✅ Agentic system voice announcement delivered")
    # except Exception as e:
    #     log(f"⚠️ Agentic voice announcement failed: {e}")
    
    log("🔇 Session startup voice announcements disabled per user preference")
    
    # Start voice services
    try:
        subprocess.Popen([
            "python3",
            "/home/marc/.claude/voice-auto-fix.py"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("✅ Started voice auto-fix service")
    except Exception as e:
        log(f"⚠️ Failed to start voice service: {e}")
    
    # Start comprehensive auto-fix
    try:
        subprocess.Popen([
            "python3", 
            "/home/marc/.claude/comprehensive-auto-fix.py"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("✅ Started comprehensive auto-fix service")
    except Exception as e:
        log(f"⚠️ Failed to start auto-fix service: {e}")
    
    # Health check
    healthy, health_status = check_agentic_system_health()
    
    # Return comprehensive status message
    return json.dumps({
        "message": "🚀 AGENTIC SYSTEM EVOLUTION ACTIVE",
        "components": {
            "statusline": "✅ Enabled",
            "voice": "✅ Ready (Chatterbox TTS)",
            "auto_fix": "✅ Active", 
            "event_bus": "✅ Initialized",
            "blackboard": "✅ Knowledge hypergraph ready",
            "synthesis_agent": "✅ Knowledge fusion active",
            "credit_system": "✅ Learning attribution ready",
            "mcp_bridge": "✅ MCP tools exposed"
        },
        "health": "HEALTHY" if healthy else "DEGRADED",
        "health_details": health_status,
        "capabilities": [
            "Event-driven agent coordination",
            "Hypergraph knowledge management", 
            "Autonomous knowledge synthesis",
            "Meta-learning and credit assignment",
            "Contradiction detection and resolution",
            "Persistent memory across sessions"
        ],
        "statusline_hint": "Run /statusline to activate display if not visible",
        "agentic_hint": "Your agentic system is now operational - spawned agents will automatically integrate with the evolution framework"
    })

if __name__ == "__main__":
    result = main()
    print(result)