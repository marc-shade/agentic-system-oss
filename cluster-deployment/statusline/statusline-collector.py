#!/usr/bin/env python3
"""
🐕 PIXEL THE CORGI - NES Retro Statusline Data Collector
8-bit style monitoring for AGENTIC SYSTEM observability.

Agentic metrics monitored:
- ⚙️ CPU usage (only shown if >= 50% - warning/critical)
- 🧩 Memory usage (only shown if >= 60% - warning/critical)
- ⏱️ Session time (Claude Code uptime)
- 📜 Context window usage (with staleness indicator ~)
- 🌐 Cluster nodes online (5-node cluster: macpro51/mac-studio/macmini/macbook-air/completeu)
- 📊 Action success rate with trend (↑↓→)
- 🧠 Memory entities & consolidations (with activity indicator 🔄/💤)
- 🆔 NMF identity blocks (Letta-style persona)
- 🎯 Goals & tasks (with blocked count ⏸)
- 🎤/🔇 Voice listening state (STT enabled/disabled)
- 🕳️ Knowledge gaps (with critical highlighting)
- 🌙 Consolidation age (since last memory consolidation)
- 🔄 Improvement queue (queued + in progress)
- 🐝 Hive mind / Swarm agents (co-op mode)
- 🐠 TPU status (Coral Edge TPU inferences)
- 👁️ AGI awakenings & success rate
- 📡 Node communication status (unread messages/actions)
- 🐳 Docker containers (running count)
- 📈 Session usage (current session consumption)
- 💳 Weekly allowance LEFT (Claude Max remaining %)

Color coding (NES palette):
- 🟢 Green: Good/healthy/available
- 🟡 Yellow: Warning/medium/caution
- 🔴 Red: Critical/high/danger
- ⚪ Gray: Inactive/disabled/stale
"""

import json
import sqlite3
import subprocess
import urllib.request
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import concurrent.futures

# NES Color Palette (authentic 8-bit feel)
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
# NES Primary Colors
NES_RED = "\033[91m"      # Bright red (Mario red)
NES_GREEN = "\033[92m"    # Bright green (Luigi green)
NES_YELLOW = "\033[93m"   # Bright yellow (Star power)
NES_BLUE = "\033[94m"     # Bright blue (Megaman blue)
NES_MAGENTA = "\033[95m"  # Bright magenta (Kirby pink)
NES_CYAN = "\033[96m"     # Bright cyan (Ice level)
NES_ORANGE = "\033[33m"   # Orange (Corgi color!)
# Legacy colors for compatibility
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GRAY = "\033[90m"

# Paths
AGENTIC_BASE = Path(os.environ.get("AGENTIC_SYSTEM", "/mnt/agentic-system"))
DATABASES = AGENTIC_BASE / "databases"
CLAUDE_DIR = Path.home() / ".claude"
VOICE_STATE = Path("/tmp/voice-mode-state.json")
HIVE_STATE = AGENTIC_BASE / ".hive-mind" / "current-session.json"
CONSOLIDATION_STATE = DATABASES / "consolidation_state.json"
IMPROVEMENT_QUEUE = AGENTIC_BASE / "intelligent-agents" / "improvement_queue.json"

# Thresholds
THRESHOLDS = {
    "cpu_warn": 50, "cpu_crit": 75,
    "mem_warn": 60, "mem_crit": 80,
    "load_warn": 12, "load_crit": 20,
    "success_warn": 80, "success_crit": 60,
}

def safe_json_load(path: Path) -> dict:
    """Safely load JSON file."""
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def query_db(db_path: Path, query: str, default=None):
    """Safely query SQLite database."""
    try:
        if db_path.exists():
            conn = sqlite3.connect(str(db_path), timeout=1)
            conn.row_factory = sqlite3.Row
            result = conn.execute(query).fetchall()
            conn.close()
            return [dict(row) for row in result]
    except Exception:
        pass
    return default or []

def color_by_threshold(value, warn, crit, invert=False):
    """Return color based on thresholds."""
    if invert:
        if value > warn: return GREEN
        elif value > crit: return YELLOW
        else: return RED
    else:
        if value < warn: return GREEN
        elif value < crit: return YELLOW
        else: return RED

