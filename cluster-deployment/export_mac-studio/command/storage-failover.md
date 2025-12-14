# storage-failover

Switch to cold tier storage if hot tier becomes unavailable.

This is an emergency command for when SSDRAID0 is unavailable.

Check if hot tier is available:
```bash
if [ ! -d "/Volumes/SSDRAID0/agentic-system" ]; then
    echo "⚠️  SSDRAID0 not available - operating in DEGRADED MODE"
    echo "Using cold storage: /Volumes/FILES/agentic-system"
    echo ""
    echo "Performance Impact:"
    echo "  - Voice TTS: 5-10x slower"
    echo "  - Database queries: 5-10x slower"
    echo "  - Agent spawning: 2-3x slower"
    echo ""
    echo "To restore full performance, reconnect SSDRAID0 and restart services."
else
    echo "✅ Hot tier available - operating normally"
    echo "Primary: /Volumes/SSDRAID0/agentic-system"
fi
```

**Failover procedure** (automatic via environmental-awareness hook):
1. Environmental awareness detects missing SSDRAID0
2. Configuration falls back to `AGENTIC_COLD_DATA` environment variable
3. Services continue operating (degraded performance)
4. Backup data on FILES ensures no data loss

**Manual failover** (if needed):
```bash
export AGENTIC_HOT_DATA="/Volumes/FILES/agentic-system/backups"
export AGENTIC_DB_PATH="/Volumes/FILES/agentic-system/backups/databases"
export AGENTIC_VOICE_CACHE="/Volumes/FILES/agentic-system/backups/voice-cache"
```

Then restart MCP servers and services.
