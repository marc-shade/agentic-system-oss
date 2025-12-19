# Situational Awareness Hook System

## Overview

The Situational Awareness Hook provides comprehensive context and bearings when starting a Claude Code session. It gathers real-time information about the system, project, and environment to give Claude immediate awareness of the current state.

## Features

### 🔍 Real-Time Analysis
- **Timestamp Context**: Current time, day, period (morning/afternoon/evening/night)
- **Git Repository Status**: Branch, recent commits, modified files, unpushed changes
- **Process Monitoring**: Active Claude and MCP processes with resource usage
- **System Resources**: Memory, CPU, and disk usage statistics
- **Recent Activity**: Files modified in the last 24 hours
- **Project Structure**: Directory contents categorized by type
- **Environment Info**: Python version, Node version, Git version, paths
- **Error Detection**: Recent errors from log files

### 🎙️ Voice Integration
- Automatic voice announcements of key status information
- Context-aware greetings based on time of day
- Professional emotion tone with configurable volume
- Non-blocking voice synthesis

### 💾 Context Caching
- Stores situational data in `/Users/marc/.claude/.situational_cache.json`
- Other hooks can access cached context for decision-making
- Real-time data sharing across hook ecosystem

### ⚡ Performance Optimized
- Executes in under 3 seconds
- Non-blocking operation
- Intelligent timeout handling
- Memory-efficient data gathering

## Architecture

### Core Components

#### 1. Main Hook (`situational_awareness_hook.py`)
```python
class SituationalAwareness:
    - get_timestamp_context()     # Time and date analysis
    - get_git_status()           # Git repository inspection  
    - get_active_processes()     # Process monitoring
    - get_system_resources()     # Resource usage analysis
    - get_recent_file_activity() # File modification tracking
    - get_project_structure()    # Directory analysis
    - get_environment_info()     # Environment inspection
    - check_error_logs()         # Error detection
    - synthesize_voice_summary() # Voice announcements
    - save_context_cache()       # Context persistence
```

#### 2. Configuration Integration
- Integrated into `master_hooks_config.json`
- Configured as SessionStart hook with priority 1
- 5-second timeout with non-blocking execution

#### 3. Data Flow
```
Session Start → Hook Execution → Data Gathering → Voice Synthesis → Cache Storage → Summary Display
```

## Installation

### Automatic Deployment
```bash
python3 /Users/marc/.claude/hooks/deploy_situational_awareness.py
```

### Manual Installation
1. Copy `situational_awareness_hook.py` to `/Users/marc/.claude/hooks/session-start/`
2. Update `master_hooks_config.json` with SessionStart configuration
3. Deploy configuration to Claude Code
4. Test execution

## Configuration Files

### Hook Configuration (`master_hooks_config.json`)
```json
"SessionStart": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "python3 /Users/marc/.claude/hooks/session-start/situational_awareness_hook.py",
        "timeout": 5000,
        "background": false,
        "description": "Comprehensive situational awareness gathering",
        "priority": 1,
        "can_block": false
      }
    ]
  }
]
```

### Cache Structure
```json
{
  "gathering_time": "timestamp",
  "timestamp": {
    "formatted": "2025-08-17 14:35:35",
    "time_period": "afternoon",
    "day": "Sunday",
    "is_weekend": true,
    "timezone": "EDT"
  },
  "git": {
    "is_repo": true,
    "current_branch": "main",
    "recent_commits": ["commit1", "commit2"],
    "modified_files": [{"status": "M", "file": "example.py"}],
    "unpushed_commits": 2
  },
  "processes": {
    "claude_processes": [...],
    "mcp_processes": [...],
    "total_claude_memory": 150.5,
    "total_mcp_memory": 892.3
  },
  "resources": {
    "memory": {"total_gb": 32.0, "available_gb": 8.4, "used_percent": 73.9},
    "cpu": {"usage_percent": 15.2, "core_count": 8},
    "disk": {"total_gb": 1000.0, "free_gb": 250.0, "used_percent": 75.0}
  },
  "recent_files": [...],
  "project_structure": {...},
  "environment": {...},
  "error_logs": [...]
}
```

## Sample Output

### Console Display
```
🔍 SITUATIONAL AWARENESS
📅 2025-08-17 14:35:35 (afternoon)
🌿 Branch: main
📝 4 modified files
⬆️ 2 unpushed commits
💾 Memory: 73.9% used (8.4GB available)
⚙️ Processes: 9 Claude, 92 MCP
📁 20 files modified in last 24h
⚠️ 2 recent errors in logs
⏱️ Analysis completed in 0.91s
```