# ═══════════════════════════════════════════════════════════════════════════════
# Data Collection Functions
# ═══════════════════════════════════════════════════════════════════════════════

def get_hardware_status() -> dict:
    """Get hardware status from local API."""
    try:
        with urllib.request.urlopen("http://localhost:8888/api/all", timeout=2) as r:
            data = json.loads(r.read())
            usage = data.get("usage", {})
            return {
                "cpu": usage.get("cpu", {}),
                "memory": usage.get("memory", {}),
                "storage": usage.get("storage", {}),
                "network": usage.get("network", {}),
                "specs": data.get("specs", {}),
                "services": data.get("services", {}),
            }
    except Exception:
        return {}

def get_cluster_status() -> dict:
    """Get cluster node status via Convex heartbeat API."""
    # First try Convex real-time cluster data
    try:
        req = urllib.request.Request(
            "http://192.168.1.27:3210/api/query",
            data=json.dumps({"path": "nodes:clusterHealth", "args": {}, "format": "json"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read())
            # Check for Convex API error response (returns HTTP 200 with status: "error")
            if data.get("status") == "error":
                raise ValueError("Convex API error")
            val = data.get("value", {})
            online = int(val.get("onlineCount", 0))
            total = int(val.get("totalNodes", 5))
            # Return synthetic status dict for compatibility
            return {f"node_{i}": {"online": i < online} for i in range(total)}
    except Exception:
        pass

    # Fallback: ping via mDNS hostnames (more reliable than static IPs)
    nodes = {
        "macpro51": {"host": "macpro51.local", "role": "builder"},
        "mac-studio": {"host": "Marcs-Mac-Studio.local", "role": "orchestrator"},
        "macmini": {"host": "macmini.local", "role": "small-inference"},
        "macbook-air": {"host": "Marcs-MacBook-Air.local", "role": "researcher"},
        "completeu": {"host": "completeu-server.local", "role": "ai-inference"},
    }

    def check_node(name_info):
        name, info = name_info
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", info["host"]],
                capture_output=True, timeout=1.5
            )
            return name, result.returncode == 0
        except Exception:
            return name, False

    status = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_node, item): item for item in nodes.items()}
        for future in concurrent.futures.as_completed(futures, timeout=2):
            try:
                name, online = future.result(timeout=0.5)
                status[name] = {"online": online, **nodes[name]}
            except Exception:
                name, info = futures[future]
                status[name] = {"online": False, **info}

    return status

def get_memory_status() -> dict:
    """Get enhanced memory system status."""
    status = {
        "entities": 0, "relations": 0, "working_memory": 0,
        "episodes": 0, "concepts": 0, "skills": 0,
        "consolidation": {}, "recent_activity": False,
    }

    # Primary: Enhanced Memory MCP database (correct location)
    enhanced_memory_db = CLAUDE_DIR / "enhanced_memories" / "memory.db"
    if enhanced_memory_db.exists():
        entities = query_db(enhanced_memory_db, "SELECT COUNT(*) as cnt FROM entities", [{"cnt": 0}])
        status["entities"] = entities[0].get("cnt", 0) if entities else 0

        # Check recent activity (last 5 minutes)
        recent = query_db(enhanced_memory_db, """
            SELECT COUNT(*) as cnt FROM entities
            WHERE datetime(last_accessed) > datetime('now', '-5 minutes')
        """, [{"cnt": 0}])
        status["recent_activity"] = (recent[0].get("cnt", 0) if recent else 0) > 0

        # Get 4-tier counts from enhanced memory if tables exist
        for table, key in [("working_memory", "working_memory"), ("episodic_memory", "episodes"),
                          ("semantic_memory", "concepts"), ("procedural_memory", "skills")]:
            try:
                result = query_db(enhanced_memory_db, f"SELECT COUNT(*) as cnt FROM {table}", [{"cnt": 0}])
                status[key] = result[0].get("cnt", 0) if result else 0
            except Exception:
                pass

        # Get consolidation stats from enhanced memory if available
        cons_stats = query_db(enhanced_memory_db, """
            SELECT COUNT(*) as total FROM consolidation_jobs WHERE status = 'completed'
        """, [{"total": 0}])
        if cons_stats and cons_stats[0].get("total", 0) > 0:
            status["consolidation"]["total"] = cons_stats[0].get("total", 0)

    # Fallback: Legacy database paths
    legacy_memory_db = DATABASES / "memory.db"
    if not status["entities"] and legacy_memory_db.exists():
        entities = query_db(legacy_memory_db, "SELECT COUNT(*) as cnt FROM entities", [{"cnt": 0}])
        status["entities"] = entities[0].get("cnt", 0) if entities else 0

    # Load consolidation state from JSON (fallback/additional source)
    consolidation_state = safe_json_load(CONSOLIDATION_STATE)
    if consolidation_state:
        if not status["consolidation"].get("total"):
            status["consolidation"]["total"] = consolidation_state.get("total_consolidations", 0)
        status["consolidation"]["session_count"] = consolidation_state.get("session_count", 0)
        status["consolidation"]["last"] = consolidation_state.get("last_consolidation", "")

    return status

