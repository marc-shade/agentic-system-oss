#!/bin/bash
#
# Ensure SMB Shares Always Available
#
# This script ensures network shares are ALWAYS working and accessible by:
# 1. Enabling SMB, NetBIOS, and Avahi services on boot
# 2. Running health checks every 5 minutes
# 3. Auto-recovering from failures
# 4. Logging all status changes
#

set -e

echo "=== Ensuring SMB is Always Available ==="
echo ""

# 1. Enable all required services
echo "1. Enabling services for automatic startup..."
sudo systemctl enable smb.service nmb.service avahi-daemon.service
sudo systemctl start smb.service nmb.service avahi-daemon.service
echo "   ✓ Services enabled and started"
echo ""

# 2. Verify SELinux configuration
echo "2. Ensuring SELinux is configured correctly..."
sudo setsebool -P samba_export_all_rw on
sudo semanage fcontext -a -t samba_share_t "/mnt/agentic-system(/.*)?" 2>/dev/null || echo "   (Context already set)"
sudo restorecon -R /mnt/agentic-system
echo "   ✓ SELinux configured"
echo ""

# 3. Verify firewall allows SMB
echo "3. Ensuring firewall allows SMB..."
if ! sudo firewall-cmd --list-services | grep -q "samba"; then
    sudo firewall-cmd --permanent --add-service=samba
    sudo firewall-cmd --reload
    echo "   ✓ Firewall rule added"
else
    echo "   ✓ Firewall already configured"
fi
echo ""

# 4. Install systemd timer for health checks
echo "4. Installing automatic health check timer..."

# Create systemd service file
sudo tee /etc/systemd/system/smb-health-check.service > /dev/null <<'EOF'
[Unit]
Description=SMB Share Health Check
After=smb.service nmb.service

[Service]
Type=oneshot
ExecStart=/mnt/agentic-system/scripts/check-smb-health.sh
StandardOutput=journal
StandardError=journal
EOF

# Create systemd timer file
sudo tee /etc/systemd/system/smb-health-check.timer > /dev/null <<'EOF'
[Unit]
Description=Run SMB health check every 5 minutes
Requires=smb-health-check.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable smb-health-check.timer
sudo systemctl start smb-health-check.timer
echo "   ✓ Health check timer installed (runs every 5 minutes)"
echo ""

# 5. Run initial health check
echo "5. Running initial health check..."
/mnt/agentic-system/scripts/check-smb-health.sh
echo ""

# 6. Show status
echo "=== SMB Share Status ==="
echo ""
echo "Services:"
systemctl is-active smb.service && echo "  ✓ SMB service: active" || echo "  ✗ SMB service: INACTIVE"
systemctl is-active nmb.service && echo "  ✓ NetBIOS service: active" || echo "  ✗ NetBIOS service: INACTIVE"
systemctl is-active avahi-daemon.service && echo "  ✓ Avahi discovery: active" || echo "  ✗ Avahi discovery: INACTIVE"
systemctl is-active smb-health-check.timer && echo "  ✓ Health check timer: active" || echo "  ✗ Health check timer: INACTIVE"
echo ""

echo "Network Access:"
echo "  • SMB ports: $(ss -tuln | grep -c ':445 ') listening sockets"
echo "  • NetBIOS ports: $(ss -tuln | grep -c ':137 ') broadcast sockets"
echo "  • Current IPs: $(ip addr show | grep "inet 192.168" | awk '{print $2}' | cut -d/ -f1 | paste -sd ", ")"
echo ""

echo "Next Health Check:"
systemctl status smb-health-check.timer --no-pager | grep "Trigger:"
echo ""

echo "✅ SMB shares are now configured for 24/7 availability!"
echo ""
echo "To manually check status:"
echo "  sudo systemctl status smb.service"
echo "  journalctl -u smb-health-check.service -f"
echo ""
echo "To view health check logs:"
echo "  tail -f /var/log/smb-health-check.log"
echo ""
