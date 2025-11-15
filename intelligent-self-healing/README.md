# Intelligent Self-Healing System

**AI-powered configuration management using Claude Agent SDK**

This replaces dumb bash scripts with intelligent agents that can reason about configuration changes and make smart decisions.

## Architecture

### Old System (Dumb)
```
statusline-watchdog.sh
  ├─ Simple pattern matching
  ├─ Blindly restores expected values
  ├─ No reasoning about intent
  └─ Can't learn from past decisions
```

### New System (Intelligent)
```
Intelligent Config Agent (Claude SDK)
  ├─ AI-powered reasoning about changes
  ├─ Understands user intent vs system errors
  ├─ Asks for clarification when uncertain
  ├─ Learns from past decisions
  └─ Provides explanations for actions
```

## Components

### 1. `intelligent_config_agent.py`
Core AI agent using Claude API for intelligent decision-making.

**Key Features:**
- Analyzes configuration changes using Claude Sonnet 4
- Determines if changes are intentional or errors
- Provides confidence scores and reasoning
- Logs decisions for future learning
- Takes snapshots before making changes
- Falls back to rule-based system if AI unavailable

**Usage:**
```python
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()

# Analyze a single change
analysis = agent.analyze_config_change(
    config_key="statusLine.command",
    old_value="/Users/marc/.claude/ember-statusline-utf8.sh",
    new_value="/Users/marc/.claude/agentic-statusline.sh",
    change_source="user_edit"
)

# Intelligently heal entire config file
results = agent.intelligent_heal_config(
    config_path=Path("~/.claude/settings.json").expanduser(),
    expected_values={
        "statusLine.command": "/Users/marc/.claude/agentic-statusline.sh"
    },
    change_source="watchdog"
)
```

**AI Analysis Response:**
```json
{
  "is_intentional": true,
  "confidence": 0.95,
  "reasoning": "Change from ember-statusline to agentic-statusline appears intentional. The naming convention suggests a purposeful switch from pet status to system status display.",
  "recommendation": "keep_new",
  "red_flags": [],
  "context": "statusline_replacement"
}
```

### 2. `intelligent_statusline_watchdog.py`
Intelligent watchdog specifically for statusline configuration.

**Features:**
- Uses AI agent to analyze statusline changes
- Only restores when AI is confident it's an error
- Leaves intentional changes alone
- Asks user for confirmation when uncertain
- Works from session-start hook

**Usage:**
```bash
# Run watchdog (uses AI)
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Force rule-based fallback
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py --force-rule-based
```

**Example Output:**
```
============================================================
🤖 Intelligent StatusLine Watchdog (AI-Powered)
============================================================

🤖 Analyzing statusline change in settings.json...

📊 Analysis:
  Is Intentional: False
  Confidence: 85.0%
  Reasoning: StatusLine appears to have been reset to old value by automatic script. User explicitly switched to agentic-statusline.sh earlier today.
  Recommendation: restore_old

🔧 Restoring agentic statusline (confidence: 85.0%)
✅ Agentic statusline restored
   Snapshot: /Users/marc/.claude/config_snapshots/settings_before_watchdog_restore_20251104_103000.json

============================================================
📊 Watchdog Summary
============================================================
Configs checked: 2
Configs healed: 1
Confirmations needed: 0

✅ Watchdog complete
```

## Decision Memory

All AI decisions are logged to enable learning:

**Location:** `~/.claude/intelligent_healing_decisions.jsonl`

**Format:**
```json
{
  "timestamp": "2025-11-04T10:30:00",
  "config_key": "statusLine.command",
  "old_value": "/Users/marc/.claude/ember-statusline-utf8.sh",
  "new_value": "/Users/marc/.claude/agentic-statusline.sh",
  "change_source": "user_edit",
  "analysis": {
    "is_intentional": true,
    "confidence": 0.95,
    "reasoning": "...",
    "recommendation": "keep_new"
  },
  "action_taken": "kept_new"
}
```

The agent uses this log to make better decisions over time by referencing similar past changes.

## Configuration Snapshots

Before making any changes, the agent takes snapshots:

**Location:** `~/.claude/config_snapshots/`

**Format:** `{filename}_{label}_{timestamp}.json`

**Example:**
```
settings_before_watchdog_restore_20251104_103000.json
settings_after_watchdog_restore_20251104_103005.json
settings_manual_20251104_120000.json
```

This allows rollback if AI makes a wrong decision.

## Integration with Session Start

Update `~/.claude/hooks/session-start.sh` to use intelligent watchdog:

```bash
# Old (dumb bash script):
# bash ~/.claude/statusline-watchdog.sh >> "$LOG_FILE" 2>&1

# New (intelligent AI agent):
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py >> "$LOG_FILE" 2>&1
```

## AI Decision Process

1. **Detect Change**: Watchdog detects statusline doesn't match expected value

2. **Context Gathering**:
   - Get diff of old vs new value
   - Check change source (script, user edit, system corruption)
   - Retrieve similar past decisions from memory

3. **AI Analysis**:
   - Send detailed prompt to Claude Sonnet 4
   - Get analysis with confidence score
   - Parse JSON response with recommendation

4. **Decision**:
   - **High confidence (>80%) + restore**: Make the change
   - **High confidence (>80%) + keep**: Leave as-is
   - **Low confidence (<60%)**: Ask user for confirmation
   - **Parse error / API failure**: Fall back to rule-based