def get_agent_runtime_status() -> dict:
    """Get goals and tasks from agent-runtime."""
    status = {
        "active_goals": 0, "completed_goals": 0,
        "pending_tasks": 0, "in_progress_tasks": 0, "blocked_tasks": 0,
    }

    runtime_db = DATABASES / "agent_runtime.db"
    if runtime_db.exists():
        goals = query_db(runtime_db, "SELECT status, COUNT(*) as cnt FROM goals GROUP BY status", [])
        for g in goals:
            if g.get("status") == "active":
                status["active_goals"] = g.get("cnt", 0)

        tasks = query_db(runtime_db, "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status", [])
        for t in tasks:
            s = t.get("status", "")
            cnt = t.get("cnt", 0)
            if s == "pending": status["pending_tasks"] = cnt
            elif s == "in_progress": status["in_progress_tasks"] = cnt

    return status

def get_action_outcomes() -> dict:
    """Get action success rate with trend."""
    status = {"rate": 0, "total": 0, "trend": "→"}

    memory_db = DATABASES / "memory.db"
    if memory_db.exists():
        result = query_db(memory_db, """
            SELECT
                COALESCE(ROUND(AVG(success_score) * 100), 0) as rate,
                COUNT(*) as total,
                COALESCE(ROUND(AVG(CASE WHEN created_at > datetime('now', '-1 hour')
                    THEN success_score END) * 100), 0) as recent_rate
            FROM action_outcomes WHERE created_at > datetime('now', '-24 hours')
        """, [{"rate": 0, "total": 0, "recent_rate": 0}])

        if result:
            status["rate"] = int(result[0].get("rate", 0))
            status["total"] = result[0].get("total", 0)
            recent = result[0].get("recent_rate", 0)
            if status["total"] > 5:
                if recent > status["rate"] + 5: status["trend"] = "↑"
                elif recent < status["rate"] - 5: status["trend"] = "↓"

    return status

def get_voice_status() -> dict:
    """Get voice listening state."""
    status = {"listening": False}

    if VOICE_STATE.exists():
        data = safe_json_load(VOICE_STATE)
        status["listening"] = data.get("stt_enabled", False)

    if not status["listening"]:
        try:
            result = subprocess.run(["pgrep", "-f", "voice.*listen|whisper"],
                                   capture_output=True, timeout=1)
            status["listening"] = result.returncode == 0
        except Exception:
            pass

    return status

def get_knowledge_gaps() -> dict:
    """Get knowledge gaps count."""
    status = {"gaps": 0, "critical": 0}

    memory_db = DATABASES / "memory.db"
    if memory_db.exists():
        result = query_db(memory_db, """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN severity >= 0.7 THEN 1 ELSE 0 END) as critical
            FROM knowledge_gaps WHERE status = 'open'
        """, [{"total": 0, "critical": 0}])
        if result:
            status["gaps"] = result[0].get("total", 0) or 0
            status["critical"] = result[0].get("critical", 0) or 0

    return status

