#!/bin/bash
#
# Batch Fix Hardcoded Paths in Shell Scripts
# ============================================
#
# Finds and fixes all hardcoded paths in shell scripts across the codebase.
# Adds platform-aware path detection to ensure cross-platform compatibility.
#
# Usage:
#     ./batch_fix_shell_paths.sh --dry-run  # Preview changes
#     ./batch_fix_shell_paths.sh            # Apply changes
#

set -e

# Detect our own storage base
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
DRY_RUN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        *) shift ;;
    esac
done

echo "============================================================"
echo " Batch Fix Hardcoded Paths in Shell Scripts"
echo "============================================================"
echo ""
echo "Storage base: $STORAGE_BASE"
echo "Mode: $([ "$DRY_RUN" = true ] && echo 'DRY RUN (preview only)' || echo 'APPLY CHANGES')"
echo ""

# Files to skip
SKIP_FILES=(
    "batch_fix_shell_paths.sh"       # This script
    "detect-storage.sh"              # Detection script itself
    "backup-sync.sh"                 # May have intentional paths
)

# Directories to skip
SKIP_DIRS=(
    ".git"
    "node_modules"
    "venv"
    ".venv"
    "backups"
)

# The platform detection function to inject
DETECTION_FUNCTION='
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
'

# Check if file should be skipped
should_skip() {
    local file=$1
    local basename=$(basename "$file")

    # Check skip files
    for skip in "${SKIP_FILES[@]}"; do
        if [ "$basename" = "$skip" ]; then
            return 0
        fi
    done

    # Check skip directories
    for skip in "${SKIP_DIRS[@]}"; do
        if [[ "$file" == *"/$skip/"* ]]; then
            return 0
        fi
    done

    return 1
}

# Check if file already has platform detection
has_detection() {
    local file=$1
    grep -q "detect_storage_base\|detect_storage\|STORAGE_BASE.*uname" "$file" 2>/dev/null
}

# Check if file has hardcoded paths
has_hardcoded_paths() {
    local file=$1
    grep -qE '"/Volumes/SSDRAID0/agentic-system|"/Volumes/FILES/agentic-system|"/mnt/agentic-system|"/home/marc/agentic-system' "$file" 2>/dev/null
}

