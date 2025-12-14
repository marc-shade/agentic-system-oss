#!/usr/bin/env python3
"""
Arduino Status Rotation Workflow - Physical system monitoring display

Capabilities:
- Rotate through 7 system status views every 5 seconds
- Update LCD display with real-time status
- Set LED colors based on system health
- Display: Temporal, AutoKitteh, Qdrant, MCP, Resources, Memory, Cluster
- Trigger alerts on critical failures
- Gracefully handle Arduino disconnection

STATUS: Production Ready
"""

import asyncio
import logging
import json
import psutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
import sys
import socket
import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_storage_base() -> Path:
    """Detect correct storage base path for current platform"""
    system = platform.system()

    if system == "Darwin":  # macOS
        # Check for SSDRAID0 (hot tier)
        ssd_path = Path("/Volumes/SSDRAID0/agentic-system")
        if ssd_path.exists():
            return ssd_path
        # Fallback to FILES (cold tier - backup only)
        files_path = Path("/Volumes/FILES/agentic-system")
        if files_path.exists():
            return files_path
        # Last resort - home directory
        return Path.home() / "agentic-system"
    elif system == "Linux":
        # Linux nodes use /home/marc/agentic-system
        return Path("/home/marc/agentic-system")
    else:
        # Unknown platform - use home directory
        return Path.home() / "agentic-system"

# Status view rotation sequence
STATUS_VIEWS = [
    "temporal",
    "autokitteh",
    "qdrant",
    "mcp_servers",
    "system_resources",
    "memory_stats",
    "cluster_status"
]


@activity.defn
async def check_arduino_connection() -> Dict[str, Any]:
    """Check if Arduino is connected and accessible"""
    try:
        import serial.tools.list_ports

        # Find Arduino ports
        ports = [p.device for p in serial.tools.list_ports.comports()
                if 'usbmodem' in p.device.lower()]

        if not ports:
            return {
                "connected": False,
                "port": None,
                "error": "No Arduino devices found"
            }

        # Try first available port
        port = ports[0]

        # Test connection (quick check)
        try:
            import serial
            ser = serial.Serial(port, 115200, timeout=1)
            ser.close()

            return {
                "connected": True,
                "port": port,
                "device_count": len(ports)
            }
        except Exception as e:
            return {
                "connected": False,
                "port": port,
                "error": f"Port not accessible: {e}"
            }

    except ImportError:
        return {
            "connected": False,
            "port": None,
            "error": "pyserial not installed"
        }
    except Exception as e:
        logger.error(f"Arduino connection check failed: {e}")
        return {
            "connected": False,
            "port": None,
            "error": str(e)
        }


