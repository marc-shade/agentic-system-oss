#!/bin/bash
#
# SMB Health Check - Ensures network shares are always available
# Run this periodically to verify and auto-fix SMB share availability
#

LOG_FILE="/var/log/smb-health-check.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if SMB service is running
if ! systemctl is-active --quiet smb.service; then
    log "ERROR: SMB service is not running! Attempting restart..."
    sudo systemctl start smb.service
    sleep 2
    if systemctl is-active --quiet smb.service; then
        log "SUCCESS: SMB service restarted"
    else
        log "CRITICAL: Failed to restart SMB service!"
        exit 1
    fi
else
    log "OK: SMB service is active"
fi

# Check if NetBIOS service is running
if ! systemctl is-active --quiet nmb.service; then
    log "ERROR: NetBIOS service is not running! Attempting restart..."
    sudo systemctl start nmb.service
    sleep 2
    if systemctl is-active --quiet nmb.service; then
        log "SUCCESS: NetBIOS service restarted"
    else
        log "WARNING: NetBIOS service failed to start (non-critical)"
    fi
else
    log "OK: NetBIOS service is active"
fi

# Check if Avahi is running for network discovery
if ! systemctl is-active --quiet avahi-daemon.service; then
    log "WARNING: Avahi daemon not running! Starting..."
    sudo systemctl start avahi-daemon.service
fi

# Verify share is accessible locally
# Use authenticated test since share requires valid users
if echo "macpro51" | smbclient -L localhost -U marc 2>&1 | grep -q "agentic-system"; then
    log "OK: Share 'agentic-system' is visible locally"
else
    log "ERROR: Share 'agentic-system' not visible! Restarting SMB..."
    sudo systemctl restart smb.service nmb.service
    sleep 3
    if echo "macpro51" | smbclient -L localhost -U marc 2>&1 | grep -q "agentic-system"; then
        log "SUCCESS: Share recovered after restart"
    else
        log "CRITICAL: Share still not visible after restart!"
        exit 1
    fi
fi

# Check if SMB ports are listening
if ss -tuln | grep -q ":445 "; then
    log "OK: SMB port 445 is listening"
else
    log "ERROR: SMB port 445 not listening!"
    exit 1
fi

# Verify SELinux context
CONTEXT=$(ls -Zd /mnt/agentic-system | awk '{print $1}')
if echo "$CONTEXT" | grep -q "samba_share_t"; then
    log "OK: SELinux context is correct (samba_share_t)"
else
    log "WARNING: SELinux context may be incorrect: $CONTEXT"
    log "Attempting to fix..."
    sudo semanage fcontext -a -t samba_share_t "/mnt/agentic-system(/.*)?"
    sudo restorecon -R /mnt/agentic-system
    log "SELinux context restored"
fi

# Verify SELinux boolean
if getsebool samba_export_all_rw | grep -q "on"; then
    log "OK: SELinux boolean samba_export_all_rw is enabled"
else
    log "WARNING: SELinux boolean not set, fixing..."
    sudo setsebool -P samba_export_all_rw on
    log "SELinux boolean enabled"
fi

log "=== Health check complete: All systems operational ==="
exit 0