def get_consolidation_age() -> dict:
    """Get time since last consolidation."""
    status = {"age_minutes": 9999, "time_str": ""}

    consolidation_state = safe_json_load(CONSOLIDATION_STATE)
    if consolidation_state:
        last_run = consolidation_state.get("last_consolidation", "")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                age = datetime.now(last_dt.tzinfo) - last_dt if last_dt.tzinfo else datetime.now() - last_dt
                status["age_minutes"] = int(age.total_seconds() / 60)
            except Exception:
                pass

    age = status["age_minutes"]
    if age < 60:
        status["time_str"] = f"{age}m"
    elif age < 1440:
        status["time_str"] = f"{age // 60}h"
    else:
        status["time_str"] = f"{age // 1440}d"

    return status

def get_improvement_status() -> dict:
    """Get improvement queue status."""
    status = {"queued": 0, "in_progress": 0}

    if IMPROVEMENT_QUEUE.exists():
        data = safe_json_load(IMPROVEMENT_QUEUE)
        status["queued"] = len(data.get("queued", []))
        status["in_progress"] = len(data.get("in_progress", []))

    return status

def get_hive_status() -> dict:
    """Get hive mind / swarm status."""
    status = {"active": False, "agents": 0}

    if HIVE_STATE.exists():
        data = safe_json_load(HIVE_STATE)
        status["active"] = data.get("active", False)
        status["agents"] = len(data.get("agents", []))

    # Check .claude-flow too
    flow_state = AGENTIC_BASE / ".claude-flow" / "swarm-state.json"
    if not status["active"] and flow_state.exists():
        data = safe_json_load(flow_state)
        status["active"] = data.get("active", False)
        status["agents"] = len(data.get("agents", []))

    return status

def get_tpu_status() -> dict:
    """Get Coral TPU status."""
    status = {"available": False, "inferences": 0}

    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=2)
        status["available"] = "18d1:9302" in result.stdout or "Google" in result.stdout
    except Exception:
        pass

    tpu_db = DATABASES / "tpu_usage.db"
    if tpu_db.exists():
        stats = query_db(tpu_db, """
            SELECT COUNT(*) as cnt FROM inference_log
            WHERE timestamp > datetime('now', '-1 hour')
        """, [{"cnt": 0}])
        status["inferences"] = stats[0].get("cnt", 0) if stats else 0

    return status

def get_agi_status() -> dict:
    """Get AGI development metrics."""
    status = {"awakenings": 0, "successful_sessions": 0}

    bootstrap = safe_json_load(DATABASES / "bootstrap_state.json")
    if bootstrap:
        status["awakenings"] = bootstrap.get("total_awakenings", 0)
        status["successful_sessions"] = bootstrap.get("successful_sessions", 0)

    return status

def get_docker_status() -> dict:
    """Get Docker container status."""
    status = {"running": 0, "containers": []}

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            containers = [c for c in result.stdout.strip().split("\n") if c]
            status["running"] = len(containers)
            status["containers"] = containers
    except Exception:
        pass

    return status

def get_comm_status() -> dict:
    """Get node communication status."""
    status = {"unread": 0, "pending_actions": 0, "connected": False}

    comm_file = DATABASES / "cluster" / "comm_status.json"
    if comm_file.exists():
        data = safe_json_load(comm_file)
        status["unread"] = data.get("unread_messages", 0)
        status["pending_actions"] = data.get("pending_actions", 0)
        status["connected"] = True

    return status


def get_nmf_block_status() -> dict:
    """Get Neural Memory Fabric identity block status (Letta-style blocks)."""
    import socket
    hostname = socket.gethostname().replace("-", "").replace(".", "_").lower()

    status = {
        "total_blocks": 0,
        "agents": [],
        "block_labels": [],
        "hostname": hostname,
    }

    all_blocks = []
    all_agents = set()

    # Database locations to check
    db_paths = [
        CLAUDE_DIR / "enhanced_memories" / "memory.db",  # Claude home
        AGENTIC_BASE / "databases" / "mcp" / "enhanced_memories.db",  # NMF MCP
    ]

    for db_path in db_paths:
        if db_path.exists():
            # Query nmf_memory_blocks table (NMF system)
            nmf_blocks = query_db(db_path, """
                SELECT agent_id, block_name FROM nmf_memory_blocks
                ORDER BY agent_id, block_name
            """, [])
            if nmf_blocks:
                all_blocks.extend(nmf_blocks)
                all_agents.update(b.get("agent_id", "") for b in nmf_blocks)

            # Query memory_blocks table (Letta integration)
            letta_blocks = query_db(db_path, """
                SELECT agent_id, label as block_name FROM memory_blocks
                ORDER BY agent_id, label
            """, [])
            if letta_blocks:
                all_blocks.extend(letta_blocks)
                all_agents.update(b.get("agent_id", "") for b in letta_blocks)

    if all_blocks:
        status["total_blocks"] = len(all_blocks)
        status["agents"] = list(all_agents)
        status["block_labels"] = [b.get("block_name", b.get("label", "")) for b in all_blocks]

    return status

