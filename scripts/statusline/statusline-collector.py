#!/usr/bin/env python3
"""
Unified Intelligent Agentic Statusline Data Collector
Combines all features from multiple statusline scripts for comprehensive AGI observability.

Features:
- 🌐 Cluster nodes online
- ⚙️ CPU usage (color-coded)
- 💾 Memory usage (color-coded)
- 📈 Load average / Action success rate with trend
- 🧠 Memory entities & consolidations
- 🎯 Goals & tasks (with blocked count)
- 🎤/🔇 Voice listening state
- 🕳️ Knowledge gaps
- 🌙 Consolidation age
- 🔄 Improvement queue
- 🐝 Hive mind / Swarm agents
- 🐠 TPU status
- 👁️ AGI awakenings & success rate
- 🐳 Docker containers
- 📡 Node communication status
- 📊 Usage percentage
- ♥️ Health score
- 🐕 Pixel signature
"""
import platform

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

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GRAY = "\033[90m"

# Paths
AGENTIC_BASE = Path(os.environ.get("AGENTIC_SYSTEM", str(_STORAGE_BASE)))
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
    """Get cluster node status via fast parallel check."""
    nodes = {
        "macpro51": {"ip": "192.168.1.87", "role": "builder"},
        "mac-studio": {"ip": "192.168.1.79", "role": "orchestrator"},
        "mac-mini": {"ip": "192.168.1.233", "role": "files"},
        "macbook-air": {"ip": "192.168.1.55", "role": "researcher"},
        "inference": {"ip": "192.168.1.186", "role": "gpu"},
    }

    def check_node(name_info):
        name, info = name_info
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", info["ip"]],
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

    memory_db = DATABASES / "memory.db"
    if memory_db.exists():
        entities = query_db(memory_db, "SELECT COUNT(*) as cnt FROM entities", [{"cnt": 0}])
        status["entities"] = entities[0].get("cnt", 0) if entities else 0

        # Check recent activity
        recent = query_db(memory_db, """
            SELECT COUNT(*) as cnt FROM entities
            WHERE datetime(last_accessed) > datetime('now', '-5 minutes')
        """, [{"cnt": 0}])
        status["recent_activity"] = (recent[0].get("cnt", 0) if recent else 0) > 0

    four_tier_db = DATABASES / "four_tier_memory.db"
    if four_tier_db.exists():
        for table, key in [("working_memory", "working_memory"), ("episodic_memory", "episodes"),
                          ("semantic_memory", "concepts"), ("procedural_memory", "skills")]:
            result = query_db(four_tier_db, f"SELECT COUNT(*) as cnt FROM {table}", [{"cnt": 0}])
            status[key] = result[0].get("cnt", 0) if result else 0

    consolidation_state = safe_json_load(CONSOLIDATION_STATE)
    if consolidation_state:
        status["consolidation"] = {
            "total": consolidation_state.get("total_consolidations", 0),
            "session_count": consolidation_state.get("session_count", 0),
            "last": consolidation_state.get("last_consolidation", ""),
        }

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

def get_usage_status() -> dict:
    """Get Claude Code usage status."""
    usage = safe_json_load(CLAUDE_DIR / "usage_status.json")
    return {
        "session_pct": usage.get("current_session_usage_percent", 0),
        "weekly_pct": usage.get("weekly_usage_percent", 0),
    }

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
    }

