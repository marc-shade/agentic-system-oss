# storage-backup

Manually trigger a backup sync from hot (SSDRAID0) to cold (FILES) storage.

Run the backup script:

```bash
/Volumes/SSDRAID0/agentic-system/backup-sync.sh
```

This will:
1. Sync databases (critical data) - rsync with --delete
2. Sync agent memory (important data) - rsync with --delete
3. Sync MCP state (configuration) - rsync with --delete
4. Log all operations to backup log file
5. Keep only last 100 lines of log

**Note**: Voice cache and sensory data are NOT backed up (easily regenerated).

After backup, check the log:
```bash
tail -20 /Volumes/FILES/agentic-system/backups/sync.log
```

This backup runs automatically hourly via cron, but can be triggered manually when needed.
