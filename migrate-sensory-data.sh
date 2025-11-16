#!/bin/bash
# Sensory Data Migration Script - Phase 4
# Migrates recent 30 days of sensory data to SSDRAID0 hot tier

set -e

HOT_SENSORY="/mnt/agentic-system/sensory-recent"
COLD_SENSORY="/Volumes/FILES/agentic-system/data/sensory"
LOG_FILE="/mnt/agentic-system/migration.log"

echo "$(date): Starting sensory data migration to SSDRAID0..." | tee -a "$LOG_FILE"

# Create subdirectories
mkdir -p "$HOT_SENSORY/vision"
mkdir -p "$HOT_SENSORY/webcam"
mkdir -p "$HOT_SENSORY/state"

# Copy config
if [ -f "$COLD_SENSORY/config.json" ]; then
    cp "$COLD_SENSORY/config.json" "$HOT_SENSORY/config.json"
    echo "$(date): ✅ Config copied" | tee -a "$LOG_FILE"
fi

# Migrate recent vision screenshots (last 30 days)
echo "$(date): Phase 1: Vision screenshots (last 30 days)..." | tee -a "$LOG_FILE"
recent_count=$(find "$COLD_SENSORY/vision" -type f -mtime -30 | wc -l | tr -d ' ')
echo "$(date): Found $recent_count recent vision files" | tee -a "$LOG_FILE"

# Copy recent vision files
find "$COLD_SENSORY/vision" -type f -mtime -30 -exec cp {} "$HOT_SENSORY/vision/" \;
copied_count=$(find "$HOT_SENSORY/vision" -type f | wc -l | tr -d ' ')

if [ "$recent_count" -eq "$copied_count" ]; then
    vision_size=$(du -sh "$HOT_SENSORY/vision" | cut -f1)
    echo "$(date): ✅ Vision data migrated ($copied_count files, $vision_size)" | tee -a "$LOG_FILE"
else
    echo "$(date): ❌ Vision migration incomplete (expected: $recent_count, got: $copied_count)" | tee -a "$LOG_FILE"
    exit 1
fi

# Migrate recent webcam data (last 30 days)
echo "$(date): Phase 2: Webcam data (last 30 days)..." | tee -a "$LOG_FILE"
webcam_count=$(find "$COLD_SENSORY/webcam" -type f -mtime -30 2>/dev/null | wc -l | tr -d ' ')

if [ "$webcam_count" -gt 0 ]; then
    find "$COLD_SENSORY/webcam" -type f -mtime -30 -exec cp {} "$HOT_SENSORY/webcam/" \;
    webcam_size=$(du -sh "$HOT_SENSORY/webcam" | cut -f1)
    echo "$(date): ✅ Webcam data migrated ($webcam_count files, $webcam_size)" | tee -a "$LOG_FILE"
else
    echo "$(date): ⚠️  No recent webcam data found" | tee -a "$LOG_FILE"
fi

# Copy state directory
if [ -d "$COLD_SENSORY/state" ]; then
    rsync -av "$COLD_SENSORY/state/" "$HOT_SENSORY/state/" >> "$LOG_FILE" 2>&1
    echo "$(date): ✅ State directory synced" | tee -a "$LOG_FILE"
fi

echo "$(date): ✅ Sensory data migration completed successfully!" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Summary
echo "Migration Summary:" | tee -a "$LOG_FILE"
du -sh "$HOT_SENSORY" | tee -a "$LOG_FILE"
du -sh "$HOT_SENSORY/vision" | tee -a "$LOG_FILE"
du -sh "$HOT_SENSORY/webcam" | tee -a "$LOG_FILE"
du -sh "$HOT_SENSORY/state" | tee -a "$LOG_FILE"
echo "Recent data window: 30 days" | tee -a "$LOG_FILE"

exit 0