@activity.defn
async def check_temporal_status() -> Dict[str, Any]:
    """Check Temporal server status"""
    try:
        # Try to connect to Temporal gRPC port
        response = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "curl", "-s", "http://localhost:8233/api/v1/namespaces/default",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=2.0
        )
        await response.communicate()

        healthy = response.returncode == 0

        return {
            "service": "Temporal",
            "status": "healthy" if healthy else "down",
            "port": 7233,
            "ui_port": 8233,
            "healthy": healthy
        }

    except Exception as e:
        logger.error(f"Temporal check failed: {e}")
        return {
            "service": "Temporal",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def check_autokitteh_status() -> Dict[str, Any]:
    """Check AutoKitteh server status"""
    try:
        # Check if AutoKitteh is responding on port 9980
        response = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "curl", "-s", "http://localhost:9980/health",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ),
            timeout=2.0
        )
        stdout, _ = await response.communicate()

        healthy = response.returncode == 0

        return {
            "service": "AutoKitteh",
            "status": "healthy" if healthy else "down",
            "port": 9980,
            "healthy": healthy
        }

    except Exception as e:
        logger.error(f"AutoKitteh check failed: {e}")
        return {
            "service": "AutoKitteh",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def check_qdrant_status() -> Dict[str, Any]:
    """Check Qdrant vector database status"""
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with asyncio.timeout(2.0):
                async with session.get("http://localhost:6333/") as resp:
                    healthy = resp.status == 200

                    # Try to get collection count
                    collections = 0
                    try:
                        async with session.get("http://localhost:6333/collections") as coll_resp:
                            if coll_resp.status == 200:
                                data = await coll_resp.json()
                                collections = len(data.get("result", {}).get("collections", []))
                    except:
                        pass

                    return {
                        "service": "Qdrant",
                        "status": "healthy" if healthy else "down",
                        "port": 6333,
                        "collections": collections,
                        "healthy": healthy
                    }

    except Exception as e:
        logger.error(f"Qdrant check failed: {e}")
        return {
            "service": "Qdrant",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def check_mcp_servers() -> Dict[str, Any]:
    """Check MCP server status"""
    servers = {
        "enhanced-memory": 8101,
        "agent-runtime": 8102,
        "arduino-surface": 8200
    }

    results = {
        "service": "MCP Servers",
        "servers": {},
        "healthy_count": 0,
        "total_count": len(servers)
    }

    for name, port in servers.items():
        try:
            # Quick port check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            healthy = result == 0
            results["servers"][name] = {
                "port": port,
                "healthy": healthy,
                "status": "up" if healthy else "down"
            }

            if healthy:
                results["healthy_count"] += 1

        except Exception as e:
            results["servers"][name] = {
                "port": port,
                "healthy": False,
                "status": "error",
                "error": str(e)
            }

    results["healthy"] = results["healthy_count"] == results["total_count"]
    results["status"] = "healthy" if results["healthy"] else "degraded"

    return results


@activity.defn
async def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage (CPU, memory, disk)"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.5)

        # Memory usage
        mem = psutil.virtual_memory()
        mem_percent = mem.percent

        # Disk usage for SSDRAID0
        disk = psutil.disk_usage('/Volumes/SSDRAID0')
        disk_percent = disk.percent

        # Determine health
        healthy = cpu_percent < 90 and mem_percent < 95 and disk_percent < 90

        if cpu_percent > 90 or mem_percent > 95 or disk_percent > 90:
            status = "warning"
        elif cpu_percent > 95 or mem_percent > 98 or disk_percent > 95:
            status = "critical"
        else:
            status = "healthy"

        return {
            "service": "System",
            "status": status,
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(mem_percent, 1),
            "disk_percent": round(disk_percent, 1),
            "healthy": healthy
        }

    except Exception as e:
        logger.error(f"System resource check failed: {e}")
        return {
            "service": "System",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def check_memory_stats() -> Dict[str, Any]:
    """Check enhanced memory statistics"""
    try:
        storage_base = get_storage_base()
        db_path = storage_base / "databases/enhanced_memory/memory.db"

        if not db_path.exists():
            return {
                "service": "Memory",
                "status": "not_found",
                "healthy": False
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get entity count
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]

        # Get compression stats if available
        cursor.execute("SELECT COUNT(*) FROM entities WHERE compressed = 1")
        compressed = cursor.fetchone()[0]

        conn.close()

        compression_rate = (compressed / total_entities * 100) if total_entities > 0 else 0

        return {
            "service": "Memory",
            "status": "healthy",
            "total_entities": total_entities,
            "compressed": compressed,
            "compression_rate": round(compression_rate, 1),
            "healthy": True
        }

    except Exception as e:
        logger.error(f"Memory stats check failed: {e}")
        return {
            "service": "Memory",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def check_cluster_status() -> Dict[str, Any]:
    """Check cluster node status"""
    try:
        storage_base = get_storage_base()
        db_path = storage_base / "databases/cluster/shared_memories.db"

        if not db_path.exists():
            return {
                "service": "Cluster",
                "status": "not_configured",
                "healthy": True  # Not critical if cluster not set up
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get shared memory count
        cursor.execute("SELECT COUNT(*) FROM entities")
        shared_count = cursor.fetchone()[0]

        conn.close()

        return {
            "service": "Cluster",
            "status": "healthy",
            "shared_memories": shared_count,
            "healthy": True
        }

    except Exception as e:
        logger.error(f"Cluster status check failed: {e}")
        return {
            "service": "Cluster",
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


@activity.defn
async def update_lcd_display(port: str, view_name: str, status_data: Dict) -> Dict:
    """Update Arduino LCD display with status information"""
    try:
        import serial

        # Open serial connection
        ser = serial.Serial(port, 115200, timeout=1)
        await asyncio.sleep(0.1)  # Wait for Arduino to initialize

        # Clear display
        ser.write(b'clear\n')
        await asyncio.sleep(0.05)

        # Format display text based on view
        if view_name == "temporal":
            line1 = f"Temporal: {status_data.get('status', 'unknown')[:9]}"
            line2 = f"Port: {status_data.get('port', '?')}"

        elif view_name == "autokitteh":
            line1 = f"AutoKitteh: {status_data.get('status', 'unknown')[:5]}"
            line2 = f"Port: {status_data.get('port', '?')}"

        elif view_name == "qdrant":
            line1 = f"Qdrant: {status_data.get('status', 'unknown')[:9]}"
            line2 = f"Colls: {status_data.get('collections', 0)}"

        elif view_name == "mcp_servers":
            healthy = status_data.get('healthy_count', 0)
            total = status_data.get('total_count', 0)
            line1 = f"MCP Servers"
            line2 = f"Online: {healthy}/{total}"

        elif view_name == "system_resources":
            cpu = status_data.get('cpu_percent', 0)
            mem = status_data.get('memory_percent', 0)
            line1 = f"CPU: {cpu}%"
            line2 = f"MEM: {mem}%"

        elif view_name == "memory_stats":
            entities = status_data.get('total_entities', 0)
            comp = status_data.get('compression_rate', 0)
            line1 = f"Memory: {entities}"
            line2 = f"Comp: {comp}%"

        elif view_name == "cluster_status":
            shared = status_data.get('shared_memories', 0)
            line1 = f"Cluster: {status_data.get('status', 'unknown')[:9]}"
            line2 = f"Shared: {shared}"

        else:
            line1 = "Unknown View"
            line2 = ""

        # Send to LCD (row, col, text)
        ser.write(f"display 0 0 {line1[:16]}\n".encode())
        await asyncio.sleep(0.05)
        ser.write(f"display 1 0 {line2[:16]}\n".encode())

        ser.close()

        logger.info(f"LCD updated: {view_name} - {line1} / {line2}")
        return {"success": True, "view": view_name}

    except Exception as e:
        logger.error(f"LCD update failed: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def set_health_led(port: str, overall_health: str) -> Dict:
    """Set RGB LED color based on overall system health"""
    try:
        import serial

        # Determine LED color
        if overall_health == "healthy":
            r, g, b = 0, 255, 0  # Green
        elif overall_health == "warning":
            r, g, b = 255, 255, 0  # Yellow
        elif overall_health == "critical":
            r, g, b = 255, 0, 0  # Red
        else:
            r, g, b = 0, 0, 255  # Blue (unknown)

        # Send LED command
        ser = serial.Serial(port, 115200, timeout=1)
        await asyncio.sleep(0.1)
        ser.write(f"led 0 {r} {g} {b}\n".encode())
        ser.close()

        logger.info(f"LED set to {overall_health}: RGB({r},{g},{b})")
        return {"success": True, "color": [r, g, b], "health": overall_health}

    except Exception as e:
        logger.error(f"LED update failed: {e}")
        return {"success": False, "error": str(e)}


@workflow.defn
class ArduinoStatusRotationWorkflow:
    """
    Continuous Arduino status display rotation
    Cycles through system status views every 5 seconds
    """

    @workflow.run
    async def run(self) -> dict:
        workflow.logger.info("Starting Arduino status rotation workflow")

        stats = {
            "started_at": workflow.now().isoformat(),  # FIX: Use workflow.now() for determinism
            "rotations": 0,
            "updates": 0,
            "errors": 0,
            "disconnections": 0
        }

        current_view_index = 0
        arduino_port = None

        while True:
            try:
                # Check Arduino connection
                connection_status = await workflow.execute_activity(
                    check_arduino_connection,
                    start_to_close_timeout=timedelta(seconds=5),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )

                if not connection_status.get("connected"):
                    workflow.logger.warning(f"Arduino not connected: {connection_status.get('error')}")
                    stats["disconnections"] += 1
                    await asyncio.sleep(30)  # Wait longer when disconnected
                    continue

                arduino_port = connection_status.get("port")
                workflow.logger.info(f"Arduino connected on {arduino_port}")

                # Get current view
                view_name = STATUS_VIEWS[current_view_index]
                workflow.logger.info(f"Checking status: {view_name}")

                # Execute appropriate status check
                if view_name == "temporal":
                    status_data = await workflow.execute_activity(
                        check_temporal_status,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "autokitteh":
                    status_data = await workflow.execute_activity(
                        check_autokitteh_status,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "qdrant":
                    status_data = await workflow.execute_activity(
                        check_qdrant_status,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "mcp_servers":
                    status_data = await workflow.execute_activity(
                        check_mcp_servers,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "system_resources":
                    status_data = await workflow.execute_activity(
                        check_system_resources,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "memory_stats":
                    status_data = await workflow.execute_activity(
                        check_memory_stats,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                elif view_name == "cluster_status":
                    status_data = await workflow.execute_activity(
                        check_cluster_status,
                        start_to_close_timeout=timedelta(seconds=5)
                    )
                else:
                    status_data = {"error": "Unknown view"}

                # Update LCD display
                update_result = await workflow.execute_activity(
                    update_lcd_display,
                    args=[arduino_port, view_name, status_data],
                    start_to_close_timeout=timedelta(seconds=3)
                )

                if update_result.get("success"):
                    stats["updates"] += 1
                else:
                    stats["errors"] += 1

                # Determine overall health and set LED
                overall_health = "healthy"
                if not status_data.get("healthy", True):
                    if status_data.get("status") == "critical":
                        overall_health = "critical"
                    else:
                        overall_health = "warning"

                await workflow.execute_activity(
                    set_health_led,
                    args=[arduino_port, overall_health],
                    start_to_close_timeout=timedelta(seconds=3)
                )

                # Move to next view
                current_view_index = (current_view_index + 1) % len(STATUS_VIEWS)
                if current_view_index == 0:
                    stats["rotations"] += 1
                    workflow.logger.info(f"Completed rotation {stats['rotations']}")

                # Wait 5 seconds before next update
                await asyncio.sleep(5)

            except Exception as e:
                stats["errors"] += 1
                workflow.logger.error(f"Error in status rotation: {e}")
                await asyncio.sleep(10)  # Wait on error

        return stats


async def main():
    """Test Arduino status rotation activities"""
    print("Testing Arduino Status Rotation Activities...")
    print("=" * 60)

    # Test Arduino connection
    print("\n1. Checking Arduino connection...")
    connection = await check_arduino_connection()
    print(json.dumps(connection, indent=2))

    if connection.get("connected"):
        port = connection.get("port")

        # Test all status checks
        print("\n2. Testing Temporal status...")
        temporal = await check_temporal_status()
        print(json.dumps(temporal, indent=2))

        print("\n3. Testing AutoKitteh status...")
        autokitteh = await check_autokitteh_status()
        print(json.dumps(autokitteh, indent=2))

        print("\n4. Testing Qdrant status...")
        qdrant = await check_qdrant_status()
        print(json.dumps(qdrant, indent=2))

        print("\n5. Testing MCP servers...")
        mcp = await check_mcp_servers()
        print(json.dumps(mcp, indent=2))

        print("\n6. Testing system resources...")
        resources = await check_system_resources()
        print(json.dumps(resources, indent=2))

        print("\n7. Testing memory stats...")
        memory = await check_memory_stats()
        print(json.dumps(memory, indent=2))

        print("\n8. Testing cluster status...")
        cluster = await check_cluster_status()
        print(json.dumps(cluster, indent=2))

        print("\n9. Testing LCD update...")
        lcd_result = await update_lcd_display(port, "temporal", temporal)
        print(json.dumps(lcd_result, indent=2))

        print("\n10. Testing LED update...")
        led_result = await set_health_led(port, "healthy")
        print(json.dumps(led_result, indent=2))
    else:
        print("\nArduino not connected - skipping hardware tests")

    print("\n" + "=" * 60)
    print("Arduino status rotation activities tested!")


if __name__ == "__main__":
    asyncio.run(main())
