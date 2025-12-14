# MCP Health Check

Comprehensive health check for all MCP servers with diagnostics and recovery guidance.

## Usage

```bash
/mcp-health
```

## Implementation

```bash
echo "=== MCP SYSTEM HEALTH CHECK ==="
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

# Configuration Files
echo -e "\n=== Configuration Files ==="
[ -f ~/.claude.json ] && echo "✅ ~/.claude.json: $(wc -c < ~/.claude.json | xargs) bytes" || echo "❌ ~/.claude.json: Missing"
[ -f ~/.mcp.json ] && echo "✅ ~/.mcp.json: $(wc -c < ~/.mcp.json | xargs) bytes" || echo "❌ ~/.mcp.json: Missing"
[ -f ~/.claude/settings.json ] && echo "✅ settings.json: Present" || echo "⚠️  settings.json: Missing"

# MCP Server Configuration Count
echo -e "\n=== Server Configuration ==="
user_servers=$(cat ~/.claude.json 2>/dev/null | jq '.mcpServers | length' 2>/dev/null || echo "0")
project_servers=$(cat ~/.mcp.json 2>/dev/null | jq '.mcpServers | length' 2>/dev/null || echo "0")
total_servers=$((user_servers + project_servers))
echo "User-level servers: $user_servers"
echo "Project-level servers: $project_servers"
echo "Total configured: $total_servers"

# Process Health
echo -e "\n=== Process Health ==="
mcp_processes=$(ps aux | grep -E "enhanced-memory|voice-mode|arduino_surface|agent-runtime|sequential-thinking|chrome-devtools|safla" | grep -v grep | wc -l | tr -d ' ')
echo "Running MCP processes: $mcp_processes"

# Database Health
echo -e "\n=== Database Health ==="
if [ -d /Volumes/SSDRAID0/agentic-system/databases/mcp/ ]; then
    db_count=$(ls /Volumes/SSDRAID0/agentic-system/databases/mcp/*.db 2>/dev/null | wc -l | tr -d ' ')
    db_size=$(du -sh /Volumes/SSDRAID0/agentic-system/databases/mcp/ 2>/dev/null | cut -f1)
    echo "✅ Database directory accessible"
    echo "   Databases: $db_count"
    echo "   Total size: $db_size"

    # Check individual databases
    for db in /Volumes/SSDRAID0/agentic-system/databases/mcp/*.db; do
        if [ -f "$db" ]; then
            db_name=$(basename "$db")
            db_file_size=$(ls -lh "$db" | awk '{print $5}')
            echo "   - $db_name: $db_file_size"
        fi
    done
else
    echo "❌ Database directory not accessible"
fi

# State Directory Health
echo -e "\n=== State Directory Health ==="
if [ -d /Volumes/SSDRAID0/agentic-system/mcp-state/ ]; then
    state_size=$(du -sh /Volumes/SSDRAID0/agentic-system/mcp-state/ 2>/dev/null | cut -f1)
    state_dirs=$(ls -d /Volumes/SSDRAID0/agentic-system/mcp-state/*/ 2>/dev/null | wc -l | tr -d ' ')
    echo "✅ State directory accessible"
    echo "   Subdirectories: $state_dirs"
    echo "   Total size: $state_size"
else
    echo "⚠️  State directory not accessible"
fi

# Tier 0 Essential Servers
echo -e "\n=== Tier 0 (Essential) Health ==="
for server in "enhanced-memory" "voice-mode" "arduino-surface" "safla"; do
    if ps aux | grep "$server" | grep -v grep > /dev/null; then
        echo "✅ $server: Running"
    else
        echo "❌ $server: Not running"
    fi
done

# Tier 1 Cognitive Servers
echo -e "\n=== Tier 1 (Cognitive) Health ==="
if ps aux | grep "agent-runtime" | grep -v grep > /dev/null; then
    echo "✅ agent-runtime-mcp: Running"
else
    echo "❌ agent-runtime-mcp: Not running"
fi

# Tier 2 Reasoning Servers
echo -e "\n=== Tier 2 (Reasoning) Health ==="
if ps aux | grep "sequential-thinking" | grep -v grep > /dev/null; then
    echo "✅ sequential-thinking: Running"
else
    echo "❌ sequential-thinking: Not running"
fi

# Check for errors in recent logs (if accessible)
echo -e "\n=== Recent Errors ==="
if [ -d /Volumes/SSDRAID0/agentic-system/mcp-servers/ ]; then
    error_count=$(find /Volumes/SSDRAID0/agentic-system/mcp-servers/ -name "*.log" -exec grep -i error {} \; 2>/dev/null | wc -l | tr -d ' ')
    echo "Errors in logs (last scan): $error_count"
    if [ "$error_count" -gt 0 ]; then
        echo "⚠️  Errors detected - review logs"
    fi
else
    echo "Log directory not accessible"
fi

# Overall Health Summary
echo -e "\n=== OVERALL HEALTH SUMMARY ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

issues=0

# Check configuration
if [ ! -f ~/.claude.json ]; then
    echo "❌ Configuration issue: Missing ~/.claude.json"
    issues=$((issues + 1))
fi

# Check processes
if [ "$mcp_processes" -lt 3 ]; then
    echo "❌ Process issue: Low MCP process count ($mcp_processes)"
    issues=$((issues + 1))
fi

# Check databases
if [ ! -d /Volumes/SSDRAID0/agentic-system/databases/mcp/ ]; then
    echo "❌ Storage issue: Database directory not accessible"
    issues=$((issues + 1))
fi

# Final verdict
if [ "$issues" -eq 0 ]; then
    echo "✅ MCP SYSTEM IS HEALTHY"
    echo "All essential services operational"
else
    echo "⚠️  MCP SYSTEM HAS ISSUES"
    echo "Found $issues issue(s) requiring attention"
    echo ""
    echo "Recovery Actions:"
    echo "1. Restart Claude Code to reinitialize MCP servers"
    echo "2. Check ~/.claude.json configuration"
    echo "3. Verify SSDRAID0 drive is mounted"
    echo "4. Review MCP server logs for errors"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

## What This Shows

- Configuration file status and sizes
- Server configuration counts
- Process health for all tiers
- Database health and sizes
- State directory status
- Recent error detection
- Overall health verdict
- Recovery recommendations

## Output Format

```
=== MCP SYSTEM HEALTH CHECK ===
Timestamp: 2025-01-03 14:30:00

