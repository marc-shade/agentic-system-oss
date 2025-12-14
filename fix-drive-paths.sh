#!/bin/bash
# fix-drive-paths.sh - Find and fix wrong drive paths
# Created: 2025-10-31
# Purpose: Ensure all code references use SSDRAID0 (primary) not FILES (backup)

set -euo pipefail


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

PRIMARY="$STORAGE_BASE"
BACKUP="$STORAGE_BASE"

echo "Drive Path Correction Utility"
echo "=============================="
echo ""
echo "PRIMARY (correct): $PRIMARY"
echo "BACKUP (wrong):    $BACKUP"
echo ""

# Function to scan for wrong paths
scan_wrong_paths() {
    local dir="$1"
    echo "Scanning $dir for wrong paths..."

    # Find files with wrong paths (excluding migration scripts which legitimately reference FILES)
    grep -r "$BACKUP" "$dir" \
        --exclude-dir=".git" \
        --exclude-dir="node_modules" \
        --exclude-dir="venv" \
        --exclude-dir="__pycache__" \
        --exclude="*.log" \
        --exclude="*.db" \
        --include="*.py" \
        --include="*.sh" \
        --include="*.json" \
        --include="*.md" \
        2>/dev/null | \
        grep -v "migrate-" | \
        grep -v "backup-sync" | \
        grep -v "DRIVE_CONFIGURATION.md" || true
}

# Function to fix paths in a file
fix_file_paths() {
    local file="$1"

    # Skip migration and backup scripts
    if [[ "$file" =~ migrate- ]] || [[ "$file" =~ backup-sync ]]; then
        return
    fi

    # Create backup
    cp "$file" "$file.bak"

    # Replace paths
    sed -i '' "s|$BACKUP|$PRIMARY|g" "$file"

    echo "  Fixed: $file"
}

# Scan common locations
echo "1. Scanning SSDRAID0 agentic-system..."
scan_wrong_paths "$PRIMARY"

echo ""
echo "2. Scanning Claude configuration..."
scan_wrong_paths "/Users/marc/.claude"

echo ""
echo "3. Summary Report"
echo "=================="
echo ""

# Count occurrences
count_wrong=$(grep -r "$BACKUP" "$PRIMARY" \
    --exclude-dir=".git" --exclude-dir="node_modules" --exclude-dir="venv" \
    --include="*.py" --include="*.sh" --include="*.json" \
    2>/dev/null | grep -v "migrate-" | grep -v "backup-sync" | wc -l | xargs)

echo "Wrong paths found: $count_wrong"

if [ "$count_wrong" -gt 0 ]; then
    echo ""
    echo "To automatically fix these paths, run:"
    echo "  bash $0 --fix"
else
    echo ""
    echo "All paths are correct!"
fi

# Auto-fix mode
if [ "${1:-}" = "--fix" ]; then
    echo ""
    echo "4. Fixing Paths (--fix mode)"
    echo "=============================="

    # Find and fix Python files
    find "$PRIMARY" -name "*.py" -type f | while read -r file; do
        if grep -q "$BACKUP" "$file" 2>/dev/null; then
            if [[ ! "$file" =~ migrate- ]]; then
                fix_file_paths "$file"
            fi
        fi
    done

    # Find and fix shell scripts
    find "$PRIMARY" -name "*.sh" -type f | while read -r file; do
        if grep -q "$BACKUP" "$file" 2>/dev/null; then
            if [[ ! "$file" =~ migrate- ]] && [[ ! "$file" =~ backup-sync ]]; then
                fix_file_paths "$file"
            fi
        fi
    done

    echo ""
    echo "Paths fixed! Backups saved with .bak extension."
fi

echo ""
echo "Verification Commands:"
echo "====================="
echo ""
echo "# Check running processes:"
echo "  ps aux | grep python | grep agentic-system"
echo ""
echo "# Verify databases:"
echo "  find /mnt/agentic-system -name '*.db' -type f"
echo ""
echo "# Test from correct location:"
echo "  cd $STORAGE_BASE/persistent-agent-sdk"
echo "  source venv/bin/activate"
echo "  python3 -c 'import os; print(os.getcwd())'"
echo ""
