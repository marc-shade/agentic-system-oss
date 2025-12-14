#!/bin/bash
# Fix all macOS-specific paths to Linux equivalents
# Converts /Volumes/SSDRAID0/ and /Volumes/FILES/ to /mnt/agentic-system/ or /home/marc/agentic-system/

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

echo "🔧 Fixing macOS paths in KutiraAI and other services..."
echo ""

KUTIRAAI_DIR="$STORAGE_BASE/services/kutiraai"
AGENTIC_DIR="$STORAGE_BASE"

# Backup the file first
echo "📦 Creating backup..."
cp "${KUTIRAAI_DIR}/api-server-real.js" "${KUTIRAAI_DIR}/api-server-real.js.backup-$(date +%Y%m%d-%H%M%S)"

echo "🔍 Replacing paths in api-server-real.js..."

# Replace /Volumes/SSDRAID0/agentic-system with /mnt/agentic-system
sed -i "s|/Volumes/SSDRAID0/agentic-system|/mnt/agentic-system|g" "${KUTIRAAI_DIR}/api-server-real.js"

# Replace /Volumes/FILES/agentic-system with /mnt/agentic-system
sed -i "s|/Volumes/FILES/agentic-system|/mnt/agentic-system|g" "${KUTIRAAI_DIR}/api-server-real.js"

# Replace /Volumes/FILES/code/kutiraai with $STORAGE_BASE/services/kutiraai
sed -i "s|/Volumes/FILES/code/kutiraai|$STORAGE_BASE/services/kutiraai|g" "${KUTIRAAI_DIR}/api-server-real.js"

# Replace /Volumes/SSDRAID0/code with /mnt/agentic-system
sed -i "s|/Volumes/SSDRAID0/code|/mnt/agentic-system|g" "${KUTIRAAI_DIR}/api-server-real.js"

# Replace /Volumes/FILES/code with /mnt/agentic-system
sed -i "s|/Volumes/FILES/code|/mnt/agentic-system|g" "${KUTIRAAI_DIR}/api-server-real.js"

# Replace /Volumes/FILES/temporal-db with $STORAGE_BASE/databases/temporal
sed -i "s|/Volumes/FILES/temporal-db|$STORAGE_BASE/databases/temporal|g" "${KUTIRAAI_DIR}/api-server-real.js"

echo ""
echo "✅ Path replacements complete!"
echo ""

# Show what was changed
echo "📊 Verification - checking for remaining /Volumes references:"
if grep -n "/Volumes" "${KUTIRAAI_DIR}/api-server-real.js" 2>/dev/null; then
    echo ""
    echo "⚠️  WARNING: Some /Volumes references still exist (see above)"
else
    echo "✅ No /Volumes references found - all paths fixed!"
fi

echo ""
echo "🔄 Next steps:"
echo "  1. Create missing directories (autonomous-operation, etc.)"
echo "  2. Restart kutiraai-api service: systemctl --user restart kutiraai-api.service"
echo "  3. Check logs: journalctl --user -u kutiraai-api.service -f"