=== Configuration Files ===
✅ ~/.claude.json: 2154223 bytes
✅ ~/.mcp.json: 1234 bytes
✅ settings.json: Present

=== Server Configuration ===
User-level servers: 5
Project-level servers: 4
Total configured: 9

=== Process Health ===
Running MCP processes: 6

=== Database Health ===
✅ Database directory accessible
   Databases: 3
   Total size: 911M
   - enhanced_memories.db: 850M
   - agent_runtime.db: 50M
   - conversation_memories.db: 11M

=== Tier 0 (Essential) Health ===
✅ enhanced-memory: Running
✅ voice-mode: Running
✅ arduino-surface: Running
✅ safla: Running

=== Tier 1 (Cognitive) Health ===
✅ agent-runtime-mcp: Running

=== Tier 2 (Reasoning) Health ===
✅ sequential-thinking: Running

=== Recent Errors ===
Errors in logs (last scan): 0

=== OVERALL HEALTH SUMMARY ===
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ MCP SYSTEM IS HEALTHY
All essential services operational
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Recovery Actions

If health check fails:

1. **Configuration Issues**:
   ```bash
   # Verify configuration files
   cat ~/.claude.json | jq .
   cat ~/.mcp.json | jq .
   ```

2. **Process Issues**:
   ```bash
   # Restart Claude Code
   # This reinitializes all MCP servers
   ```

3. **Database Issues**:
   ```bash
   # Check drive mount
   ls /Volumes/SSDRAID0/agentic-system/databases/mcp/

   # Verify database integrity
   sqlite3 /Volumes/SSDRAID0/agentic-system/databases/mcp/enhanced_memories.db "PRAGMA integrity_check;"
   ```

4. **Storage Issues**:
   ```bash
   # Check disk space
   df -h /Volumes/SSDRAID0

   # Clean up if needed
   /Volumes/SSDRAID0/agentic-system/cleanup-old-sensory.sh
   ```

## Related Commands

- `/mcp-list` - List all MCP servers
- `/mcp-status` - Quick status check
- `/mcp-restart` - Restart MCP servers

## Notes

- Comprehensive diagnostic tool
- Provides specific recovery guidance
- Safe to run frequently
- No destructive actions
- Checks all three tiers of MCP architecture
