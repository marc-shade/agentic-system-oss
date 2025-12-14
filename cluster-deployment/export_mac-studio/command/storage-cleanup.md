# storage-cleanup

Clean up old sensory data to maintain the 30-day rolling window.

Run the cleanup script:

```bash
/Volumes/SSDRAID0/agentic-system/cleanup-old-sensory.sh
```

This will:
1. Move vision files older than 30 days from hot to cold storage
2. Move webcam files older than 30 days from hot to cold storage
3. Delete archived files older than 90 days (permanent deletion)
4. Log all operations to cleanup log file
5. Display summary of remaining files

The cleanup maintains:
- **Hot tier**: Last 30 days of sensory data (fast access)
- **Cold tier**: 31-90 days archived (backup)
- **Deleted**: 90+ days (no longer needed)

Check the log:
```bash
tail -20 /Volumes/SSDRAID0/agentic-system/cleanup.log
```

This cleanup runs automatically daily via cron, but can be triggered manually when storage is low.
