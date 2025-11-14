#!/bin/bash
# Orchestrator Task Delegation to Builder Node
# Enables SSH + tmux integration for persistent context across machines

BUILDER_IP="192.168.1.183"
BUILDER_USER="marc"
BUILDER_SESSION_CMD="builder-session"

usage() {
    echo "Usage: $0 {create|execute|attach|status} [task-name] [command]"
    echo ""
    echo "Commands:"
    echo "  create <task-name>              - Create new tmux session on Builder"
    echo "  execute <task-name> <command>   - Execute command in Builder session"
    echo "  attach <task-name>              - Attach to Builder session (interactive)"
    echo "  status                          - Show all Builder sessions"
    exit 1
}

case "$1" in
    create)
        if [ -z "$2" ]; then
            echo "Error: Task name required"
            usage
        fi
        TASK_NAME="$2"
        echo "🔨 Creating Builder session: $TASK_NAME"

        ssh ${BUILDER_USER}@${BUILDER_IP} "
            cd /mnt/agentic-system
            ~/builder-session create $TASK_NAME 2>/dev/null || \
            ~/.local/bin/builder-session create $TASK_NAME 2>/dev/null || \
            /usr/local/bin/builder-session create $TASK_NAME
        "
        echo "✅ Session created on Builder node"
        ;;

    execute)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Error: Task name and command required"
            usage
        fi
        TASK_NAME="$2"
        COMMAND="${@:3}"
        echo "⚙️  Executing in Builder session: $TASK_NAME"
        echo "📝 Command: $COMMAND"

        ssh ${BUILDER_USER}@${BUILDER_IP} "
            tmux send-keys -t $TASK_NAME '$COMMAND' C-m
        "
        echo "✅ Command sent to Builder session"
        ;;

    attach)
        if [ -z "$2" ]; then
            echo "Error: Task name required"
            usage
        fi
        TASK_NAME="$2"
        echo "🔗 Attaching to Builder session: $TASK_NAME"

        ssh -t ${BUILDER_USER}@${BUILDER_IP} "tmux attach-session -t $TASK_NAME"
        ;;

    status)
        echo "📊 Builder Node Sessions:"
        ssh ${BUILDER_USER}@${BUILDER_IP} "tmux list-sessions 2>/dev/null || echo 'No active sessions'"
        ;;

    *)
        usage
        ;;
esac
