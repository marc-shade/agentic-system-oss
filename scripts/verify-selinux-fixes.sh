#!/bin/bash
# Post-Reboot Verification Script
# Run this after reboot to verify all SELinux fixes

echo "═══════════════════════════════════════════════════════════════════"
echo "    POST-REBOOT SELINUX VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

echo "1. FAILED SERVICES:"
sudo systemctl --failed
echo ""

echo "2. SELINUX DENIAL COUNT (last 30 minutes):"
DENIALS=$(sudo ausearch -m avc -ts recent 2>/dev/null | grep denied | wc -l)
echo "Total denials: $DENIALS"
if [ "$DENIALS" -lt 10 ]; then
    echo "✓ Minimal denials (acceptable)"
else
    echo "⚠ High denial count - review needed"
fi
echo ""

echo "3. CRITICAL SERVICES STATUS:"
for service in smb.service builder-node-api.service vncserver@:2.service ramdisk-init.service; do
    if systemctl is-active --quiet $service; then
        echo "✓ $service - ACTIVE"
    else
        echo "✗ $service - INACTIVE/FAILED"
    fi
done
echo ""

echo "4. DOCKER CONTAINERS:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "redis|qdrant|n8n"
echo ""

echo "5. RAMDISK MOUNT:"
if mount | grep -q ramdisk; then
    echo "✓ Ramdisk mounted"
    mount | grep ramdisk
else
    echo "✗ Ramdisk NOT mounted"
fi
echo ""

echo "6. SELINUX CONTEXTS:"
echo "Mount point:"
ls -ldZ /mnt/agentic-system
echo ""
echo "Scripts (sample):"
ls -lZ /mnt/agentic-system/scripts/*.sh | head -3
echo ""
echo "Whisper server:"
ls -lZ /mnt/agentic-system/voice-cache/whisper.cpp/build/bin/whisper-server
echo ""

echo "7. SMB HEALTH CHECK LOG:"
tail -5 /var/log/smb-health-check.log
echo ""

echo "8. RECENT SELINUX DENIALS (last 5):"
sudo ausearch -m avc -ts recent 2>/dev/null | grep denied | tail -5 || echo "✓ No recent denials"
echo ""

echo "═══════════════════════════════════════════════════════════════════"