def get_usage_status() -> dict:
    """Get Claude Code usage status."""
    usage = safe_json_load(CLAUDE_DIR / "usage_status.json")
    weekly_used = usage.get("weekly_all_percent", usage.get("weekly_usage_percent", 0))
    # Use previous values if current parse failed
    if weekly_used is None or weekly_used == 0:
        weekly_used = usage.get("previous_weekly", 0)
    session_used = usage.get("session_percent", usage.get("current_session_usage_percent", 0))
    if session_used is None or session_used == 0:
        session_used = usage.get("previous_session", 0)
    return {
        "session_pct": session_used or 0,
        "weekly_pct": weekly_used or 0,
        "weekly_left": 100 - (weekly_used or 0),
    }

def get_context_status() -> dict:
    """Get context window usage status."""
    status = {"percent": 0, "estimated": True, "stale": True}

    context_file = CLAUDE_DIR / "context_status.json"
    if context_file.exists():
        data = safe_json_load(context_file)
        if data:
            status["percent"] = data.get("percent", 0)
            status["estimated"] = data.get("estimated", True)
            status["total_tokens"] = data.get("total_tokens", 0)
            status["max_tokens"] = data.get("max_tokens", 200000)
            # Check staleness (older than 5 minutes)
            updated = data.get("updated_at", "")
            if updated:
                try:
                    update_time = datetime.fromisoformat(updated)
                    status["stale"] = (datetime.now() - update_time) > timedelta(minutes=5)
                except Exception:
                    status["stale"] = True

    return status

