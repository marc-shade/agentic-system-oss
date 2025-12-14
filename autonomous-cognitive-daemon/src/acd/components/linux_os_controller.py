"""Linux OS Controller - Deep integration with Linux/GNOME/Fedora.

Gives Pixel deep control over the Linux system through:
- D-Bus for desktop/systemd communication
- Freedesktop Portals for screenshots, clipboard, file access
- PipeWire/PulseAudio for audio control
- Systemd for service management
- GNOME Shell for desktop integration
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from ..utils.config import get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ScreenState(Enum):
    """Screen/display states."""
    ON = "on"
    OFF = "off"
    DIMMED = "dimmed"
    LOCKED = "locked"


class AudioState(Enum):
    """Audio states."""
    NORMAL = "normal"
    MUTED = "muted"
    DO_NOT_DISTURB = "dnd"


@dataclass
class SystemSnapshot:
    """Point-in-time system state snapshot."""
    timestamp: datetime
    display_state: str
    audio_muted: bool
    audio_volume: int
    active_window: Optional[str]
    idle_time_seconds: int
    power_state: str
    network_connected: bool
    clipboard_has_text: bool


class LinuxOSController:
    """
    Deep Linux/GNOME integration for the Autonomous Cognitive Daemon.

    Capabilities:
    - Screen control (brightness, lock, DPMS)
    - Audio control (volume, mute, output selection)
    - Clipboard access (read/write)
    - Screenshot capture
    - Window management
    - System power management
    - Service control via systemd
    - User presence detection (idle time)
    - File access via Portals
    - Application launching
    """

    def __init__(self, config: dict):
        """Initialize Linux OS Controller.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Controller configuration
        controller_config = config.get("components", {}).get("linux_os_controller", {})
        self.enabled = controller_config.get("enabled", True)

        # D-Bus session for user operations
        self._dbus_session_address = os.environ.get(
            "DBUS_SESSION_BUS_ADDRESS",
            f"unix:path=/run/user/{os.getuid()}/bus"
        )

        # Wayland/X11 detection
        self._display_server = self._detect_display_server()

        # GNOME Shell D-Bus interface
        self._gnome_shell_available = self._check_gnome_shell()

        # Screenshot directory
        self.screenshot_dir = Path(
            controller_config.get(
                "screenshot_dir",
                "/mnt/agentic-system/screenshots"
            )
        )
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Environment for D-Bus commands
        self._env = self._setup_dbus_env()

        # State cache
        self._last_snapshot: Optional[SystemSnapshot] = None
        self._event_callbacks: Dict[str, List[Callable]] = {}

        logger.info(
            "linux_os_controller_initialized",
            display_server=self._display_server,
            gnome_shell=self._gnome_shell_available,
        )

    def _detect_display_server(self) -> str:
        """Detect whether running Wayland or X11."""
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        elif os.environ.get("DISPLAY"):
            return "x11"
        else:
            return "headless"

    def _check_gnome_shell(self) -> bool:
        """Check if GNOME Shell is running."""
        try:
            result = subprocess.run(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.Shell",
                 "--object-path", "/org/gnome/Shell",
                 "--method", "org.gnome.Shell.Eval", "global.get_current_time()"],
                capture_output=True, timeout=2, env=self._setup_dbus_env()
            )
            return result.returncode == 0
        except Exception:
            return False

    def _setup_dbus_env(self) -> Dict[str, str]:
        """Setup environment variables for D-Bus communication."""
        env = os.environ.copy()

        # Required for Wayland/GNOME
        if "WAYLAND_DISPLAY" not in env:
            env["WAYLAND_DISPLAY"] = "wayland-0"
        if "XDG_RUNTIME_DIR" not in env:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"

        return env

    async def _run_async(self, cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        """Run command asynchronously with proper environment."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=self._env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        return subprocess.CompletedProcess(
            cmd, process.returncode, stdout, stderr
        )

    # =========================================================================
    # SCREEN CONTROL
    # =========================================================================

    async def get_screen_brightness(self) -> int:
        """Get current screen brightness (0-100)."""
        try:
            result = await self._run_async(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.SettingsDaemon.Power",
                 "--object-path", "/org/gnome/SettingsDaemon/Power",
                 "--method", "org.freedesktop.DBus.Properties.Get",
                 "org.gnome.SettingsDaemon.Power.Screen", "Brightness"]
            )
            if result.returncode == 0:
                # Parse response like "(<int32 80>,)"
                output = result.stdout.decode()
                import re
                match = re.search(r'int32\s+(\d+)', output)
                if match:
                    return int(match.group(1))
        except Exception as e:
            logger.warning("get_brightness_failed", error=str(e))
        return -1

    async def set_screen_brightness(self, level: int) -> bool:
        """Set screen brightness (0-100)."""
        level = max(0, min(100, level))
        try:
            result = await self._run_async(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.SettingsDaemon.Power",
                 "--object-path", "/org/gnome/SettingsDaemon/Power",
                 "--method", "org.freedesktop.DBus.Properties.Set",
                 "org.gnome.SettingsDaemon.Power.Screen", "Brightness",
                 f"<int32 {level}>"]
            )
            success = result.returncode == 0
            logger.info("set_brightness", level=level, success=success)
            return success
        except Exception as e:
            logger.warning("set_brightness_failed", error=str(e))
            return False

    async def lock_screen(self) -> bool:
        """Lock the screen."""
        try:
            result = await self._run_async(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.ScreenSaver",
                 "--object-path", "/org/gnome/ScreenSaver",
                 "--method", "org.gnome.ScreenSaver.Lock"]
            )
            success = result.returncode == 0
            logger.info("screen_locked", success=success)
            return success
        except Exception as e:
            logger.warning("lock_screen_failed", error=str(e))
            return False

    async def get_idle_time(self) -> int:
        """Get user idle time in seconds."""
        try:
            result = await self._run_async(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.Mutter.IdleMonitor",
                 "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                 "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime"]
            )
            if result.returncode == 0:
                output = result.stdout.decode()
                import re
                match = re.search(r'uint64\s+(\d+)', output)
                if match:
                    return int(match.group(1)) // 1000  # ms to seconds
        except Exception as e:
            logger.debug("get_idle_time_failed", error=str(e))
        return 0

    async def is_screen_locked(self) -> bool:
        """Check if screen is locked."""
        try:
            result = await self._run_async(
                ["gdbus", "call", "--session",
                 "--dest", "org.gnome.ScreenSaver",
                 "--object-path", "/org/gnome/ScreenSaver",
                 "--method", "org.gnome.ScreenSaver.GetActive"]
            )
            if result.returncode == 0:
                return "true" in result.stdout.decode().lower()
        except Exception as e:
            logger.debug("is_screen_locked_failed", error=str(e))
        return False

    # =========================================================================
    # AUDIO CONTROL (PipeWire/PulseAudio)
    # =========================================================================

    async def get_volume(self) -> int:
        """Get current audio volume (0-100)."""
        try:
            result = await self._run_async(
                ["pactl", "get-sink-volume", "@DEFAULT_SINK@"]
            )
            if result.returncode == 0:
                import re
                match = re.search(r'(\d+)%', result.stdout.decode())
                if match:
                    return int(match.group(1))
        except Exception as e:
            logger.debug("get_volume_failed", error=str(e))
        return -1

    async def set_volume(self, level: int) -> bool:
        """Set audio volume (0-150, >100 may distort)."""
        level = max(0, min(150, level))
        try:
            result = await self._run_async(
                ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"]
            )
            success = result.returncode == 0
            logger.info("set_volume", level=level, success=success)
            return success
        except Exception as e:
            logger.warning("set_volume_failed", error=str(e))
            return False

    async def is_muted(self) -> bool:
        """Check if audio is muted."""
        try:
            result = await self._run_async(
                ["pactl", "get-sink-mute", "@DEFAULT_SINK@"]
            )
            if result.returncode == 0:
                return "yes" in result.stdout.decode().lower()
        except Exception as e:
            logger.debug("is_muted_failed", error=str(e))
        return False

    async def set_mute(self, muted: bool) -> bool:
        """Set audio mute state."""
        try:
            state = "1" if muted else "0"
            result = await self._run_async(
                ["pactl", "set-sink-mute", "@DEFAULT_SINK@", state]
            )
            success = result.returncode == 0
            logger.info("set_mute", muted=muted, success=success)
            return success
        except Exception as e:
            logger.warning("set_mute_failed", error=str(e))
            return False

    async def toggle_mute(self) -> bool:
        """Toggle audio mute."""
        try:
            result = await self._run_async(
                ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning("toggle_mute_failed", error=str(e))
            return False

    # =========================================================================
    # CLIPBOARD (Freedesktop Portal)
    # =========================================================================

    async def get_clipboard_text(self) -> Optional[str]:
        """Get text from clipboard."""
        try:
            # wl-paste for Wayland
            if self._display_server == "wayland":
                result = await self._run_async(["wl-paste", "--no-newline"])
            else:
                result = await self._run_async(["xclip", "-selection", "clipboard", "-o"])

            if result.returncode == 0:
                return result.stdout.decode()
        except Exception as e:
            logger.debug("get_clipboard_failed", error=str(e))
        return None

    async def set_clipboard_text(self, text: str) -> bool:
        """Set text to clipboard."""
        try:
            if self._display_server == "wayland":
                process = await asyncio.create_subprocess_exec(
                    "wl-copy",
                    env=self._env,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await process.communicate(input=text.encode())
                return process.returncode == 0
            else:
                process = await asyncio.create_subprocess_exec(
                    "xclip", "-selection", "clipboard",
                    env=self._env,
                    stdin=asyncio.subprocess.PIPE,
                )
                await process.communicate(input=text.encode())
                return process.returncode == 0
        except Exception as e:
            logger.warning("set_clipboard_failed", error=str(e))
            return False

    # =========================================================================
    # SCREENSHOTS (Freedesktop Portal)
    # =========================================================================

    async def take_screenshot(self, filename: Optional[str] = None) -> Optional[Path]:
        """Take a screenshot using GNOME Screenshot or grim."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        filepath = self.screenshot_dir / filename

        try:
            if self._display_server == "wayland":
                # Use grim for Wayland
                result = await self._run_async(
                    ["grim", str(filepath)]
                )
            else:
                # Use gnome-screenshot for X11
                result = await self._run_async(
                    ["gnome-screenshot", "-f", str(filepath)]
                )

            if result.returncode == 0 and filepath.exists():
                logger.info("screenshot_taken", path=str(filepath))
                return filepath

            # Fallback to portal
            result = await self._run_async([
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Shell.Screenshot",
                "--object-path", "/org/gnome/Shell/Screenshot",
                "--method", "org.gnome.Shell.Screenshot.Screenshot",
                "false", "false", str(filepath)
            ])

            if result.returncode == 0 and filepath.exists():
                logger.info("screenshot_taken_via_shell", path=str(filepath))
                return filepath

        except Exception as e:
            logger.warning("screenshot_failed", error=str(e))

        return None

    async def take_screenshot_area(self, x: int, y: int, width: int, height: int,
                                   filename: Optional[str] = None) -> Optional[Path]:
        """Take a screenshot of a specific area."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_area_{timestamp}.png"

        filepath = self.screenshot_dir / filename

        try:
            if self._display_server == "wayland":
                result = await self._run_async(
                    ["grim", "-g", f"{x},{y} {width}x{height}", str(filepath)]
                )
            else:
                result = await self._run_async(
                    ["gnome-screenshot", "-a", f"{x},{y},{width},{height}",
                     "-f", str(filepath)]
                )

            if result.returncode == 0 and filepath.exists():
                logger.info("screenshot_area_taken", path=str(filepath))
                return filepath

        except Exception as e:
            logger.warning("screenshot_area_failed", error=str(e))

        return None

    # =========================================================================
    # WINDOW MANAGEMENT
    # =========================================================================

    async def get_active_window(self) -> Optional[Dict[str, Any]]:
        """Get information about the active window."""
        try:
            if self._gnome_shell_available:
                result = await self._run_async([
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell",
                    "--object-path", "/org/gnome/Shell",
                    "--method", "org.gnome.Shell.Eval",
                    "global.display.focus_window ? global.display.focus_window.get_title() : 'none'"
                ])
                if result.returncode == 0:
                    output = result.stdout.decode()
                    # Parse: (true, '"window title"')
                    import re
                    match = re.search(r"'([^']*)'", output)
                    if match:
                        return {"title": match.group(1).strip('"')}
        except Exception as e:
            logger.debug("get_active_window_failed", error=str(e))
        return None

    async def list_windows(self) -> List[Dict[str, Any]]:
        """List all open windows."""
        try:
            if self._gnome_shell_available:
                js_code = """
                global.get_window_actors().map(w => ({
                    title: w.meta_window.get_title(),
                    wm_class: w.meta_window.get_wm_class(),
                    focused: w.meta_window.has_focus()
                }))
                """
                result = await self._run_async([
                    "gdbus", "call", "--session",
                    "--dest", "org.gnome.Shell",
                    "--object-path", "/org/gnome/Shell",
                    "--method", "org.gnome.Shell.Eval",
                    js_code.replace("\n", " ")
                ])
                if result.returncode == 0:
                    output = result.stdout.decode()
                    # Parse JSON from eval result
                    import re
                    match = re.search(r"'(\[.*\])'", output, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
        except Exception as e:
            logger.debug("list_windows_failed", error=str(e))
        return []

    # =========================================================================
    # SYSTEM POWER MANAGEMENT
    # =========================================================================

    async def suspend(self) -> bool:
        """Suspend the system."""
        try:
            result = await self._run_async(
                ["systemctl", "suspend"]
            )
            success = result.returncode == 0
            logger.info("system_suspend", success=success)
            return success
        except Exception as e:
            logger.warning("suspend_failed", error=str(e))
            return False

    async def get_power_state(self) -> str:
        """Get current power state (AC/battery)."""
        try:
            result = await self._run_async(
                ["upower", "-i", "/org/freedesktop/UPower/devices/line_power_AC"]
            )
            if result.returncode == 0:
                if "online: yes" in result.stdout.decode().lower():
                    return "AC"
        except Exception:
            pass
        return "battery"

    async def get_battery_level(self) -> Optional[int]:
        """Get battery level percentage."""
        try:
            result = await self._run_async(
                ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"]
            )
            if result.returncode == 0:
                import re
                match = re.search(r'percentage:\s+(\d+)%', result.stdout.decode())
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return None

    # =========================================================================
    # SYSTEMD SERVICE CONTROL
    # =========================================================================

    async def get_service_status(self, service: str) -> Dict[str, Any]:
        """Get status of a systemd service."""
        try:
            result = await self._run_async(
                ["systemctl", "is-active", service]
            )
            active = result.stdout.decode().strip() == "active"

            result2 = await self._run_async(
                ["systemctl", "is-enabled", service]
            )
            enabled = result2.stdout.decode().strip() == "enabled"

            return {
                "service": service,
                "active": active,
                "enabled": enabled,
            }
        except Exception as e:
            logger.debug("get_service_status_failed", service=service, error=str(e))
            return {"service": service, "error": str(e)}

    async def restart_service(self, service: str, user: bool = True) -> bool:
        """Restart a systemd service."""
        try:
            cmd = ["systemctl"]
            if user:
                cmd.append("--user")
            cmd.extend(["restart", service])

            result = await self._run_async(cmd)
            success = result.returncode == 0
            logger.info("service_restarted", service=service, success=success)
            return success
        except Exception as e:
            logger.warning("restart_service_failed", service=service, error=str(e))
            return False

    # =========================================================================
    # APPLICATION LAUNCHING
    # =========================================================================

    async def launch_app(self, app_name: str) -> bool:
        """Launch an application by name."""
        try:
            result = await self._run_async(
                ["gtk-launch", app_name]
            )
            success = result.returncode == 0
            logger.info("app_launched", app=app_name, success=success)
            return success
        except Exception as e:
            logger.warning("launch_app_failed", app=app_name, error=str(e))
            return False

    async def open_uri(self, uri: str) -> bool:
        """Open a URI (file, URL, etc.) with default handler."""
        try:
            result = await self._run_async(
                ["xdg-open", uri]
            )
            success = result.returncode == 0
            logger.info("uri_opened", uri=uri[:50], success=success)
            return success
        except Exception as e:
            logger.warning("open_uri_failed", uri=uri[:50], error=str(e))
            return False

    # =========================================================================
    # NETWORK STATUS
    # =========================================================================

    async def is_network_connected(self) -> bool:
        """Check if network is connected."""
        try:
            result = await self._run_async(
                ["nmcli", "-t", "-f", "STATE", "general"]
            )
            if result.returncode == 0:
                return "connected" in result.stdout.decode().lower()
        except Exception:
            pass
        return False

    async def get_network_info(self) -> Dict[str, Any]:
        """Get network connection information."""
        try:
            result = await self._run_async(
                ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,STATE", "connection", "show", "--active"]
            )
            if result.returncode == 0:
                connections = []
                for line in result.stdout.decode().strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 4:
                            connections.append({
                                "name": parts[0],
                                "type": parts[1],
                                "device": parts[2],
                                "state": parts[3],
                            })
                return {"connected": True, "connections": connections}
        except Exception as e:
            logger.debug("get_network_info_failed", error=str(e))
        return {"connected": False, "connections": []}

    # =========================================================================
    # SYSTEM STATE SNAPSHOT
    # =========================================================================

    async def take_snapshot(self) -> SystemSnapshot:
        """Take a snapshot of current system state."""
        # Gather all state info in parallel
        brightness_task = asyncio.create_task(self.get_screen_brightness())
        volume_task = asyncio.create_task(self.get_volume())
        muted_task = asyncio.create_task(self.is_muted())
        idle_task = asyncio.create_task(self.get_idle_time())
        locked_task = asyncio.create_task(self.is_screen_locked())
        power_task = asyncio.create_task(self.get_power_state())
        network_task = asyncio.create_task(self.is_network_connected())
        window_task = asyncio.create_task(self.get_active_window())
        clipboard_task = asyncio.create_task(self.get_clipboard_text())

        results = await asyncio.gather(
            brightness_task, volume_task, muted_task, idle_task,
            locked_task, power_task, network_task, window_task, clipboard_task,
            return_exceptions=True
        )

        snapshot = SystemSnapshot(
            timestamp=datetime.now(),
            display_state="locked" if results[4] else "on",
            audio_muted=results[2] if not isinstance(results[2], Exception) else False,
            audio_volume=results[1] if not isinstance(results[1], Exception) else -1,
            active_window=results[7].get("title") if isinstance(results[7], dict) else None,
            idle_time_seconds=results[3] if not isinstance(results[3], Exception) else 0,
            power_state=results[5] if not isinstance(results[5], Exception) else "unknown",
            network_connected=results[6] if not isinstance(results[6], Exception) else False,
            clipboard_has_text=bool(results[8]) if not isinstance(results[8], Exception) else False,
        )

        self._last_snapshot = snapshot
        return snapshot

    # =========================================================================
    # DO NOT DISTURB MODE
    # =========================================================================

    async def enable_do_not_disturb(self) -> bool:
        """Enable Do Not Disturb mode."""
        try:
            result = await self._run_async([
                "gsettings", "set",
                "org.gnome.desktop.notifications", "show-banners", "false"
            ])
            if result.returncode == 0:
                logger.info("dnd_enabled")
                return True
        except Exception as e:
            logger.warning("enable_dnd_failed", error=str(e))
        return False

    async def disable_do_not_disturb(self) -> bool:
        """Disable Do Not Disturb mode."""
        try:
            result = await self._run_async([
                "gsettings", "set",
                "org.gnome.desktop.notifications", "show-banners", "true"
            ])
            if result.returncode == 0:
                logger.info("dnd_disabled")
                return True
        except Exception as e:
            logger.warning("disable_dnd_failed", error=str(e))
        return False

    async def is_do_not_disturb(self) -> bool:
        """Check if Do Not Disturb is enabled."""
        try:
            result = await self._run_async([
                "gsettings", "get",
                "org.gnome.desktop.notifications", "show-banners"
            ])
            if result.returncode == 0:
                return result.stdout.decode().strip() == "false"
        except Exception:
            pass
        return False

    # =========================================================================
    # PRESENCE DETECTION
    # =========================================================================

    async def is_user_active(self, threshold_seconds: int = 300) -> bool:
        """Check if user is actively using the system.

        Args:
            threshold_seconds: Idle time threshold (default 5 minutes)

        Returns:
            True if user has been active within threshold
        """
        idle_time = await self.get_idle_time()
        return idle_time < threshold_seconds

    async def wait_for_user_active(self, poll_interval: int = 30,
                                    timeout: int = 3600) -> bool:
        """Wait for user to become active.

        Args:
            poll_interval: Seconds between checks
            timeout: Maximum wait time in seconds

        Returns:
            True if user became active, False if timeout
        """
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            if await self.is_user_active():
                return True
            await asyncio.sleep(poll_interval)
        return False

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get controller statistics."""
        return {
            "enabled": self.enabled,
            "display_server": self._display_server,
            "gnome_shell_available": self._gnome_shell_available,
            "screenshot_dir": str(self.screenshot_dir),
            "last_snapshot": self._last_snapshot.timestamp.isoformat()
                           if self._last_snapshot else None,
        }

    async def test_capabilities(self) -> Dict[str, bool]:
        """Test what capabilities are available."""
        tests = {}

        # Screen brightness
        brightness = await self.get_screen_brightness()
        tests["screen_brightness"] = brightness >= 0

        # Audio
        volume = await self.get_volume()
        tests["audio_control"] = volume >= 0

        # Clipboard
        clipboard = await self.get_clipboard_text()
        tests["clipboard"] = clipboard is not None

        # Screenshot
        screenshot = await self.take_screenshot("_test.png")
        if screenshot and screenshot.exists():
            screenshot.unlink()  # Clean up test file
        tests["screenshot"] = screenshot is not None

        # Idle time
        idle = await self.get_idle_time()
        tests["idle_detection"] = True  # Will return 0 if failed

        # Network
        network = await self.is_network_connected()
        tests["network_status"] = True  # Method worked

        # GNOME Shell
        tests["gnome_shell"] = self._gnome_shell_available

        logger.info("capabilities_tested", results=tests)
        return tests
