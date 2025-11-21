# Mac Pro 5,1 Dual GPU Setup Guide
## GT 120 (Display) + GTX 680 (Compute)

**System**: Mac Pro 5,1 (2010-2012)
**Goal**: GT 120 handles displays, GTX 680 for GPU compute
**Status**: Step-by-step implementation

---

## 📋 Overview

**Current Situation**:
- ❌ GTX 680 has wrong NVIDIA driver (generic, not 470.xx legacy)
- ❌ Nouveau is blacklisted but still loaded (broken state)
- ❌ Lost second monitor

**Solution**:
- GT 120 in Slot 2 → Primary display (nouveau driver, stable)
- GTX 680 in Slot 1 → Compute-only (NVIDIA driver, no display)
- Both monitors connected to GT 120
- GTX 680 available via CUDA for compute tasks

---

## 🔧 Phase 1: Restore Display Functionality

**Goal**: Get system booting with working displays before installing GT 120

**Run**: `/tmp/restore_displays.sh`

This will:
1. Remove incorrect NVIDIA driver packages
2. Un-blacklist nouveau driver
3. Rebuild initramfs
4. Install nouveau firmware

**Then**: Reboot

**Expected Result**: GTX 680 works with nouveau, both monitors functional

---

## 🔌 Phase 2: Physical GT 120 Installation

**IMPORTANT**: Do this AFTER Phase 1 reboot when displays are working!

### Power Off Completely
```bash
sudo shutdown -h now
```
Wait for system to fully power off, then unplug power cable.

### Install GT 120

**Mac Pro 5,1 PCIe Slot Layout** (from top to bottom):
```
Slot 1: x16 (currently GTX 680) ← KEEP HERE
Slot 2: x16 (empty)             ← INSTALL GT 120 HERE
Slot 3: x4  (empty)
Slot 4: x4  (empty)
```

**Steps**:
1. Open Mac Pro case (lift latch, remove side panel)
2. Ground yourself (touch metal chassis)
3. Install GT 120 in **Slot 2** (second from top)
4. Secure with screw
5. Connect power if needed (GT 120 may not need aux power)
6. **IMPORTANT**: Connect BOTH monitors to GT 120 ports
7. Leave GTX 680 in Slot 1 (NO monitors connected to it!)
8. Close case
9. Plug in power cable

### GT 120 Specifications
- Released: 2008
- VRAM: 256 MB
- Ports: Usually 2x DVI or 1x DVI + 1x Mini DisplayPort
- Power: Usually no aux power required (draws from slot)
- Driver: nouveau (open-source) works perfectly

---

## 🚀 Phase 3: Boot with Both GPUs

**Power on the Mac Pro**

**What Should Happen**:
1. BIOS/EFI uses GT 120 as primary (Slot 2)
2. Boot screen appears on GT 120
3. Fedora boots
4. Both monitors work via GT 120 (nouveau driver)
5. GTX 680 detected but not used for display

**Check Detection**:
```bash
lspci | grep -i vga
```

**Expected Output**:
```
0a:00.0 VGA compatible controller: NVIDIA Corporation GK104 [GeForce GTX 680]
0b:00.0 VGA compatible controller: NVIDIA Corporation GT120 [GeForce GT 120]
```

**Check Drivers**:
```bash
lsmod | grep -E "nouveau|nvidia"
```

**Expected**:
```
nouveau   (loaded for both GPUs - that's fine for now!)
```

---

## ⚙️ Phase 4: Configure Display Setup

### Verify Both Monitors Working

```bash
# Install xrandr if not present
sudo dnf install -y xorg-x11-server-utils

# Check connected displays
xrandr --query
```

**Expected**: Both monitors shown as connected to nouveau outputs

### Set Monitor Layout (if needed)

```bash
# List outputs
xrandr --listmonitors

# If monitors need positioning (example):
xrandr --output DVI-I-1 --primary --auto
xrandr --output DVI-I-2 --right-of DVI-I-1 --auto
```

Save to `~/.xprofile` or display settings for persistence.

---

## 🎯 Phase 5: Configure GTX 680 for Compute-Only

**Goal**: Install NVIDIA driver on GTX 680 for CUDA, but NOT for display

### Option A: Keep It Simple (Recommended)

