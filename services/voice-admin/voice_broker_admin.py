#!/usr/bin/env python3
"""
Voice Broker Admin - Administrative interface for voice services.
Provides health monitoring, service control, and stats for:
- Whisper STT (port 2022)
- Kokoro TTS (port 8880)
- LiveKit RTC (port 7880)
- Voice Cache (port 9093)

Runs on port 9092.
"""

import argparse
import asyncio
import json
import logging
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Voice services configuration
VOICE_SERVICES = {
    "whisper": {
        "name": "Whisper STT",
        "port": 2022,
        "health_endpoint": "/health",
        "restart_cmd": ["voicemode", "whisper", "restart"],
        "status_cmd": ["voicemode", "whisper", "status"]
    },
    "kokoro": {
        "name": "Kokoro TTS",
        "port": 8880,
        "health_endpoint": "/health",
        "restart_cmd": ["voicemode", "kokoro", "restart"],
        "status_cmd": ["voicemode", "kokoro", "status"]
    },
    "livekit": {
        "name": "LiveKit RTC",
        "port": 7880,
        "health_endpoint": "/",
        "restart_cmd": ["voicemode", "livekit", "restart"],
        "status_cmd": ["voicemode", "livekit", "status"]
    },
    "voice_cache": {
        "name": "Voice Cache Proxy",
        "port": 9093,
        "health_endpoint": "/health",
        "restart_cmd": None,  # Managed differently
        "status_cmd": None
    }
}

# Stats storage
stats = {
    "start_time": datetime.now().isoformat(),
    "health_checks": 0,
    "restarts_requested": 0,
    "last_health_check": None,
    "service_status": {}
}


def check_port(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def check_service_health(service_id: str) -> dict:
    """Check health of a specific voice service."""
    service = VOICE_SERVICES.get(service_id)
    if not service:
        return {"error": f"Unknown service: {service_id}"}

    port_open = check_port(service["port"])

    status = {
        "service": service_id,
        "name": service["name"],
        "port": service["port"],
        "port_open": port_open,
        "healthy": port_open,
        "checked_at": datetime.now().isoformat()
    }

    # Try to get more detailed status via voicemode CLI
    if service.get("status_cmd"):
        try:
            result = subprocess.run(
                service["status_cmd"],
                capture_output=True,
                text=True,
                timeout=5
            )
            status["cli_output"] = result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
        except Exception as e:
            status["cli_error"] = str(e)

    return status


async def check_all_services() -> dict:
    """Check health of all voice services."""
    results = {}
    all_healthy = True

    for service_id in VOICE_SERVICES:
        status = await check_service_health(service_id)
        results[service_id] = status
        if not status.get("healthy", False):
            all_healthy = False

    stats["health_checks"] += 1
    stats["last_health_check"] = datetime.now().isoformat()
    stats["service_status"] = results

    return {
        "all_healthy": all_healthy,
        "services": results,
        "timestamp": datetime.now().isoformat()
    }


async def restart_service(service_id: str) -> dict:
    """Restart a specific voice service."""
    service = VOICE_SERVICES.get(service_id)
    if not service:
        return {"error": f"Unknown service: {service_id}"}

    if not service.get("restart_cmd"):
        return {"error": f"Service {service_id} cannot be restarted via this admin"}

    stats["restarts_requested"] += 1

    try:
        result = subprocess.run(
            service["restart_cmd"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Wait a moment for service to come up
        await asyncio.sleep(2)

        # Check if it's healthy now
        new_status = await check_service_health(service_id)

        return {
            "service": service_id,
            "restart_requested": True,
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "current_status": new_status
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Restart timed out for {service_id}"}
    except Exception as e:
        return {"error": str(e)}


# HTTP Handlers

async def handle_health(request: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({
        "status": "healthy",
        "service": "voice-broker-admin",
        "timestamp": datetime.now().isoformat()
    })


async def handle_status(request: web.Request) -> web.Response:
    """Full status of all voice services."""
    health = await check_all_services()
    return web.json_response({
        "admin_status": "running",
        "uptime_since": stats["start_time"],
        "total_health_checks": stats["health_checks"],
        "total_restarts": stats["restarts_requested"],
        **health
    })


async def handle_service_status(request: web.Request) -> web.Response:
    """Status of a specific service."""
    service_id = request.match_info.get("service_id")
    status = await check_service_health(service_id)
    return web.json_response(status)


async def handle_service_restart(request: web.Request) -> web.Response:
    """Restart a specific service."""
    service_id = request.match_info.get("service_id")
    result = await restart_service(service_id)
    status_code = 200 if "error" not in result else 400
    return web.json_response(result, status=status_code)


async def handle_restart_all(request: web.Request) -> web.Response:
    """Restart all restartable services."""
    results = {}
    for service_id, service in VOICE_SERVICES.items():
        if service.get("restart_cmd"):
            results[service_id] = await restart_service(service_id)
    return web.json_response({"restarts": results})


async def handle_stats(request: web.Request) -> web.Response:
    """Admin stats."""
    return web.json_response({
        "start_time": stats["start_time"],
        "health_checks": stats["health_checks"],
        "restarts_requested": stats["restarts_requested"],
        "last_health_check": stats["last_health_check"]
    })


async def handle_services_list(request: web.Request) -> web.Response:
    """List all managed services."""
    services = []
    for service_id, config in VOICE_SERVICES.items():
        services.append({
            "id": service_id,
            "name": config["name"],
            "port": config["port"],
            "restartable": config.get("restart_cmd") is not None
        })
    return web.json_response({"services": services})


def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application()

    app.router.add_get("/health", handle_health)
    app.router.add_get("/", handle_status)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/stats", handle_stats)
    app.router.add_get("/services", handle_services_list)
    app.router.add_get("/service/{service_id}", handle_service_status)
    app.router.add_post("/service/{service_id}/restart", handle_service_restart)
    app.router.add_post("/restart-all", handle_restart_all)

    return app


def main():
    parser = argparse.ArgumentParser(description="Voice Broker Admin Service")
    parser.add_argument("--port", type=int, default=9092, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    logger.info(f"Starting Voice Broker Admin on {args.host}:{args.port}")
    logger.info(f"Managing services: {', '.join(VOICE_SERVICES.keys())}")

    app = create_app()
    web.run_app(app, host=args.host, port=args.port, print=lambda x: logger.info(x))


if __name__ == "__main__":
    main()
