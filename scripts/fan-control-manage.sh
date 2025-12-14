#!/bin/bash
# Fan Control Management Script for Mac Pro 5,1

case "$1" in
    status)
        echo "=== Fan Control Service Status ==="
        systemctl --user status gentle-fan-control.service
        echo ""
        echo "=== Current Fan Speeds ==="
        for i in {1..6}; do
            label=$(cat /sys/devices/platform/applesmc.768/fan${i}_label)
            rpm=$(cat /sys/devices/platform/applesmc.768/fan${i}_input)
            printf "Fan %d %-8s: %4d RPM\n" $i "$label" $rpm
        done
        echo ""
        echo "=== CPU Temperature ==="
        sensors | grep "Core" | head -6
        ;;
    start)
        systemctl --user start gentle-fan-control.service
        echo "Fan control service started"
        ;;
    stop)
        systemctl --user stop gentle-fan-control.service
        echo "Fan control service stopped"
        ;;
    restart)
        systemctl --user restart gentle-fan-control.service
        echo "Fan control service restarted"
        ;;
    enable)
        systemctl --user enable gentle-fan-control.service
        echo "Fan control service enabled (will start on boot)"
        ;;
    disable)
        systemctl --user disable gentle-fan-control.service
        echo "Fan control service disabled"
        ;;
    logs)
        journalctl --user -u gentle-fan-control.service --no-pager -n "${2:-50}"
        ;;
    follow)
        journalctl --user -u gentle-fan-control.service -f
        ;;
    permissions)
        echo "Setting fan control permissions..."
        sudo chmod 666 /sys/devices/platform/applesmc.768/fan*_manual /sys/devices/platform/applesmc.768/fan*_output
        echo "Permissions set"
        ;;
    *)
        echo "Fan Control Management for Mac Pro 5,1"
        echo ""
        echo "Usage: $0 {status|start|stop|restart|enable|disable|logs|follow|permissions}"
        echo ""
        echo "Commands:"
        echo "  status       - Show service status, fan speeds, and temperatures"
        echo "  start        - Start the fan control service"
        echo "  stop         - Stop the fan control service"
        echo "  restart      - Restart the fan control service"
        echo "  enable       - Enable service to start on boot"
        echo "  disable      - Disable service from starting on boot"
        echo "  logs [N]     - Show last N log entries (default: 50)"
        echo "  follow       - Follow logs in real-time"
        echo "  permissions  - Fix fan control permissions (requires sudo)"
        exit 1
        ;;
esac
