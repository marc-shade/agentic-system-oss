#!/bin/bash
# Sensory Data Cleanup Script - Maintains 30-day rolling window
# Runs daily via cron to move old data from hot to cold tier

set -e


# Platform-aware storage detection
detect_storage_base() {
    if [ -n "$AGENTIC_SYSTEM_PATH" ] && [ -d "$AGENTIC_SYSTEM_PATH" ]; then
        echo "$AGENTIC_SYSTEM_PATH"
        return
    fi
    case "$(uname -s)" in
        Darwin)
            if [ -d "/Volumes/SSDRAID0/agentic-system" ]; then
                echo "/Volumes/SSDRAID0/agentic-system"
            elif [ -d "/Volumes/FILES/agentic-system" ]; then
                echo "/Volumes/FILES/agentic-system"
            fi
            ;;
        Linux)
            if [ -d "/home/marc/agentic-system" ]; then
                echo "/home/marc/agentic-system"
            elif [ -d "/mnt/agentic-system" ]; then
                echo "/mnt/agentic-system"
            fi
            ;;
    esac
}

STORAGE_BASE=$(detect_storage_base)

HOT_SENSORY="$STORAGE_BASE/sensory-recent"
COLD_SENSORY="$STORAGE_BASE/data/sensory"
LOG_FILE="$STORAGE_BASE/cleanup.log"
ARCHIVE_DIR="$COLD_SENSORY/archive"

echo "$(date): Starting sensory data cleanup (30-day window)..." >> "$LOG_FILE"

# Create archive directory
mkdir -p "$ARCHIVE_DIR/vision"
mkdir -p "$ARCHIVE_DIR/webcam"

# Find and move vision files older than 30 days from hot tier
if [ -d "$HOT_SENSORY/vision" ]; then
    old_vision=$(find "$HOT_SENSORY/vision" -type f -mtime +30 | wc -l | tr -d ' ')

    if [ "$old_vision" -gt 0 ]; then
        echo "$(date): Moving $old_vision old vision files to cold storage..." >> "$LOG_FILE"
        find "$HOT_SENSORY/vision" -type f -mtime +30 -exec mv {} "$ARCHIVE_DIR/vision/" \;
        echo "$(date): ✅ $old_vision vision files archived" >> "$LOG_FILE"
    else
        echo "$(date): No old vision files to archive" >> "$LOG_FILE"
    fi
fi

# Find and move webcam files older than 30 days from hot tier
if [ -d "$HOT_SENSORY/webcam" ]; then
    old_webcam=$(find "$HOT_SENSORY/webcam" -type f -mtime +30 2>/dev/null | wc -l | tr -d ' ')

    if [ "$old_webcam" -gt 0 ]; then
        echo "$(date): Moving $old_webcam old webcam files to cold storage..." >> "$LOG_FILE"
        find "$HOT_SENSORY/webcam" -type f -mtime +30 -exec mv {} "$ARCHIVE_DIR/webcam/" \;
        echo "$(date): ✅ $old_webcam webcam files archived" >> "$LOG_FILE"
    else
        echo "$(date): No old webcam files to archive" >> "$LOG_FILE"
    fi
fi

# Delete archived files older than 90 days from cold storage (keeping 90-day total history)
echo "$(date): Cleaning up files older than 90 days from archive..." >> "$LOG_FILE"

deleted_vision=$(find "$ARCHIVE_DIR/vision" -type f -mtime +90 2>/dev/null | wc -l | tr -d ' ')
deleted_webcam=$(find "$ARCHIVE_DIR/webcam" -type f -mtime +90 2>/dev/null | wc -l | tr -d ' ')

if [ "$deleted_vision" -gt 0 ]; then
    find "$ARCHIVE_DIR/vision" -type f -mtime +90 -delete
    echo "$(date): ✅ Deleted $deleted_vision vision files older than 90 days" >> "$LOG_FILE"
fi

if [ "$deleted_webcam" -gt 0 ]; then
    find "$ARCHIVE_DIR/webcam" -type f -mtime +90 -delete
    echo "$(date): ✅ Deleted $deleted_webcam webcam files older than 90 days" >> "$LOG_FILE"
fi

# Summary
hot_count=$(find "$HOT_SENSORY" -type f \( -name "*.png" -o -name "*.jpg" \) 2>/dev/null | wc -l | tr -d ' ')
hot_size=$(du -sh "$HOT_SENSORY" 2>/dev/null | cut -f1)
archive_count=$(find "$ARCHIVE_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')

echo "$(date): ✅ Cleanup completed" >> "$LOG_FILE"
echo "$(date): Hot tier: $hot_count files ($hot_size)" >> "$LOG_FILE"
echo "$(date): Archive: $archive_count files" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Keep only last 200 lines of log
tail -n 200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

exit 0
