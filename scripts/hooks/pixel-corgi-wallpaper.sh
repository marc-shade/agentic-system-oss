#!/bin/bash
# Pixel Corgi Wallpaper Generator v2
# Uses DSPy for context-aware prompt generation
# Generates visuals that reflect actual work being performed

set -e

# Configuration

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

OUTPUT_DIR="$STORAGE_BASE/generated-images"
WALLPAPER_FILE="$OUTPUT_DIR/pixel_corgi_current.jpg"
LOCK_FILE="/tmp/pixel-corgi-gen.lock"
LOG_FILE="/tmp/pixel-corgi-wallpaper.log"
COOLDOWN_FILE="/tmp/pixel-corgi-cooldown"
COOLDOWN_SECONDS=30  # Minimum seconds between generations
DSPY_PROMPTER="$STORAGE_BASE/mcp-servers/image-gen-mcp/src/image_gen_mcp/dspy_prompter.py"

# Context from arguments and environment
EVENT_TYPE="${1:-idle}"
TOOL_NAME="${2:-}"
TASK_DESC="${3:-}"
MOOD="${4:-neutral}"
ERROR_MSG="${5:-}"

# Also check environment variables (set by hooks)
TOOL_NAME="${TOOL_NAME:-$CLAUDE_TOOL_NAME}"
TASK_DESC="${TASK_DESC:-$CLAUDE_TASK_DESC}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check cooldown to prevent too frequent updates
check_cooldown() {
    if [ -f "$COOLDOWN_FILE" ]; then
        last_run=$(cat "$COOLDOWN_FILE")
        now=$(date +%s)
        elapsed=$((now - last_run))
        if [ $elapsed -lt $COOLDOWN_SECONDS ]; then
            log "Cooldown active ($elapsed < $COOLDOWN_SECONDS seconds). Skipping."
            exit 0
        fi
    fi
}

# Set cooldown timestamp
set_cooldown() {
    date +%s > "$COOLDOWN_FILE"
}

# Acquire lock to prevent concurrent generations
acquire_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        log "Another generation in progress. Skipping."
        exit 0
    fi
}

# Generate prompt using DSPy (with fallback)
generate_prompt() {
    local event="$1"
    local tool="$2"
    local task="$3"
    local mood="$4"
    local error="$5"

    # Try DSPy prompter first (uses fallback internally if LLM unavailable)
    if [ -f "$DSPY_PROMPTER" ]; then
        prompt=$($STORAGE_BASE/.venv/bin/python "$DSPY_PROMPTER" \
            --event "$event" \
            ${tool:+--tool "$tool"} \
            ${task:+--task "$task"} \
            --mood "$mood" \
            ${error:+--error "$error"} \
            --no-llm 2>/dev/null)  # Use fallback for speed, LLM optional

        if [ -n "$prompt" ]; then
            echo "$prompt"
            return
        fi
    fi

    # Ultimate fallback - simple hardcoded prompts
    local base_prompt="8-bit NES pixel art sprite, cute corgi dog Pixel, orange white black tricolor, clean pixels, retro game style"

    case "$event" in
        success|complete|done)
            echo "$base_prompt, jumping with joy, confetti, sparkles, victory pose, celebrating"
            ;;
        error|fail|failure)
            echo "$base_prompt, confused expression, tilted head, floating bug icons, worried"
            ;;
        thinking|working|processing)
            echo "$base_prompt, focused expression, tiny glasses, thinking pose"
            ;;
        start|begin|hello)
            echo "$base_prompt, excited alert pose, ears perked, wagging tail"
            ;;
        end|bye|goodbye)
            echo "$base_prompt, sleepy yawning, cozy pose, moon and stars"
            ;;
        security|scan)
            echo "$base_prompt, detective hat, magnifying glass, investigating pose, lock icons"
            ;;
        git|commit|push)
            echo "$base_prompt, delivery cap, carrying package, proud stance, branch icons"
            ;;
        coding|edit|write)
            echo "$base_prompt, tiny glasses, keyboard, focused typing, code brackets floating"
            ;;
        research|read|search)
            echo "$base_prompt, professor glasses, stack of books, thoughtful pose, lightbulbs"
            ;;
        test|testing)
            echo "$base_prompt, lab coat, test tubes, scientist pose, checkmarks"
            ;;
        build|compile|docker)
            echo "$base_prompt, hardhat, wrench, builder stance, gear icons"
            ;;
        *)
            echo "$base_prompt, happy sitting, friendly expression, pixel perfect"
            ;;
    esac
}

# Generate image using Pollinations API
generate_image() {
    local prompt="$1"
    local encoded_prompt=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$prompt'''))")
    local seed=$RANDOM
    local url="https://image.pollinations.ai/prompt/${encoded_prompt}?width=512&height=512&nologo=true&seed=${seed}"

    log "Event: $EVENT_TYPE | Tool: $TOOL_NAME | Task: $TASK_DESC"
    log "Prompt: $prompt"

    # Download image with timeout
    if curl -s -L --max-time 60 -o "$WALLPAPER_FILE.tmp" "$url"; then
        # Verify it's a valid image
        if file "$WALLPAPER_FILE.tmp" | grep -qE "(JPEG|PNG|image)"; then
            mv "$WALLPAPER_FILE.tmp" "$WALLPAPER_FILE"
            log "Image saved to $WALLPAPER_FILE"
            return 0
        else
            log "Downloaded file is not a valid image"
            rm -f "$WALLPAPER_FILE.tmp"
            return 1
        fi
    else
        log "Failed to download image"
        rm -f "$WALLPAPER_FILE.tmp"
        return 1
    fi
}

# Set GNOME wallpaper
set_wallpaper() {
    if command -v gsettings &> /dev/null; then
        gsettings set org.gnome.desktop.background picture-uri "file://$WALLPAPER_FILE"
        gsettings set org.gnome.desktop.background picture-uri-dark "file://$WALLPAPER_FILE"
        gsettings set org.gnome.desktop.background picture-options "centered"
        log "Wallpaper updated"
    else
        log "gsettings not available"
    fi
}

# Main execution
main() {
    log "=== Pixel Corgi Generator v2 ==="
    log "Event: $EVENT_TYPE | Tool: $TOOL_NAME | Task: ${TASK_DESC:0:50}"

    # Check cooldown
    check_cooldown

    # Acquire lock
    acquire_lock

    # Generate contextual prompt
    prompt=$(generate_prompt "$EVENT_TYPE" "$TOOL_NAME" "$TASK_DESC" "$MOOD" "$ERROR_MSG")

    # Generate image
    if generate_image "$prompt"; then
        # Set wallpaper
        set_wallpaper
        # Set cooldown
        set_cooldown
        log "Success!"
    else
        log "Generation failed"
    fi
}

# Run in background to not block hooks
main &

exit 0