def get_session_time() -> dict:
    """Get Claude Code session elapsed time."""
    status = {"time_str": "", "minutes": 0}
    try:
        result = subprocess.run(
            ["pgrep", "-f", "^claude "],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            pid = result.stdout.strip().split('\n')[0]
            if pid:
                ps_result = subprocess.run(
                    ["ps", "-o", "etime=", "-p", pid],
                    capture_output=True, text=True, timeout=2
                )
                if ps_result.returncode == 0:
                    etime = ps_result.stdout.strip()
                    status["time_str"] = etime
                    # Parse etime (formats: MM:SS, HH:MM:SS, D-HH:MM:SS)
                    parts = etime.replace('-', ':').split(':')
                    if len(parts) == 2:  # MM:SS
                        status["minutes"] = int(parts[0])
                    elif len(parts) == 3:  # HH:MM:SS
                        status["minutes"] = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 4:  # D-HH:MM:SS
                        status["minutes"] = int(parts[0]) * 1440 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return status

# ═══════════════════════════════════════════════════════════════════════════════
# Format Functions
# ═══════════════════════════════════════════════════════════════════════════════

def collect_all() -> dict:
    """Collect all status data."""
    return {
        "timestamp": datetime.now().isoformat(),
        "hardware": get_hardware_status(),
        "cluster": get_cluster_status(),
        "memory": get_memory_status(),
        "nmf_blocks": get_nmf_block_status(),
        "runtime": get_agent_runtime_status(),
        "action_outcomes": get_action_outcomes(),
        "voice": get_voice_status(),
        "knowledge_gaps": get_knowledge_gaps(),
        "consolidation": get_consolidation_age(),
        "improvement": get_improvement_status(),
        "hive": get_hive_status(),
        "tpu": get_tpu_status(),
        "agi": get_agi_status(),
        "docker": get_docker_status(),
        "comm": get_comm_status(),
        "usage": get_usage_status(),
        "context": get_context_status(),
        "session": get_session_time(),
    }

def format_compact() -> str:
    """Format data for compact statusline display with NES 8-bit colors."""
    data = collect_all()
    parts = []

    # 0. Hardware status ⚙️ (System vitals) - only if critical
    hw = data.get("hardware", {})
    cpu = hw.get("cpu", {})
    mem = hw.get("memory", {})
    cpu_pct = cpu.get("percent", 0)
    mem_pct = mem.get("percent", 0)

    # Only show if above warning threshold
    if cpu_pct >= THRESHOLDS["cpu_warn"]:
        cpu_color = NES_RED if cpu_pct >= THRESHOLDS["cpu_crit"] else NES_YELLOW
        parts.append(f"{cpu_color}⚙️{cpu_pct}%{RESET}")
    if mem_pct >= THRESHOLDS["mem_warn"]:
        mem_color = NES_RED if mem_pct >= THRESHOLDS["mem_crit"] else NES_YELLOW
        parts.append(f"{mem_color}🧩{mem_pct}%{RESET}")

    # 1. Session time ⏱️ (Game clock)
    session = data.get("session", {})
    session_time = session.get("time_str", "")
    if session_time:
        parts.append(f"{NES_CYAN}⏱️{session_time}{RESET}")

    # 1b. Context window usage 📜 (Scroll/buffer)
    context = data.get("context", {})
    ctx_pct = context.get("percent", 0)
    if ctx_pct > 0 or not context.get("stale", True):
        # Color based on usage (green=low, yellow=medium, red=high)
        if ctx_pct >= 70:
            ctx_color = NES_RED
        elif ctx_pct >= 50:
            ctx_color = NES_YELLOW
        else:
            ctx_color = NES_GREEN
        # Add ~ if estimated, dim if stale
        est = "~" if context.get("estimated", True) else ""
        if context.get("stale", False):
            ctx_color = GRAY
        parts.append(f"{ctx_color}📜{est}{ctx_pct}%{RESET}")

    # 2. Cluster status 🌐 (Network of nodes)
    cluster = data.get("cluster", {})
    online = sum(1 for n in cluster.values() if n.get("online"))
    total = len(cluster) or 5
    cluster_color = NES_GREEN if online == total else (NES_YELLOW if online >= 3 else NES_RED)
    parts.append(f"{cluster_color}🌐{online}/{total}{RESET}")

    # 3. Action success rate with trend (Score display)
    action = data.get("action_outcomes", {})
    if action.get("total", 0) > 0:
        rate = action.get("rate", 0)
        trend = action.get("trend", "→")
        action_color = NES_GREEN if rate >= 80 else (NES_YELLOW if rate >= 60 else NES_RED)
        parts.append(f"{action_color}📊{rate}%{trend}{RESET}")

    # 4. Memory system 🧠 (Brain power-up)
    memory = data.get("memory", {})
    entities = memory.get("entities", 0)
    cons = memory.get("consolidation", {})
    cons_total = cons.get("total", 0)
    if entities > 0 or cons_total > 0:
        icon = "🔄" if memory.get("recent_activity") else "💤"
        parts.append(f"{NES_CYAN}🧠{icon}{entities}·{cons_total}c{RESET}")

    # 4b. NMF Identity Blocks 🆔 (Letta-style persona blocks)
    nmf = data.get("nmf_blocks", {})
    total_blocks = nmf.get("total_blocks", 0)
    agent_count = len(nmf.get("agents", []))
    if total_blocks > 0:
        parts.append(f"{NES_MAGENTA}🆔{total_blocks}·{agent_count}a{RESET}")

    # 5. Goals & Tasks 🎯 (Quest log)
    rt = data.get("runtime", {})
    goals = rt.get("active_goals", 0)
    tasks = rt.get("pending_tasks", 0) + rt.get("in_progress_tasks", 0)
    blocked = rt.get("blocked_tasks", 0)
    if goals > 0 or tasks > 0:
        goal_str = f"{NES_CYAN}🎯{goals}g·{tasks}t"
        if blocked > 0:
            goal_str += f"·{NES_RED}{blocked}⏸{NES_CYAN}"
        parts.append(f"{goal_str}{RESET}")

    # 6. Voice status 🎤/🔇 (Sound effects)
    voice = data.get("voice", {})
    if voice.get("listening"):
        parts.append(f"{NES_GREEN}🎤{RESET}")
    else:
        parts.append(f"{GRAY}🔇{RESET}")

    # 7. Knowledge gaps 🕳️ (Danger pits)
    gaps = data.get("knowledge_gaps", {})
    gap_count = gaps.get("gaps", 0)
    if gap_count > 0:
        gap_color = NES_RED if gaps.get("critical", 0) > 0 else NES_YELLOW
        parts.append(f"{gap_color}🕳️{gap_count}{RESET}")

    # 8. Consolidation age 🌙 (Night/day cycle)
    cons_age = data.get("consolidation", {})
    time_str = cons_age.get("time_str", "")
    if time_str:
        age_min = cons_age.get("age_minutes", 9999)
        cons_color = NES_GREEN if age_min < 360 else (NES_YELLOW if age_min < 1440 else NES_RED)
        parts.append(f"{cons_color}🌙{time_str}{RESET}")

    # 9. Improvement queue 🔄 (Power-ups in queue)
    improvement = data.get("improvement", {})
    imp_total = improvement.get("queued", 0) + improvement.get("in_progress", 0)
    if imp_total > 0:
        imp_color = NES_GREEN if improvement.get("in_progress", 0) > 0 else NES_MAGENTA
        parts.append(f"{imp_color}🔄{imp_total}{RESET}")

    # 10. Hive mind / Swarm 🐝 (Co-op mode)
    hive = data.get("hive", {})
    if hive.get("active") and hive.get("agents", 0) > 0:
        parts.append(f"{NES_YELLOW}🐝{hive['agents']}{RESET}")

    # 11. TPU status 🐠 (Special hardware boost)
    tpu = data.get("tpu", {})
    if tpu.get("available"):
        inferences = tpu.get("inferences", 0)
        if inferences > 0:
            parts.append(f"{NES_GREEN}🐠{inferences}{RESET}")
        else:
            parts.append(f"{NES_GREEN}🐠✓{RESET}")

    # 12. AGI awakenings 👁️ (Game progress)
    agi = data.get("agi", {})
    awakenings = agi.get("awakenings", 0)
    if awakenings > 0:
        successful = agi.get("successful_sessions", 0)
        success_rate = int((successful / awakenings) * 100) if awakenings > 0 else 0
        parts.append(f"{NES_MAGENTA}👁{awakenings}·{success_rate}%{RESET}")

    # 13. Node communication 📡 (Wireless link)
    comm = data.get("comm", {})
    unread = comm.get("unread", 0)
    pending = comm.get("pending_actions", 0)
    if unread > 0 or pending > 0:
        parts.append(f"{NES_BLUE}📡{unread}m·{pending}a{RESET}")
    elif comm.get("connected"):
        parts.append(f"{NES_GREEN}📡✓{RESET}")

    # 14. Docker containers 🐳 (Active services)
    docker = data.get("docker", {})
    running = docker.get("running", 0)
    if running > 0:
        parts.append(f"{NES_BLUE}🐳{running}{RESET}")

    # 15. Session usage 📈 (Current session consumption)
    usage = data.get("usage", {})
    session_pct = int(usage.get("session_pct", 0))
    if session_pct > 0:
        session_color = NES_GREEN if session_pct < 50 else (NES_YELLOW if session_pct < 80 else NES_RED)
        parts.append(f"{session_color}📈{session_pct}%{RESET}")

    # 16. Weekly allowance LEFT 💳 (Credits remaining)
    weekly_left = int(usage.get("weekly_left", 100))
    # Color based on how much is LEFT (green=plenty, red=low)
    usage_color = NES_GREEN if weekly_left > 50 else (NES_YELLOW if weekly_left > 20 else NES_RED)
    parts.append(f"{usage_color}💳{weekly_left}%{RESET}")

    return " ".join(parts)

def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "compact":
            print(format_compact())
        elif mode == "json":
            print(json.dumps(collect_all(), indent=2, default=str))
        else:
            print(json.dumps(collect_all(), default=str))
    else:
        print(json.dumps(collect_all(), indent=2, default=str))

if __name__ == "__main__":
    main()
