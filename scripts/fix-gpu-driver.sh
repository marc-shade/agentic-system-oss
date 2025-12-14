#!/bin/bash
# Fix GTX 680 GPU Driver - Switch from Nouveau to NVIDIA
# Node: macpro51 (Fedora 43)
# Date: 2025-11-24

set -e

if [ "$EUID" -ne 0 ]; then
   echo "❌ Please run with sudo"
   exit 1
fi

echo "🎮 GTX 680 GPU Driver Fix"
echo "========================"
echo ""
echo "This will switch from Nouveau to NVIDIA proprietary driver (470xx)"
echo ""

# Check current status
echo "📊 Current GPU Status:"
lspci | grep -i vga
echo ""

# Check if NVIDIA packages installed
if ! rpm -qa | grep -q "nvidia-470xx"; then
    echo "❌ NVIDIA 470xx drivers not installed!"
    echo ""
    echo "Installing NVIDIA 470xx drivers..."
    dnf install -y akmod-nvidia-470xx xorg-x11-drv-nvidia-470xx-cuda
else
    echo "✅ NVIDIA 470xx drivers already installed"
fi

echo ""
echo "📝 Blacklisting Nouveau driver..."

# Create blacklist file
cat > /etc/modprobe.d/blacklist-nouveau.conf << 'EOF'
# Blacklist Nouveau for NVIDIA proprietary driver
blacklist nouveau
options nouveau modeset=0
EOF

echo "✅ Nouveau blacklisted"
echo ""

# Rebuild initramfs
echo "🔧 Rebuilding initramfs..."
dracut --force

echo ""
echo "🔧 Unloading Nouveau module..."
rmmod nouveau 2>/dev/null || echo "Nouveau not loaded (OK)"

echo ""
echo "✅ GPU driver fix applied!"
echo ""
echo "⚠️  REBOOT REQUIRED for changes to take effect"
echo ""
echo "After reboot:"
echo "1. Run: nvidia-smi"
echo "2. Should see GTX 680 listed"
echo "3. Run: /mnt/agentic-system/scripts/kaggle-setup.sh"
echo ""
echo "Reboot now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
    reboot
else
    echo "Please reboot manually when ready: sudo reboot"
fi
