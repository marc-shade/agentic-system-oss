#!/bin/bash
# Setup tmux with persistent cross-machine context for Builder node


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

BUILDER_IP="192.168.1.183"
BUILDER_USER="marc"

echo "🖥️  Setting up tmux persistent context on Builder node"

# Create tmux configuration with persistent session support
cat > /tmp/builder_tmux.conf << 'EOF'
# Persistent Context tmux Configuration for Builder Node
# Enables cross-machine context retention for agentic workflows

# Session management
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-resurrect'
set -g @plugin 'tmux-plugins/tmux-continuum'

# Auto-save sessions every 15 minutes
set -g @continuum-restore 'on'
set -g @continuum-save-interval '15'

# Restore pane contents
set -g @resurrect-capture-pane-contents 'on'

# Resurrect strategy for processes
set -g @resurrect-strategy-python3 'session'
set -g @resurrect-strategy-bash 'session'

# Custom session directory for cluster coordination
set -g @resurrect-dir '$STORAGE_BASE/databases/cluster/tmux-sessions'

# Status bar configuration
set -g status-bg colour235
set -g status-fg colour136
set -g status-left '#[fg=colour160]🔨 Builder Node #[fg=colour136]| #S '
set -g status-left-length 40
set -g status-right '#[fg=colour166]#(hostname) #[fg=colour136]| %H:%M'

# Window numbering
set -g base-index 1
setw -g pane-base-index 1

# Mouse support
set -g mouse on

# History limit
set -g history-limit 50000

# Enable RGB color
set -g default-terminal "screen-256color"

# Pane navigation with vim keys
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Reload config
bind r source-file ~/.tmux.conf \; display "Config reloaded!"
EOF

# Copy tmux configuration to Builder
echo "📦 Deploying tmux configuration..."
scp /tmp/builder_tmux.conf ${BUILDER_USER}@${BUILDER_IP}:~/.tmux.conf

# Create session management helper script
cat > /tmp/tmux_session_manager.sh << 'EOF'
#!/bin/bash
# Tmux Session Manager for Builder Node
# Manages persistent sessions with cross-machine context

TMUX_SESSION_DIR="$STORAGE_BASE/databases/cluster/tmux-sessions"
NODE_ID="macpro51"

case "$1" in
    create)
        SESSION_NAME="${2:-builder-work}"
        tmux new-session -d -s "$SESSION_NAME"
        echo "✅ Created session: $SESSION_NAME"
        echo "📂 Context saved to: $TMUX_SESSION_DIR"
        ;;
    attach)
        SESSION_NAME="${2:-builder-work}"
        tmux attach-session -t "$SESSION_NAME"
        ;;
    list)
        tmux list-sessions
        ;;
    save)
        ~/.tmux/plugins/tmux-resurrect/scripts/save.sh
        echo "💾 Session state saved"
        ;;
    restore)
        ~/.tmux/plugins/tmux-resurrect/scripts/restore.sh
        echo "♻️  Session state restored"
        ;;
    *)
        echo "Usage: $0 {create|attach|list|save|restore} [session-name]"
        exit 1
        ;;
esac
EOF

# Deploy session manager
scp /tmp/tmux_session_manager.sh ${BUILDER_USER}@${BUILDER_IP}:/tmp/tmux_session_manager.sh
ssh ${BUILDER_USER}@${BUILDER_IP} "chmod +x /tmp/tmux_session_manager.sh && sudo mv /tmp/tmux_session_manager.sh /usr/local/bin/builder-session"

# Create tmux session directory
ssh ${BUILDER_USER}@${BUILDER_IP} "mkdir -p $STORAGE_BASE/databases/cluster/tmux-sessions"

# Install tmux plugin manager if not present
ssh ${BUILDER_USER}@${BUILDER_IP} "
    if [ ! -d ~/.tmux/plugins/tpm ]; then
        git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
        echo '✅ Installed tmux plugin manager'
    fi
    # Install plugins
    ~/.tmux/plugins/tpm/scripts/install_plugins.sh
"

echo "✅ Tmux persistent context setup complete"
echo ""
echo "📋 Usage on Builder node:"
echo "  builder-session create [name]  - Create new persistent session"
echo "  builder-session attach [name]  - Attach to existing session"
echo "  builder-session list           - List all sessions"
echo "  builder-session save           - Save current state"
echo "  builder-session restore        - Restore saved state"
