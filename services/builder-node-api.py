#!/usr/bin/env python3
"""
Production-Quality Builder Node API Server
Provides orchestrator-accessible endpoints with Prometheus metrics
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from pydantic import BaseModel, Field

# Import existing artifact manager
sys.path.insert(0, str(Path(__file__).parent))
from artifact_manager import ArtifactManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(Path.home() / "agentic-system" / "logs" / "builder-api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Node configuration
NODE_ID = "macpro51"
NODE_TYPE = "builder"
NODE_ROLE = "construction_deployment"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = 2  # Build queue DB

# Create custom metrics registry to avoid conflicts
METRICS_REGISTRY = CollectorRegistry()

# Prometheus Metrics
builder_active_builds = Gauge(
    "builder_active_builds",
    "Number of currently running builds",
    registry=METRICS_REGISTRY,
)

builder_builds_total = Counter(
    "builder_builds_total",
    "Total number of builds processed",
    ["status"],  # success, failed, cancelled
    registry=METRICS_REGISTRY,
)

builder_build_duration_seconds = Histogram(
    "builder_build_duration_seconds",
    "Build execution duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600],
    registry=METRICS_REGISTRY,
)

builder_artifact_storage_bytes = Gauge(
    "builder_artifact_storage_bytes",
    "Total artifact storage size in bytes",
    registry=METRICS_REGISTRY,
)

builder_artifact_storage_bytes_by_project = Gauge(
    "builder_artifact_storage_bytes_by_project",
    "Artifact storage size in bytes by project",
    ["project_id"],
    registry=METRICS_REGISTRY,
)

builder_total_artifacts = Gauge(
    "builder_total_artifacts",
    "Total number of artifacts stored",
    registry=METRICS_REGISTRY,
)

builder_api_requests_total = Counter(
    "builder_api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"],
    registry=METRICS_REGISTRY,
)

builder_api_request_duration_seconds = Histogram(
    "builder_api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=METRICS_REGISTRY,
)

# Pydantic Models
class BuildRequest(BaseModel):
    """Build job submission request"""

    project_id: str = Field(..., description="Project identifier")
    git_commit: Optional[str] = Field(None, description="Git commit SHA")
    git_branch: Optional[str] = Field(None, description="Git branch name")
    build_type: str = Field("release", description="Build type (debug/release)")
    build_command: Optional[str] = Field(None, description="Custom build command")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for notifications")
    tags: Optional[List[str]] = Field(None, description="Build tags")
    priority: int = Field(5, description="Build priority (1-10, 10=highest)", ge=1, le=10)


class BuildResponse(BaseModel):
    """Build job response"""

    build_id: str
    project_id: str
    build_number: int
    status: str
    created_at: str


class BuildStatus(BaseModel):
    """Build status response"""

    build_id: str
    project_id: str
    build_number: int
    node_id: str
    status: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: Optional[int]
    git_commit: Optional[str]
    git_branch: Optional[str]
    build_type: str
    exit_code: Optional[int]
    artifacts_count: int
    artifacts_size_bytes: int
    tags: List[str]


class WebhookCallback(BaseModel):
    """Webhook callback from orchestrator"""

    build_id: str
    action: str  # "start", "complete", "cancel"
    metadata: Optional[Dict] = None


class HealthStatus(BaseModel):
    """Health check response"""

    status: str
    node_id: str
    timestamp: str
    services: Dict[str, bool]


# Global state
redis_client: Optional[redis.Redis] = None
artifact_manager: Optional[ArtifactManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context"""
    global redis_client, artifact_manager

    # Startup
    logger.info(f"Starting Builder Node API on {NODE_ID}")

    # Initialize Redis
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True,
    )
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

    # Initialize artifact manager
    artifact_manager = ArtifactManager()
    logger.info(f"Artifact manager initialized at {artifact_manager.base_path}")

    # Update initial metrics
    await update_artifact_metrics()

    yield

    # Shutdown
    logger.info("Shutting down Builder Node API")
    await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="Builder Node API",
    description="Production-quality API for Builder node (macpro51)",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on orchestrator
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request timing and metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record metrics for each request"""
    start_time = time.time()
    method = request.method
    path = request.url.path

    # Execute request
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        logger.error(f"Request failed: {e}")
        status = 500
        raise
    finally:
        # Record metrics
        duration = time.time() - start_time
        builder_api_request_duration_seconds.labels(method=method, endpoint=path).observe(
            duration
        )
        builder_api_requests_total.labels(
            method=method, endpoint=path, status=status
        ).inc()

    return response


async def update_artifact_metrics():
    """Update artifact storage metrics"""
    try:
        stats = artifact_manager.get_stats()

        # Update total metrics
        total_bytes = stats["total_size_gb"] * 1024 * 1024 * 1024
        builder_artifact_storage_bytes.set(total_bytes)
        builder_total_artifacts.set(stats["total_artifacts"])

        # Update per-project metrics
        for project_id, project_stats in stats["by_project"].items():
            project_bytes = project_stats["size_gb"] * 1024 * 1024 * 1024
            builder_artifact_storage_bytes_by_project.labels(
                project_id=project_id
            ).set(project_bytes)

        logger.debug(f"Updated artifact metrics: {stats['total_artifacts']} artifacts, {stats['total_size_gb']:.2f} GB")
    except Exception as e:
        logger.error(f"Failed to update artifact metrics: {e}")


# API Endpoints

@app.get("/", tags=["info"])
async def root():
    """API information"""
    return {
        "name": "Builder Node API",
        "version": "1.0.0",
        "node_id": NODE_ID,
        "node_type": NODE_TYPE,
        "node_role": NODE_ROLE,
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "metrics": "/api/v1/metrics",
            "build_submit": "POST /api/v1/build",
            "build_status": "GET /api/v1/build/{build_id}",
            "build_logs": "GET /api/v1/build/{build_id}/logs",
            "artifact_download": "GET /api/v1/artifacts/{build_id}/download",
            "webhook": "POST /api/v1/build/callback",
        },
    }


@app.get("/health", response_model=HealthStatus, tags=["health"])
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connectivity
        redis_ok = await redis_client.ping()

        # Check artifact storage
        artifact_path_ok = artifact_manager.base_path.exists()

        # Overall status
        status = "healthy" if (redis_ok and artifact_path_ok) else "degraded"

        return HealthStatus(
            status=status,
            node_id=NODE_ID,
            timestamp=datetime.now().isoformat(),
            services={
                "redis": redis_ok,
                "artifact_storage": artifact_path_ok,
            },
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint"""
    try:
        # Check if we can accept new builds
        queue_size = await redis_client.zcard(f"builder:queue:{NODE_ID}")
        active_builds = await redis_client.scard(f"builder:active:{NODE_ID}")

        # Consider ready if queue is not overloaded
        max_queue_size = 100
        max_active_builds = 10

        ready = queue_size < max_queue_size and active_builds < max_active_builds

        return {
            "ready": ready,
            "node_id": NODE_ID,
            "queue_size": queue_size,
            "active_builds": active_builds,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")


@app.post("/api/v1/build", response_model=BuildResponse, tags=["build"])
async def submit_build(build_req: BuildRequest, background_tasks: BackgroundTasks):
    """Submit a new build job"""
    try:
        # Create build in artifact manager
        metadata = artifact_manager.create_build(
            project_id=build_req.project_id,
            git_commit=build_req.git_commit,
            git_branch=build_req.git_branch,
            build_type=build_req.build_type,
            build_command=build_req.build_command,
            webhook_url=build_req.webhook_url,
            tags=build_req.tags or [],
        )

        build_id = metadata["build_id"]

        # Enqueue to Redis
        task = {
            "build_id": build_id,
            "type": "build",
            "project_id": build_req.project_id,
            "priority": build_req.priority,
            "created_at": datetime.now().isoformat(),
        }

        # Store task metadata
        await redis_client.hset(f"task:{build_id}", mapping=task)

        # Add to priority queue
        await redis_client.zadd(
            f"builder:queue:{NODE_ID}", {build_id: -build_req.priority}
        )

        # Update metrics in background
        background_tasks.add_task(update_artifact_metrics)

        logger.info(
            f"Build submitted: {build_id} (project={build_req.project_id}, priority={build_req.priority})"
        )

        return BuildResponse(
            build_id=build_id,
            project_id=metadata["project_id"],
            build_number=metadata["build_number"],
            status=metadata["status"],
            created_at=metadata["start_time"],
        )

    except Exception as e:
        logger.error(f"Failed to submit build: {e}")
        raise HTTPException(status_code=500, detail=f"Build submission failed: {str(e)}")


@app.get("/api/v1/build/{build_id}", response_model=BuildStatus, tags=["build"])
async def get_build_status(build_id: str):
    """Get build status"""
    try:
        metadata = artifact_manager.get_build_metadata(build_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        return BuildStatus(**metadata)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get build status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve build status: {str(e)}"
        )


@app.get("/api/v1/build/{build_id}/logs", tags=["build"])
async def stream_build_logs(build_id: str):
    """Stream build logs"""
    try:
        metadata = artifact_manager.get_build_metadata(build_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        project_id = metadata["project_id"]
        log_file = (
            artifact_manager.builds_path / project_id / build_id / "build.log"
        )

        if not log_file.exists():
            return Response(
                content="Build log not yet available\n",
                media_type="text/plain",
            )

        async def log_generator():
            """Stream log file"""
            async with aiofiles.open(log_file, "r") as f:
                async for line in f:
                    yield line

        return StreamingResponse(log_generator(), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stream logs: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to stream logs: {str(e)}"
        )


@app.get("/api/v1/artifacts/{build_id}/download", tags=["artifacts"])
async def download_artifacts(build_id: str, artifact_name: Optional[str] = None):
    """Download build artifacts"""
    try:
        metadata = artifact_manager.get_build_metadata(build_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Build {build_id} not found")

        if artifact_name:
            # Download specific artifact
            artifact_path = artifact_manager.get_artifact_path(build_id, artifact_name)

            if not artifact_path or not artifact_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Artifact {artifact_name} not found in build {build_id}",
                )

            return FileResponse(
                path=str(artifact_path),
                filename=artifact_name,
                media_type="application/octet-stream",
            )
        else:
            # Return artifact manifest
            project_id = metadata["project_id"]
            manifest_file = (
                artifact_manager.builds_path / project_id / build_id / "manifest.json"
            )

            if not manifest_file.exists():
                return {"build_id": build_id, "artifacts": []}

            async with aiofiles.open(manifest_file, "r") as f:
                manifest = json.loads(await f.read())

            return manifest

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download artifacts: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download artifacts: {str(e)}"
        )


@app.post("/api/v1/build/callback", tags=["build"])
async def webhook_callback(callback: WebhookCallback, background_tasks: BackgroundTasks):
    """Receive webhook callbacks from orchestrator"""
    try:
        build_id = callback.build_id
        action = callback.action

        logger.info(f"Received webhook callback: action={action}, build_id={build_id}")

        if action == "start":
            # Mark build as running
            builder_active_builds.inc()
            await redis_client.sadd(f"builder:active:{NODE_ID}", build_id)

        elif action == "complete":
            # Mark build as complete
            builder_active_builds.dec()
            await redis_client.srem(f"builder:active:{NODE_ID}", build_id)

            # Update metadata
            success = callback.metadata.get("success", False)
            exit_code = callback.metadata.get("exit_code", 0)

            artifact_manager.update_build_status(
                build_id=build_id,
                status="success" if success else "failed",
                exit_code=exit_code,
            )

            # Update metrics
            builder_builds_total.labels(
                status="success" if success else "failed"
            ).inc()

            if "duration" in callback.metadata:
                builder_build_duration_seconds.observe(callback.metadata["duration"])

            background_tasks.add_task(update_artifact_metrics)

        elif action == "cancel":
            # Cancel build
            builder_active_builds.dec()
            await redis_client.srem(f"builder:active:{NODE_ID}", build_id)
            await redis_client.zrem(f"builder:queue:{NODE_ID}", build_id)

            artifact_manager.update_build_status(
                build_id=build_id, status="cancelled"
            )

            builder_builds_total.labels(status="cancelled").inc()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        return {"status": "success", "action": action, "build_id": build_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook callback failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Webhook callback failed: {str(e)}"
        )


@app.get("/api/v1/metrics", tags=["monitoring"])
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    # Update artifact metrics before exporting
    await update_artifact_metrics()

    # Generate Prometheus metrics from custom registry
    metrics_output = generate_latest(METRICS_REGISTRY)

    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


# Main entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "builder-node-api:app",
        host="0.0.0.0",
        port=9000,
        log_level="info",
        access_log=True,
    )