5. **Action**:
   - Take snapshot before change
   - Apply change if appropriate
   - Log decision for learning
   - Report results

## Fallback Strategy

If AI unavailable:
1. Falls back to rule-based `SmartConfigPreserver`
2. If that fails, uses ultra-safe "preserve existing" default
3. Logs warning about fallback mode

## Extending to Other Configs

The intelligent agent is generic and can be used for any configuration:

```python
# Heal MCP server configs
agent.intelligent_heal_config(
    config_path=Path("~/.claude.json").expanduser(),
    expected_values={
        "mcpServers.enhanced-memory.command": "python",
        "mcpServers.enhanced-memory.args.0": "/path/to/server.py"
    },
    change_source="mcp_healing"
)

# Heal hook configs
agent.intelligent_heal_config(
    config_path=Path("~/.claude/settings.json").expanduser(),
    expected_values={
        "hooks.PreToolUse.0.hooks.0.command": "/Users/marc/.claude/hooks/pre_tool_use.py"
    },
    change_source="hook_healing"
)
```

## Future Enhancements

1. **Integration with Enhanced Memory MCP**
   - Store decisions in enhanced-memory instead of JSONL
   - Query memory for similar past situations
   - Build knowledge graph of configuration relationships

2. **Voice Integration**
   - Use voice-mode MCP to ask user for confirmation
   - Speak decision reasoning
   - Get verbal approval for uncertain changes

3. **Pattern Learning**
   - Detect patterns in user vs system changes
   - Learn user preferences over time
   - Adjust confidence thresholds based on accuracy

4. **Proactive Monitoring**
   - Run continuously as daemon
   - Detect changes in real-time
   - Alert immediately on suspicious changes

5. **Multi-Agent Collaboration**
   - Spawn specialist agents for different config types
   - Coordinate healing across multiple systems
   - Share learnings between agents

## Performance

- **AI analysis latency**: ~500-1000ms per decision
- **Fallback latency**: ~10ms rule-based
- **Memory usage**: ~50MB agent + ~20MB Claude SDK
- **Cost**: ~$0.01 per 10 decisions (Sonnet 4 pricing)

## Testing

```bash
# Test AI analysis
cd /Volumes/SSDRAID0/agentic-system/intelligent-self-healing
python3 intelligent_config_agent.py analyze \
  --key "statusLine.command" \
  --old "/Users/marc/.claude/ember-statusline-utf8.sh" \
  --new "/Users/marc/.claude/agentic-statusline.sh"

# Test watchdog
python3 intelligent_statusline_watchdog.py

# Test with forced rule-based fallback
python3 intelligent_statusline_watchdog.py --force-rule-based

# Take manual snapshot
python3 intelligent_config_agent.py snapshot \
  --config ~/.claude/settings.json
```

## Monitoring

Check decision log to see what AI is deciding:

```bash
# Recent decisions
tail -f ~/.claude/intelligent_healing_decisions.jsonl | jq .

# Decisions for specific key
grep "statusLine" ~/.claude/intelligent_healing_decisions.jsonl | jq .

# High-confidence decisions
jq 'select(.analysis.confidence > 0.8)' ~/.claude/intelligent_healing_decisions.jsonl

# User confirmations needed
jq 'select(.analysis.recommendation == "ask_user")' ~/.claude/intelligent_healing_decisions.jsonl
```

## Troubleshooting

**AI agent fails to initialize:**
```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# Set if missing
export ANTHROPIC_API_KEY="your_key_here"
```

**Watchdog not running:**
```bash
# Check session-start hook
cat ~/.claude/hooks/session-start.sh | grep -A2 "StatusLine"

# Run manually to test
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

**AI making wrong decisions:**
```bash
# Review recent decisions
tail -20 ~/.claude/intelligent_healing_decisions.jsonl | jq .

# Check confidence scores
jq '.analysis.confidence' ~/.claude/intelligent_healing_decisions.jsonl | sort -n

# If consistently wrong, may need to adjust prompts in intelligent_config_agent.py
```

**Need to rollback:**
```bash
# List snapshots
ls -lht ~/.claude/config_snapshots/ | head -20

# Restore from snapshot
cp ~/.claude/config_snapshots/settings_before_watchdog_restore_20251104_103000.json \
   ~/.claude/settings.json
```

## Migration from Old System

1. **Backup current configs:**
   ```bash
   cp ~/.claude/settings.json ~/.claude/settings.json.backup
   cp ~/.claude/settings.local.json ~/.claude/settings.local.json.backup
   ```

2. **Install intelligent agent:**
   Already done - files in `/Volumes/SSDRAID0/agentic-system/intelligent-self-healing/`

3. **Update session-start hook:**
   Replace bash watchdog with Python intelligent watchdog (see Integration section)

4. **Test first run:**
   ```bash
   python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
   ```

5. **Monitor for a few days:**
   Check decision log to ensure AI is making good decisions

6. **Extend to other configs:**
   Once confident, apply to hooks, MCP servers, etc.

## Philosophy

**"Intelligent, not automatic"**

The old system blindly restored configurations. The new system:
- Reasons about changes
- Understands context and intent
- Asks when uncertain
- Learns from experience
- Explains its decisions

This aligns with the agentic system's core principle: **agents should augment human intelligence, not replace it**.
