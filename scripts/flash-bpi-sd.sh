#!/bin/bash
# Flash BPI-M2 Berry SD Card
# Automates downloading and flashing Armbian to microSD

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo "=========================================="
echo "BPI-M2 Berry SD Card Flasher"
echo "=========================================="
echo

# Recommended image
IMAGE_NAME="Armbian_22.11.0-trunk_Banana_Pi_BPI-M2_Berry_bullseye_edge_6.0.9.img.xz"
GDRIVE_ID="1vyK13DB2Z1OMjGE9Wd1XHYIMFPZ8UuZI"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    info "Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    info "Detected: Linux"
else
    error "Unsupported OS: $OSTYPE"
fi

# Check for required tools
check_tools() {
    info "Checking required tools..."

    if [[ "$OS" == "macos" ]]; then
        if ! command -v diskutil &> /dev/null; then
            error "diskutil not found (should be built-in on macOS)"
        fi
    else
        if ! command -v lsblk &> /dev/null; then
            error "lsblk not found. Install: sudo apt install util-linux"
        fi
    fi

    success "All required tools available"
}

# Download image
download_image() {
    info "Downloading Armbian image..."

    if [[ -f "$IMAGE_NAME" ]]; then
        info "Image already exists: $IMAGE_NAME"
        read -p "Re-download? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return
        fi
    fi

    warn "Manual download required from Google Drive"
    echo
    echo "1. Open this URL in your browser:"
    echo "   https://drive.google.com/file/d/$GDRIVE_ID/view"
    echo
    echo "2. Click 'Download' button"
    echo "3. Save to: $(pwd)"
    echo "4. Filename should be: $IMAGE_NAME"
    echo
    read -p "Press Enter when download is complete..."

    if [[ ! -f "$IMAGE_NAME" ]]; then
        error "Image file not found: $IMAGE_NAME"
    fi

    success "Image ready: $IMAGE_NAME"
}

# Find SD card
find_sd_card() {
    info "Detecting SD card..."
    echo

    if [[ "$OS" == "macos" ]]; then
        diskutil list
        echo
        warn "Identify your SD card from the list above"
        warn "Usually something like /dev/disk2 or /dev/disk4"
        warn "Look for the size matching your SD card"
        echo
        read -p "Enter SD card device (e.g., disk2): " DISK
        SD_CARD="/dev/$DISK"

        # Verify
        if [[ ! -e "$SD_CARD" ]]; then
            error "Device not found: $SD_CARD"
        fi

        diskutil info "$DISK" | grep -E "Device Node:|Disk Size:"

    else
        lsblk -p
        echo
        warn "Identify your SD card from the list above"
        warn "Usually something like /dev/sdb or /dev/mmcblk0"
        warn "Look for the size matching your SD card"
        echo
        read -p "Enter SD card device (e.g., /dev/sdb): " SD_CARD

        # Verify
        if [[ ! -e "$SD_CARD" ]]; then
            error "Device not found: $SD_CARD"
        fi

        lsblk -o NAME,SIZE,TYPE,MOUNTPOINT "$SD_CARD"
    fi

    echo
    error "⚠️  WARNING: This will ERASE ALL DATA on $SD_CARD ⚠️"
    echo
    read -p "Are you ABSOLUTELY SURE? Type 'yes' to continue: " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        error "Aborted by user"
    fi
}

# Flash image
flash_image() {
    info "Flashing image to $SD_CARD..."
    echo
    info "This will take 5-10 minutes..."

    if [[ "$OS" == "macos" ]]; then
        # Unmount all partitions
        info "Unmounting partitions..."
        diskutil unmountDisk "$SD_CARD" || true

        # Extract and flash in one go
        info "Extracting and flashing..."

        # Use rdisk for faster writing
        RDISK=$(echo "$SD_CARD" | sed 's/disk/rdisk/')

        if command -v pv &> /dev/null; then
            # With progress bar
            xz -dc "$IMAGE_NAME" | pv | sudo dd of="$RDISK" bs=4m conv=sync
        else
            # Without progress bar
            warn "Install 'pv' for progress bar: brew install pv"
            xz -dc "$IMAGE_NAME" | sudo dd of="$RDISK" bs=4m conv=sync status=progress
        fi

        # Eject
        info "Syncing and ejecting..."
        sync
        diskutil eject "$SD_CARD"

    else
        # Unmount all partitions
        info "Unmounting partitions..."
        sudo umount ${SD_CARD}* 2>/dev/null || true

        # Extract and flash
        info "Extracting and flashing..."

        if command -v pv &> /dev/null; then
            # With progress bar
            xz -dc "$IMAGE_NAME" | pv | sudo dd of="$SD_CARD" bs=4M conv=fsync
        else
            # Without progress bar
            warn "Install 'pv' for progress bar: sudo apt install pv"
            xz -dc "$IMAGE_NAME" | sudo dd of="$SD_CARD" bs=4M conv=fsync status=progress
        fi

        # Sync and eject
        info "Syncing and ejecting..."
        sync
        sudo eject "$SD_CARD"
    fi

    success "Flashing complete!"
}

# Print next steps
print_next_steps() {
    echo
    echo "=========================================="
    echo "SD Card Ready!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo
    echo "1. Remove SD card from your computer"
    echo "2. Insert into BPI-M2 Berry"
    echo "3. Connect Ethernet cable"
    echo "4. Connect 5V/2A power supply"
    echo "5. Wait 2-3 minutes for first boot"
    echo
    echo "6. Find the board's IP address:"
    echo "   - Check your router's DHCP leases"
    echo "   - Or: nmap -sn 192.168.1.0/24"
    echo "   - Or: avahi-browse -t _ssh._tcp"
    echo
    echo "7. SSH into the board:"
    echo "   ssh root@192.168.1.XXX"
    echo "   Password: 1234"
    echo
    echo "8. First login will prompt:"
    echo "   - Change root password"
    echo "   - Create user 'marc'"
    echo "   - Set marc's password"
    echo
    echo "9. Then run the setup script:"
    echo "   ./setup-bpi-sentinel.sh"
    echo
    echo "=========================================="
}

# Main flow
main() {
    check_tools
    download_image
    find_sd_card
    flash_image
    print_next_steps
}

main
