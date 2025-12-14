#!/bin/bash
# Mount macpro51 agentic-system SMB share
MOUNT_POINT=/Volumes/agentic-macpro51

if mount | grep -q 'agentic-system'; then
    echo 'Already mounted'
else
    mkdir -p $MOUNT_POINT 2>/dev/null || true
    open 'smb://marc@macpro51.local/agentic-system'
    echo 'Opening Finder to mount - enter password if prompted'
fi
