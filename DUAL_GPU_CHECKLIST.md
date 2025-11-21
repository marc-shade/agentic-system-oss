# Dual GPU Setup Checklist
**Mac Pro 5,1: GT 120 (Display) + GTX 680 (Compute)**

---

## ✅ Phase 1: Restore Display Functionality - COMPLETE

**Completed**:
- ✅ Removed wrong NVIDIA driver (580.xx - too new!)
- ✅ Un-blacklisted nouveau driver
- ✅ Rebuilt initramfs
- ✅ Confirmed linux-firmware installed

**Next**: Reboot to activate nouveau on GTX 680

---

## 🔄 Phase 2: Reboot and Verify - IN PROGRESS

**Command**:
```bash
sudo reboot
```

**After Reboot - Verify**:
```bash
# 1. Check both GPUs detected
lspci | grep -i vga

# Expected:
# 0a:00.0 VGA compatible controller: NVIDIA Corporation GK104 [GeForce GTX 680]

# 2. Check nouveau is loaded
lsmod | grep nouveau

# Expected: nouveau module loaded

# 3. Check both monitors working
# Visual check: Can you see this text on both monitors?
```

**Success Criteria**:
- ✅ System boots
- ✅ GTX 680 detected
- ✅ Nouveau driver loaded
- ✅ Both monitors working

---

## 🔌 Phase 3: Install GT 120 Hardware - PENDING

**ONLY DO THIS AFTER REBOOT WHEN DISPLAYS ARE WORKING!**

**Physical Installation Steps**:

1. **Power off completely**:
   ```bash
   sudo shutdown -h now
   ```
   Wait for full shutdown, then unplug power cable

2. **Open Mac Pro case**:
   - Lift latch on back
   - Remove side panel

3. **Install GT 120**:
   - Ground yourself (touch metal chassis)
   - Install GT 120 in **Slot 2** (second from top)
   - Secure with screw
   - GT 120 usually doesn't need aux power

4. **Connect monitors**:
   - **DISCONNECT both monitors from GTX 680**
   - **CONNECT both monitors to GT 120**
   - This is critical!

5. **Leave GTX 680**:
   - Keep in Slot 1
   - No monitors connected to it
   - It will be compute-only

6. **Close case and power on**

**Slot Layout**:
```
┌──────────────────────────────┐
│ Slot 1: GTX 680 (no display)│ ← Keep here
│ Slot 2: GT 120 (2 monitors) │ ← Install here
│ Slot 3: Empty               │
│ Slot 4: Empty               │
└──────────────────────────────┘
```

---

## 🚀 Phase 4: Boot with Both GPUs - PENDING

**After installing GT 120 and reconnecting power**:

1. Power on Mac Pro

2. Verify both GPUs detected:
   ```bash
   lspci | grep -i vga
   ```

   Expected output:
   ```
   0a:00.0 VGA compatible controller: NVIDIA Corporation GK104 [GeForce GTX 680]
   0b:00.0 VGA compatible controller: NVIDIA Corporation GT120 [GeForce GT 120]
   ```
   (Bus IDs may vary)

3. Check displays:
   ```bash
   # Install xrandr if needed
   sudo dnf install -y xorg-x11-server-utils

   # Check connected displays
   xrandr --query
   ```

4. Verify both monitors working on GT 120

**Success Criteria**:
- ✅ Both GPUs show in lspci
- ✅ Both monitors working
- ✅ Display on GT 120 (nouveau)
- ✅ GTX 680 present but not used for display

---

## ⚙️ Phase 5: Configure Displays (Optional) - PENDING

**If monitor layout needs adjustment**:

```bash
# List outputs
xrandr --listmonitors

# Example: Set primary and position
xrandr --output DVI-I-1 --primary --auto
xrandr --output DVI-I-2 --right-of DVI-I-1 --auto
```

**Make permanent** (choose one):
- GNOME Settings → Displays → Arrange → Apply
- Or create `~/.xprofile` with xrandr commands

---

## 🎯 Phase 6: Configure GTX 680 for Compute (Optional) - PENDING

**ONLY IF you need local CUDA! Otherwise skip this!**

**Decision Point**:
- ✅ Skip this: Just use Kaggle GPU (recommended!)
- ⚠️ Do this: Need local CUDA for quick tests

**If proceeding**:
```bash
sudo /tmp/configure_compute_gtx680.sh
```

This will:
1. Install NVIDIA 470.xx driver (if available)
2. Configure X server to use GT 120 for display
3. Configure GTX 680 for compute-only
4. Wait for kernel module to build
5. Rebuild initramfs
6. Reboot

**After reboot**:
```bash
nvidia-smi  # Should show GTX 680
```

---

## 🧪 Phase 7: Final Testing - PENDING

### Test 1: Display Stability
- ✅ Both monitors working?
- ✅ Can move windows between monitors?
- ✅ No flickering or artifacts?

### Test 2: GPU Detection
```bash
lspci | grep -i vga
# Should show both GPUs

lsmod | grep -E "nouveau|nvidia"
# Should show appropriate drivers
```

### Test 3: CUDA (if NVIDIA driver installed)
```bash
nvidia-smi
# Should show GTX 680 with 2GB VRAM

# Test PyTorch
python3 -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```

---

## 📋 Quick Reference Commands

### Check GPU Status
```bash
# List all GPUs
lspci | grep -i vga

# Check loaded drivers
lsmod | grep -E "nouveau|nvidia"

# Check displays
xrandr --query
```

### Check NVIDIA Status (if installed)
```bash
nvidia-smi
modinfo nvidia | grep version
```

### Troubleshooting
```bash
# If displays break, boot to recovery and run:
sudo rm /etc/X11/xorg.conf.d/20-dual-gpu.conf
sudo /tmp/restore_displays.sh
sudo reboot

# Check X server logs
sudo journalctl -xe | grep -i xorg

# Check kernel messages
sudo dmesg | grep -i "nvidia\|nouveau" | tail -30
```

---

## 📊 Current Status

**Phase 1**: ✅ COMPLETE
**Phase 2**: 🔄 READY TO REBOOT
**Phase 3**: ⏸️ WAITING (install GT 120 after reboot)
**Phase 4**: ⏸️ WAITING (boot with both GPUs)
**Phase 5**: ⏸️ WAITING (optional display config)
**Phase 6**: ⏸️ WAITING (optional NVIDIA for GTX 680)
**Phase 7**: ⏸️ WAITING (final testing)

---

## 🎯 What to Do Right Now

**IMMEDIATE**:
```bash
sudo reboot
```

**AFTER REBOOT**:
1. Verify both monitors working
2. Check `lspci | grep -i vga` shows GTX 680
3. Report back status
4. Then proceed with GT 120 physical installation

---

**Files Created**:
- ✅ `/tmp/restore_displays.sh` (used)
- ✅ `/tmp/configure_compute_gtx680.sh` (for later)
- ✅ `/home/marc/agentic-system/DUAL_GPU_SETUP_GUIDE.md` (full guide)
- ✅ `/home/marc/agentic-system/GPU_UPGRADE_ANALYSIS.md` (analysis)
- ✅ `/home/marc/agentic-system/DUAL_GPU_CHECKLIST.md` (this file)

**Ready to reboot!** 🚀