# Fix a single file
fix_file() {
    local file=$1
    local basename=$(basename "$file")

    # Skip if needed
    if should_skip "$file"; then
        [ "$VERBOSE" = true ] && echo "  SKIP (in skip list): $basename"
        return 1
    fi

    # Skip if already has detection
    if has_detection "$file"; then
        [ "$VERBOSE" = true ] && echo "  SKIP (already has detection): $basename"
        return 1
    fi

    # Check for hardcoded paths
    if ! has_hardcoded_paths "$file"; then
        [ "$VERBOSE" = true ] && echo "  SKIP (no hardcoded paths): $basename"
        return 1
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "  WOULD FIX: $file"
        return 0
    fi

    # Create backup
    cp "$file" "$file.bak"

    # Read file content
    local content=$(cat "$file")
    local shebang=""
    local rest=""

    # Extract shebang if present
    if [[ "$content" == "#!/"* ]]; then
        shebang=$(echo "$content" | head -1)
        rest=$(echo "$content" | tail -n +2)
    else
        rest="$content"
    fi

    # Find where to insert detection (after initial comments and set commands)
    local temp_file=$(mktemp)

    # Write shebang
    [ -n "$shebang" ] && echo "$shebang" > "$temp_file"

    # Process rest of file
    local in_header=true
    local detection_added=false

    while IFS= read -r line || [ -n "$line" ]; do
        if [ "$in_header" = true ]; then
            # Keep initial comments and set commands
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ "$line" =~ ^[[:space:]]*$ ]] || [[ "$line" =~ ^set[[:space:]] ]]; then
                echo "$line" >> "$temp_file"
            else
                # End of header, insert detection function
                if [ "$detection_added" = false ]; then
                    echo "$DETECTION_FUNCTION" >> "$temp_file"
                    detection_added=true
                fi
                in_header=false
                # Process this line for path replacements
                line=$(echo "$line" | sed \
                    -e 's|"/Volumes/SSDRAID0/agentic-system"|"$STORAGE_BASE"|g' \
                    -e 's|"/Volumes/FILES/agentic-system"|"$STORAGE_BASE"|g' \
                    -e 's|"/mnt/agentic-system"|"$STORAGE_BASE"|g' \
                    -e 's|"/home/marc/agentic-system"|"$STORAGE_BASE"|g' \
                    -e "s|'/Volumes/SSDRAID0/agentic-system'|'\$STORAGE_BASE'|g" \
                    -e "s|'/Volumes/FILES/agentic-system'|'\$STORAGE_BASE'|g" \
                    -e "s|'/mnt/agentic-system'|'\$STORAGE_BASE'|g" \
                    -e "s|'/home/marc/agentic-system'|'\$STORAGE_BASE'|g" \
                    -e 's|/Volumes/SSDRAID0/agentic-system/|$STORAGE_BASE/|g' \
                    -e 's|/Volumes/FILES/agentic-system/|$STORAGE_BASE/|g' \
                    -e 's|/mnt/agentic-system/|$STORAGE_BASE/|g' \
                    -e 's|/home/marc/agentic-system/|$STORAGE_BASE/|g')
                echo "$line" >> "$temp_file"
            fi
        else
            # Process line for path replacements
            line=$(echo "$line" | sed \
                -e 's|"/Volumes/SSDRAID0/agentic-system"|"$STORAGE_BASE"|g' \
                -e 's|"/Volumes/FILES/agentic-system"|"$STORAGE_BASE"|g' \
                -e 's|"/mnt/agentic-system"|"$STORAGE_BASE"|g' \
                -e 's|"/home/marc/agentic-system"|"$STORAGE_BASE"|g' \
                -e "s|'/Volumes/SSDRAID0/agentic-system'|'\$STORAGE_BASE'|g" \
                -e "s|'/Volumes/FILES/agentic-system'|'\$STORAGE_BASE'|g" \
                -e "s|'/mnt/agentic-system'|'\$STORAGE_BASE'|g" \
                -e "s|'/home/marc/agentic-system'|'\$STORAGE_BASE'|g" \
                -e 's|/Volumes/SSDRAID0/agentic-system/|$STORAGE_BASE/|g' \
                -e 's|/Volumes/FILES/agentic-system/|$STORAGE_BASE/|g' \
                -e 's|/mnt/agentic-system/|$STORAGE_BASE/|g' \
                -e 's|/home/marc/agentic-system/|$STORAGE_BASE/|g')
            echo "$line" >> "$temp_file"
        fi
    done <<< "$rest"

    # If we never got out of header, add detection at end
    if [ "$detection_added" = false ]; then
        echo "$DETECTION_FUNCTION" >> "$temp_file"
    fi

    # Move temp file to original
    mv "$temp_file" "$file"
    chmod +x "$file"

    # Remove backup on success
    rm "$file.bak"

    echo "  FIXED: $file"
    return 0
}

# Find all shell scripts with hardcoded paths
echo "Scanning for shell scripts with hardcoded paths..."
echo ""

FIXED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

# Find shell scripts
while IFS= read -r -d '' file; do
    if fix_file "$file"; then
        ((FIXED_COUNT++))
    else
        ((SKIPPED_COUNT++))
    fi
done < <(find "$STORAGE_BASE" -type f \( -name "*.sh" -o -name "*.bash" \) -print0 2>/dev/null)

echo ""
echo "============================================================"
echo " Summary"
echo "============================================================"
echo "  Files $([ "$DRY_RUN" = true ] && echo 'would be ' || echo '')fixed: $FIXED_COUNT"
echo "  Files skipped: $SKIPPED_COUNT"
echo "  Errors: $ERROR_COUNT"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "  Run without --dry-run to apply changes."
fi