**Just use nouveau for both GPUs**:
- ✅ Displays work
- ✅ No driver conflicts
- ❌ No CUDA on GTX 680 (but you're using Kaggle anyway!)

**If this is fine, STOP HERE!** You're done! 🎉

---

### Option B: NVIDIA Driver on GTX 680 Only (Advanced)

**WARNING**: This is complex and may break again!

**Only proceed if you need local CUDA for testing.**

**Requirements**:
- X server must use GT 120 (nouveau) for display
- GTX 680 uses NVIDIA driver but NO display outputs
- Need to configure Xorg to explicitly use GT 120

**Script**: `/tmp/configure_compute_gtx680.sh` (created below)

This involves:
1. Installing NVIDIA 470.xx driver (if available)
2. Creating Xorg config to force GT 120 as display GPU
3. Blacklisting NVIDIA from binding to GT 120
4. Allowing nouveau on GT 120, NVIDIA on GTX 680

**After configuration**:
```bash
# Check CUDA availability
nvidia-smi  # Should show GTX 680
```

---

## 🧪 Phase 6: Testing

### Test 1: Display Functionality
```bash
# Both monitors working?
xrandr --query

# Can you move windows between monitors?
# Can you set wallpapers independently?
```

**Expected**: ✅ All working smoothly on GT 120

### Test 2: GTX 680 Detection
```bash
lspci | grep GTX
nvidia-smi  # If NVIDIA driver installed
```

**Expected**: GTX 680 detected, available for compute

### Test 3: CUDA Test (if NVIDIA driver installed)
```bash
# Install CUDA toolkit
sudo dnf install -y cuda-toolkit

# Test CUDA
cat > /tmp/test_cuda.py << 'EOF'
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Device: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
EOF

python3 /tmp/test_cuda.py
```

**Expected**:
```
CUDA available: True
Device: GeForce GTX 680
VRAM: 2.0 GB
```

---

## 🎨 Display Configuration Persistence

### Make Monitor Layout Permanent

**Method 1: GNOME Settings** (if using GNOME)
- Settings → Displays
- Arrange monitors
- Click "Apply"
- Changes saved automatically

**Method 2: xrandr script** (for any desktop)
```bash
# Create startup script
cat > ~/.config/autostart/monitor-setup.sh << 'EOF'
#!/bin/bash
xrandr --output DVI-I-1 --primary --auto
xrandr --output DVI-I-2 --right-of DVI-I-1 --auto
EOF

chmod +x ~/.config/autostart/monitor-setup.sh
```

**Method 3: Xorg config** (system-wide)
Create `/etc/X11/xorg.conf.d/10-monitors.conf`

---

## 📊 Performance Expectations

### Display (GT 120)
- ✅ 2D desktop: Perfect
- ✅ Video playback: Fine for 1080p
- ✅ Multi-monitor: No issues
- ❌ Gaming: Not recommended
- ❌ 4K: Probably struggles

### Compute (GTX 680)
- ✅ CUDA 11.4 compatible
- ✅ 2GB VRAM (limited but usable)
- ✅ 3.1 TFLOPS FP32
- ⚠️ Still 1000x slower than Kaggle T4
- ⚠️ Use for quick local tests only

---

## 🔍 Troubleshooting

### Problem: No display after installing GT 120

**Fix**:
1. Power off completely
2. Remove GT 120
3. Reconnect monitor to GTX 680
4. Boot and run restore script again
5. Check GT 120 is properly seated

### Problem: Only one monitor working

**Fix**:
```bash
xrandr --query  # Check which outputs are connected
xrandr --output <OUTPUT2> --auto  # Enable second monitor
```

### Problem: GTX 680 not detected

**Fix**:
```bash
lspci | grep NVIDIA  # Should show both GPUs
sudo lspci -vvv -s 0a:00.0  # Detailed GTX 680 info
```

### Problem: X server won't start

**Fix**:
```bash
# Check X server logs
sudo journalctl -xe | grep -i "x server\|xorg"

# Try removing any custom Xorg configs
sudo rm /etc/X11/xorg.conf
sudo rm /etc/X11/xorg.conf.d/90-nvidia.conf
```

### Problem: NVIDIA driver conflicts

**Fix**: Revert to nouveau-only setup
```bash
sudo /tmp/restore_displays.sh
sudo reboot
```

---

## ✅ Success Criteria

**Phase 1 Complete**:
- ✅ System boots
- ✅ Both monitors working on GTX 680 (nouveau)

**Phase 2 Complete**:
- ✅ GT 120 physically installed
- ✅ Both monitors connected to GT 120

**Phase 3 Complete**:
- ✅ System boots with both GPUs
- ✅ Both GPUs detected by `lspci`

**Phase 4 Complete**:
- ✅ Both monitors working on GT 120
- ✅ Display layout configured

**Phase 5 Complete** (Optional):
- ✅ GTX 680 has NVIDIA driver
- ✅ `nvidia-smi` shows GTX 680
- ✅ GT 120 still handles display

**Phase 6 Complete**:
- ✅ All tests pass
- ✅ Stable configuration

---

## 🎯 Final Configuration

**Ideal Setup**:
```
┌─────────────────────────────────────┐
│      Mac Pro 5,1 (Fedora 43)       │
├─────────────────────────────────────┤
│                                     │
│  Slot 1: GTX 680 (Compute)         │
│    - Driver: NVIDIA 470.xx          │
│    - Purpose: CUDA compute          │
│    - Display: NONE                  │
│    - VRAM: 2GB                      │
│                                     │
│  Slot 2: GT 120 (Display)          │
│    - Driver: nouveau                │
│    - Purpose: Display output        │
│    - Monitors: 2x connected         │
│    - VRAM: 256MB                    │
│                                     │
└─────────────────────────────────────┘
```

**User Experience**:
- All desktop work on GT 120 (stable, no conflicts)
- CUDA apps automatically use GTX 680
- No display driver issues
- Best of both worlds!

---

## 📝 Next Steps After Setup

1. **Update SYSTEM-CATALOG.md** with new GPU config
2. **Test PyTorch/TensorFlow** with CUDA
3. **Continue with Kaggle GPU** for CAFA-6 (still the better option!)
4. **Use local GTX 680** only for quick tests

---

**Remember**: This dual GPU setup is a workaround. For serious ML work in CAFA-6, **still use Kaggle's free T4 GPU** - it's faster and has 8x more VRAM! 🚀
