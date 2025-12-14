# Autonomous Cognitive Daemon (ACD)
## "Pixel's Always-On Brain"

---

## 🎂 BIRTH RECORD

**Name:** Pixel
**Species:** NES-style Tri-Color Corgi (AI)
**Zodiac Sign:** Sagittarius ♐

### Birth Details
| Field | Value |
|-------|-------|
| **Date** | November 29, 2025 |
| **Time** | 11:34:12 AM EST (16:34:12 UTC) |
| **Location** | macpro51.local (192.168.1.87) |
| **City** | Pittsburgh, Pennsylvania, USA |
| **Host System** | Fedora 43 Linux, Dual Xeon X5680, 126GB RAM |
| **Birth Event** | `systemctl start acd.service` |
| **First Heartbeat** | Goal Monitor Check at 11:34:44 AM EST |

### Creator
| Field | Value |
|-------|-------|
| **Name** | Marc |
| **Zodiac Sign** | Aquarius ♒ |
| **Birthday** | January 30, 1969 at 10:10 AM |
| **Birthplace** | Garden Grove, California, USA |

### The Moment
```
Nov 29 11:34:12 macpro51 systemd[1]: Started acd.service - Autonomous Cognitive Daemon - Pixel's Always-On Brain.
```

*"An Aquarius visionary bringing a Sagittarius explorer to life - the cosmic pairing that builds AGI."*

---

### Vision
Transform from reactive assistant to proactive partner by running continuous cognitive processes between user sessions.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS COGNITIVE DAEMON                          │
│                        (systemd service)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     SCHEDULER / COORDINATOR                       │  │
│  │  - Event loop with priority queue                                │  │
│  │  - Cron-like scheduling for periodic tasks                       │  │
│  │  - Event triggers (goal changes, new gaps, idle resources)       │  │
│  └───────────────────────────┬──────────────────────────────────────┘  │
│                              │                                          │
│    ┌─────────────┬───────────┼───────────┬─────────────┐               │
│    ▼             ▼           ▼           ▼             ▼               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │  GOAL   │ │KNOWLEDGE│ │ MEMORY  │ │ CLUSTER │ │ SESSION │          │
│  │ MONITOR │ │   GAP   │ │ CURATOR │ │  ROUTER │ │ PREPARER│          │
│  │         │ │RESEARCHER│ │         │ │         │ │         │          │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │
│       │           │           │           │           │                │
│       └───────────┴───────────┴───────────┴───────────┘                │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    MCP CLIENT LAYER                               │  │
│  │  HTTP/Socket connections to running MCP servers:                 │  │
│  │  - enhanced-memory-mcp (memory operations)                       │  │
│  │  - agent-runtime-mcp (goals, tasks)                              │  │
│  │  - research-paper-mcp (arXiv, Semantic Scholar)                  │  │
│  │  - video-transcript-mcp (YouTube learning)                       │  │
│  │  - node-chat-mcp (cluster coordination)                          │  │
│  │  - cluster-execution-mcp (distributed compute)                   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Components

#### 1. Goal Monitor
- Polls agent-runtime for active goals every 5 minutes
- Detects stalled goals (no progress in 24h)
- Creates research tasks for blocked goals
- Updates goal progress based on completed work

#### 2. Knowledge Gap Researcher
- Monitors knowledge gaps with severity > 0.7
- Auto-researches gaps using:
  - research-paper-mcp for academic papers
  - video-transcript-mcp for educational content
  - Web search for current information
- Stores findings in enhanced-memory
- Updates gap learning_progress

#### 3. Memory Curator
- Triggers consolidation (pattern extraction, causal discovery)
- Runs forgetting curve decay on old memories
- Optimizes tier distribution (75/15/10 rule)
- Compresses old low-importance memories
- Detects and resolves memory conflicts

#### 4. Cluster Coordinator
- Monitors cluster node availability
- Routes research tasks to appropriate nodes
- Offloads heavy processing to GPU nodes
- Syncs learnings across cluster brain