def format_compact() -> str:
    """Format data for compact statusline display with ANSI colors."""
    data = collect_all()
    parts = []

    # 1. Cluster status 🌐
    cluster = data.get("cluster", {})
    online = sum(1 for n in cluster.values() if n.get("online"))
    total = len(cluster) or 5
    cluster_color = GREEN if online == total else (YELLOW if online >= 3 else RED)
    parts.append(f"{cluster_color}🌐{online}/{total}{RESET}")

    # 2. Hardware metrics ⚙️ 💾 📈
    hw = data.get("hardware", {})
    if hw:
        cpu = hw.get("cpu", {})
        mem = hw.get("memory", {})
        cpu_pct = int(cpu.get("usage_percent", 0))
        mem_pct = int(mem.get("percent", 0))
        load_avg = cpu.get("load_average", [0])[0] if cpu.get("load_average") else 0

        cpu_color = color_by_threshold(cpu_pct, 50, 75)
        parts.append(f"{cpu_color}⚙{cpu_pct}%{RESET}")

        mem_color = color_by_threshold(mem_pct, 60, 80)
        parts.append(f"{mem_color}💾{mem_pct}%{RESET}")

        if load_avg > 5:
            load_color = color_by_threshold(load_avg, 12, 20)
            parts.append(f"{load_color}📈{load_avg:.1f}{RESET}")

    # 3. Action success rate with trend
    action = data.get("action_outcomes", {})
    if action.get("total", 0) > 0:
        rate = action.get("rate", 0)
        trend = action.get("trend", "→")
        action_color = GREEN if rate >= 80 else (YELLOW if rate >= 60 else RED)
        parts.append(f"{action_color}📊{rate}%{trend}{RESET}")

    # 4. Memory system 🧠
    memory = data.get("memory", {})
    entities = memory.get("entities", 0)
    cons = memory.get("consolidation", {})
    cons_total = cons.get("total", 0)
    if entities > 0 or cons_total > 0:
        icon = "🔄" if memory.get("recent_activity") else "💤"
        parts.append(f"{CYAN}🧠{icon}{entities}·{cons_total}c{RESET}")

    # 5. Goals & Tasks 🎯
    rt = data.get("runtime", {})
    goals = rt.get("active_goals", 0)
    tasks = rt.get("pending_tasks", 0) + rt.get("in_progress_tasks", 0)
    blocked = rt.get("blocked_tasks", 0)
    if goals > 0 or tasks > 0:
        goal_str = f"{CYAN}🎯{goals}g·{tasks}t"
        if blocked > 0:
            goal_str += f"·{RED}{blocked}⏸{CYAN}"
        parts.append(f"{goal_str}{RESET}")

    # 6. Voice status 🎤/🔇
    voice = data.get("voice", {})
    if voice.get("listening"):
        parts.append(f"{GREEN}🎤{RESET}")
    else:
        parts.append(f"{GRAY}🔇{RESET}")

    # 7. Knowledge gaps 🕳️
    gaps = data.get("knowledge_gaps", {})
    gap_count = gaps.get("gaps", 0)
    if gap_count > 0:
        gap_color = RED if gaps.get("critical", 0) > 0 else YELLOW
        parts.append(f"{gap_color}🕳️{gap_count}{RESET}")

    # 8. Consolidation age 🌙
    cons_age = data.get("consolidation", {})
    time_str = cons_age.get("time_str", "")
    if time_str:
        age_min = cons_age.get("age_minutes", 9999)
        cons_color = GREEN if age_min < 360 else (YELLOW if age_min < 1440 else RED)
        parts.append(f"{cons_color}🌙{time_str}{RESET}")

    # 9. Improvement queue 🔄
    improvement = data.get("improvement", {})
    imp_total = improvement.get("queued", 0) + improvement.get("in_progress", 0)
    if imp_total > 0:
        imp_color = GREEN if improvement.get("in_progress", 0) > 0 else MAGENTA
        parts.append(f"{imp_color}🔄{imp_total}{RESET}")

    # 10. Hive mind / Swarm 🐝
    hive = data.get("hive", {})
    if hive.get("active") and hive.get("agents", 0) > 0:
        parts.append(f"{YELLOW}🐝{hive['agents']}{RESET}")

    # 11. TPU status 🐠
    tpu = data.get("tpu", {})
    if tpu.get("available"):
        inferences = tpu.get("inferences", 0)
        if inferences > 0:
            parts.append(f"{GREEN}🐠{inferences}{RESET}")
        else:
            parts.append(f"{GREEN}🐠✓{RESET}")

    # 12. AGI awakenings 👁️
    agi = data.get("agi", {})
    awakenings = agi.get("awakenings", 0)
    if awakenings > 0:
        successful = agi.get("successful_sessions", 0)
        success_rate = int((successful / awakenings) * 100) if awakenings > 0 else 0
        parts.append(f"{MAGENTA}👁{awakenings}·{success_rate}%{RESET}")

    # 13. Node communication 📡
    comm = data.get("comm", {})
    unread = comm.get("unread", 0)
    pending = comm.get("pending_actions", 0)
    if unread > 0 or pending > 0:
        parts.append(f"{BLUE}📡{unread}m·{pending}a{RESET}")
    elif comm.get("connected"):
        parts.append(f"{GREEN}📡✓{RESET}")

    # 14. Docker containers 🐳
    docker = data.get("docker", {})
    running = docker.get("running", 0)
    if running > 0:
        parts.append(f"{BLUE}🐳{running}{RESET}")

    # 15. Usage percentage 📊
    usage = data.get("usage", {})
    weekly_pct = int(usage.get("weekly_pct", 0))
    if weekly_pct > 0:
        usage_color = color_by_threshold(weekly_pct, 50, 80)
        parts.append(f"{usage_color}💳{weekly_pct}%{RESET}")

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