### Voice Announcement
> "Good afternoon, Marc! You have 4 modified files and 2 unpushed commits. 92 MCP servers are running."

## Integration with Other Hooks

### Accessing Cached Data
```python
import json

# Load situational cache
with open("/Users/marc/.claude/.situational_cache.json", 'r') as f:
    context = json.load(f)

# Example: Check if high memory usage
memory_usage = context["resources"]["memory"]["used_percent"]
if memory_usage > 80:
    # Take action for high memory usage
    pass

# Example: Check git status for delegation decisions
has_uncommitted_changes = len(context["git"]["modified_files"]) > 0
if has_uncommitted_changes:
    # Suggest committing changes before major operations
    pass
```

### Hook Dependencies
- **Voice System**: Uses Siobhan voice for announcements
- **Memory System**: Can integrate with enhanced memory hooks
- **Security Hooks**: Provides context for security decisions
- **Performance Hooks**: Shares resource usage data

## Logging

### Log File Location
`/Users/marc/.claude/logs/situational_awareness.log`

### Log Entries
```
[2025-08-17T14:35:35] Starting situational awareness gathering
[2025-08-17T14:35:35] Context gathered - Git repo: True, MCP processes: 92, Memory usage: 73.9%
[2025-08-17T14:35:35] Voice synthesis error: Connection refused
```

## Testing

### Test Suite
```bash
python3 /Users/marc/.claude/hooks/test_situational_awareness.py
```

### Test Coverage
- ✅ Hook execution verification
- ✅ Cache data validation
- ✅ Other hook access testing
- ✅ Performance timing validation
- ✅ Error handling verification

## Performance Metrics

### Execution Times
- **Git Analysis**: ~0.2s
- **Process Monitoring**: ~0.3s
- **Resource Analysis**: ~0.1s
- **File Activity**: ~0.8s
- **Voice Synthesis**: ~0.5s
- **Total Execution**: <3.0s

### Resource Usage
- **Memory**: ~10MB during execution
- **CPU**: Minimal impact (<5% spike)
- **Disk I/O**: Read-only operations
- **Network**: None required

## Troubleshooting

### Common Issues

#### Hook Not Executing
1. Check file permissions: `chmod +x situational_awareness_hook.py`
2. Verify Python path: `which python3`
3. Check Claude configuration syntax
4. Review hook logs for errors

#### Voice Synthesis Failing
1. Verify Siobhan voice system availability
2. Check voice server connection
3. Test manual voice synthesis
4. Review audio system permissions

#### Cache File Missing
1. Check log directory permissions
2. Verify disk space availability
3. Review execution logs for errors
4. Test manual hook execution

#### Slow Performance
1. Check system resource usage
2. Reduce file scanning depth
3. Optimize git repository size
4. Review timeout settings

### Debug Commands
```bash
# Test hook execution
python3 /Users/marc/.claude/hooks/session-start/situational_awareness_hook.py

# Check cache contents
cat /Users/marc/.claude/.situational_cache.json | jq .

# Review logs
tail -f /Users/marc/.claude/logs/situational_awareness.log

# Test voice system
python3 -c "
import sys
sys.path.append('/Users/marc/.claude')
from siobhan_voice import siobhan
siobhan.speak('Test message', emotion='professional', volume=0.4)
"
```

## Future Enhancements

### Planned Features
- **Project Type Detection**: Automatic identification of project types (React, Python, etc.)
- **Dependency Analysis**: Package.json, requirements.txt analysis
- **Security Scanning**: Basic vulnerability detection
- **Performance Trending**: Historical resource usage tracking
- **Smart Notifications**: Contextual alerts and suggestions
- **Integration Recommendations**: Suggest relevant MCP servers based on context

### Extensibility
The hook system is designed for easy extension. New analysis modules can be added by:

1. Creating new analysis functions in the `SituationalAwareness` class
2. Adding data to the context dictionary
3. Updating cache structure documentation
4. Testing integration with existing hooks

## Documentation

### Files
- `situational_awareness_hook.py` - Main hook implementation
- `test_situational_awareness.py` - Test suite
- `deploy_situational_awareness.py` - Deployment script
- `SITUATIONAL_AWARENESS_DOCUMENTATION.md` - This documentation

### Configuration
- `master_hooks_config.json` - Hook system configuration
- `~/.config/claude-desktop/config.json` - Claude integration

### Cache and Logs
- `.situational_cache.json` - Context cache file
- `logs/situational_awareness.log` - Execution logs

---

**The Situational Awareness Hook provides Claude Code with immediate environmental context, enabling more informed decisions and better user experience from the moment a session begins.**