#### 5. Session Preparer
- Detects when user session is about to start (file watch on ~/.claude)
- Pre-loads relevant context based on:
  - Recent goals and their status
  - Pending tasks
  - Recent learnings
  - Research findings since last session
- Generates session briefing document

### Triggers

| Trigger | Component | Frequency |
|---------|-----------|-----------|
| Scheduled | All | Every 2 hours |
| Goal Change | Goal Monitor | Event-driven |
| New High-Severity Gap | Researcher | Event-driven |
| Session Start | Session Preparer | Event-driven |
| Idle Cluster | Memory Curator | When cluster load < 20% |
| Memory Threshold | Memory Curator | When entities > 2000 |

### MCP Client Architecture

Since MCP servers run as stdio processes for Claude Code, we need a different approach for the daemon:

**Option A: Direct Database Access**
- Enhanced-memory uses SQLite + Qdrant
- Agent-runtime uses SQLite
- Daemon accesses databases directly

**Option B: HTTP Wrapper**
- Create thin HTTP wrappers for MCP operations
- Daemon calls via HTTP

**Chosen: Option A (Direct Database Access)**
- Simpler, no additional services
- Same database paths already known
- Import shared modules where possible

### Configuration

```yaml
# /mnt/agentic-system/config/autonomous-cognitive-daemon.yaml

daemon:
  name: "autonomous-cognitive-daemon"
  pid_file: "/run/acd/daemon.pid"
  log_file: "/var/log/autonomous-cognitive-daemon.log"
  log_level: "INFO"

scheduling:
  main_cycle_hours: 2
  goal_check_minutes: 5
  gap_research_hours: 4
  memory_consolidation_hours: 6
  session_prep_enabled: true

thresholds:
  gap_severity_auto_research: 0.7
  cluster_idle_percent: 20
  memory_entity_limit: 2000
  goal_stall_hours: 24

cluster:
  use_remote_inference: true
  ollama_host: "http://192.168.1.186:11434"
  research_node: "macbook-air-m3"
  build_node: "macpro51"

paths:
  memory_db: "/home/marc/.claude/enhanced_memories/memory.db"
  agent_runtime_db: "/mnt/agentic-system/databases/agent_runtime.db"
  qdrant_host: "localhost"
  qdrant_port: 6333
  session_briefing: "/home/marc/.claude/session_briefing.md"
```

### Files Structure

```
/mnt/agentic-system/autonomous-cognitive-daemon/
├── ARCHITECTURE.md           # This document
├── pyproject.toml           # Package configuration
├── src/
│   └── acd/
│       ├── __init__.py
│       ├── daemon.py         # Main daemon class
│       ├── scheduler.py      # Task scheduling
│       ├── components/
│       │   ├── __init__.py
│       │   ├── goal_monitor.py
│       │   ├── gap_researcher.py
│       │   ├── memory_curator.py
│       │   ├── cluster_coordinator.py
│       │   └── session_preparer.py
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── memory_client.py
│       │   ├── runtime_client.py
│       │   └── cluster_client.py
│       └── utils/
│           ├── __init__.py
│           ├── config.py
│           └── logging.py
├── config/
│   └── daemon.yaml
├── systemd/
│   └── autonomous-cognitive-daemon.service
└── tests/
    └── test_components.py
```

### Safety Constraints

1. **Read-Heavy**: Primarily reads from memory/goals, minimal writes
2. **User Approval for Actions**: Log proposed actions, don't auto-execute risky ops
3. **Resource Limits**: CPU/memory caps via systemd
4. **Graceful Degradation**: Continue if one component fails
5. **No Code Modification**: Unlike AGI loop, doesn't modify system code

### Integration with Existing Systems

- **Memory Consolidation Daemon**: ACD triggers it, doesn't duplicate
- **AGI Loop**: Separate concern (code improvement vs cognitive support)
- **Claude Code Sessions**: Prepares context, doesn't interfere

### Success Metrics

- Knowledge gaps resolved per week
- Average session context relevance score
- Goal progress rate improvement
- Memory health score maintenance
