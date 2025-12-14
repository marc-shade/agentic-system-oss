# storage-status

Check the status of the two-tier storage architecture (hot/cold).

Run commands to check disk usage:

```bash
# Hot tier (SSDRAID0) status
echo "=== HOT TIER (SSDRAID0) ==="
du -sh /Volumes/SSDRAID0/agentic-system/*

# Cold tier (FILES) backup status
echo ""
echo "=== COLD TIER (FILES) BACKUPS ==="
du -sh /Volumes/FILES/agentic-system/backups/*

# Overall storage summary
echo ""
echo "=== STORAGE SUMMARY ==="
df -h /Volumes/SSDRAID0 | tail -n 1
df -h /Volumes/FILES | tail -n 1
```

This shows:
- Database sizes on hot tier
- Voice cache size
- Sensory data (30-day window)
- Backup sizes on cold tier
- Total available space on both drives

Use this to monitor storage health and identify when cleanup or backup is needed.
