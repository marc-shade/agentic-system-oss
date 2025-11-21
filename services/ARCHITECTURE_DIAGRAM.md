# Build Executor Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BUILD EXECUTOR ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                               INPUT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   API Call   │    │  Git Webhook │    │   Scheduled  │                  │
│  │   (Python)   │    │   Trigger    │    │    Build     │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                           │
│         └───────────────────┴───────────────────┘                           │
│                             │                                               │
│                             ▼                                               │
│                    ┌─────────────────┐                                      │
│                    │  Redis Queue    │                                      │
│                    │   (DB 2)        │                                      │
│                    │  build_queue    │                                      │
│                    └─────────────────┘                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

                                  │
                                  ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                          BUILD EXECUTOR CORE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Build Executor Worker                            │    │
│  │                   (build_executor.py)                                │    │
│  │                                                                       │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │    │
│  │  │  Thread Pool   │  │   Concurrency  │  │  Shutdown      │        │    │
│  │  │  Management    │  │   Control      │  │  Handler       │        │    │
│  │  │  (2 workers)   │  │   (Semaphore)  │  │  (Graceful)    │        │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘        │    │
│  │                                                                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐   │    │
│  │  │              Build Execution Pipeline                        │   │    │
│  │  │                                                               │   │    │
│  │  │  1. Fetch Job from Redis                                     │   │    │
│  │  │  2. Create Workspace (/tmp/builds/{build_id})               │   │    │
│  │  │  3. Initialize Artifact Manager                              │   │    │
│  │  │  4. Send Webhook (build.started)                            │   │    │
│  │  │  5. Clone Repository (git)                                   │   │    │
│  │  │  6. Pull Docker Image                                        │   │    │
│  │  │  7. Start Container (isolated)                               │   │    │
│  │  │  8. Execute Build Command                                    │   │    │
│  │  │  9. Capture Logs                                             │   │    │
│  │  │ 10. Collect Artifacts                                        │   │    │
│  │  │ 11. Update Metadata                                          │   │    │
│  │  │ 12. Update Metrics                                           │   │    │
│  │  │ 13. Send Webhook (build.completed/failed)                   │   │    │
│  │  │ 14. Cleanup Workspace                                        │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

                │                  │                  │
                ▼                  ▼                  ▼

┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
│  Docker Engine     │  │  Artifact Manager  │  │  Webhook Delivery  │
│                    │  │                    │  │                    │
│ ┌────────────────┐ │  │ ┌────────────────┐ │  │ ┌────────────────┐ │
│ │   Container    │ │  │ │  Build Metadata│ │  │ │ HTTP Callbacks │ │
│ │   Isolation    │ │  │ │   (JSON)       │ │  │ │  w/ Retry      │ │
│ └────────────────┘ │  │ └────────────────┘ │  │ └────────────────┘ │
│                    │  │                    │  │                    │
│ ┌────────────────┐ │  │ ┌────────────────┐ │  │ ┌────────────────┐ │
│ │ Volume Mounts  │ │  │ │   Artifacts    │ │  │ │  Exponential   │ │
│ │ /workspace     │ │  │ │   Storage      │ │  │ │   Backoff      │ │
│ │ /output        │ │  │ │   (SHA256)     │ │  │ │  (1s,5s,15s)   │ │
│ └────────────────┘ │  │ └────────────────┘ │  │ └────────────────┘ │
│                    │  │                    │  │                    │
│ ┌────────────────┐ │  │ ┌────────────────┐ │  │ ┌────────────────┐ │
│ │ Resource Limits│ │  │ │   Versioning   │ │  │ │  Delivery Log  │ │
│ │ 2GB RAM        │ │  │ │   Build #      │ │  │ │  (webhooks.log)│ │
│ │ 1 CPU Core     │ │  │ │   Symlinks     │ │  │ └────────────────┘ │
│ └────────────────┘ │  │ └────────────────┘ │  │                    │
└────────────────────┘  └────────────────────┘  └────────────────────┘

                │                  │                  │
                └──────────────────┴──────────────────┘
                                   │
                                   ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                            STORAGE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   Artifact Storage  │  │    Redis State      │  │    Log Storage      │  │
│  │                     │  │                     │  │                     │  │
│  │ /artifacts/builds/  │  │  build:{id}:status  │  │  build_executor.log │  │
│  │   {project}/        │  │  metrics:builds:*   │  │  webhooks.log       │  │
│  │     {build_id}/     │  │  build_duration:*   │  │                     │  │
│  │       metadata.json │  │                     │  │                     │  │
│  │       manifest.json │  │                     │  │                     │  │
│  │       artifacts/    │  │                     │  │                     │  │
│  │         binaries/   │  │                     │  │                     │  │
│  │         packages/   │  │                     │  │                     │  │
│  │         docs/       │  │                     │  │                     │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘

                                   │
                                   ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MONITORING LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   Prometheus    │  │      Loki       │  │    Grafana      │             │
│  │                 │  │                 │  │                 │             │
│  │ Build Metrics   │  │   Build Logs    │  │  Dashboards     │             │
│  │ Success Rate    │  │   Error Logs    │  │  Alerts         │             │
│  │ Duration        │  │   Audit Trail   │  │  Trends         │             │
│  │ Queue Depth     │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### 1. Job Submission Flow

```
Client → Redis Queue → Executor Worker → Docker Container → Artifacts
```

### 2. Build Execution Flow

```
Fetch Job
    ↓
Create Workspace (/tmp/builds/{id})
    ↓
Clone Repo (if git_repo provided)
    ↓
Pull Image (node:20, python:3.12, etc.)
    ↓
Start Container
    ├─ Mount /workspace (source)
    ├─ Mount /output (artifacts)
    └─ Set resource limits
    ↓
Execute Build Command
    ├─ Capture stdout/stderr
    └─ Monitor timeout
    ↓
Collect Artifacts
    ├─ Classify by type
    ├─ Calculate SHA256
    └─ Store metadata
    ↓
Update Status
    ├─ Redis state
    ├─ Prometheus metrics
    └─ Webhook callback
    ↓
Cleanup Workspace
```

### 3. Webhook Notification Flow

```
Build Event
    ↓
Webhook Delivery
    ├─ Attempt 1 (immediate)
    ├─ Attempt 2 (+1s if failed)
    ├─ Attempt 3 (+5s if failed)
    └─ Attempt 4 (+15s if failed)
    ↓
Log Result (webhooks.log)
```

### 4. Artifact Storage Structure

```
/home/marc/agentic-system/artifacts/
└── builds/
    └── {project_id}/
        ├── latest → {latest_build_id}
        └── {build_id}/
            ├── metadata.json (build info)
            ├── manifest.json (artifact list)
            └── artifacts/
                ├── binaries/
                ├── packages/
                └── documentation/
                    └── build.log
```

### 5. Concurrency Control

```
┌─────────────────────────────────────┐
│     Active Builds Semaphore         │
│     (MAX_CONCURRENT_BUILDS=2)       │
├─────────────────────────────────────┤
│                                     │
│  Slot 1: [Build A - Running]       │
│  Slot 2: [Build B - Running]       │
│                                     │
│  Queue:  Build C, Build D, ...      │
│                                     │
└─────────────────────────────────────┘
```

### 6. Resource Management

```
Per Container:
├─ Memory: 2GB limit
├─ CPU: 1 core quota
├─ Disk: Workspace in /tmp/builds
├─ Network: Host network access
└─ Volumes: Source + Output only

Host Resources (macpro51):
├─ 24 threads available
├─ 126GB RAM available
├─ 930GB NVMe RAID10
└─ Max 2-4 concurrent builds
```

## Integration Points

### Phase 2: Task Queue
- Redis DB 2 for job queue
- Job schema with build configuration
- Status tracking in Redis

### Phase 3: Artifact Management
- `artifact_manager.py` integration
- Automatic artifact classification
- Build versioning and metadata

### Phase 4: Monitoring
- Prometheus metrics (Redis export)
- Loki log aggregation
- Grafana dashboards

### Phase 5: Orchestration
- Webhook callbacks
- Build status propagation
- Cluster coordination

## Security Boundaries

```
┌──────────────────────────────────────────┐
│             Host System                   │
│  ┌────────────────────────────────────┐  │
│  │       Build Executor Process       │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │     Docker Container         │  │  │
│  │  │  ┌────────────────────────┐  │  │  │
│  │  │  │   Build Environment    │  │  │  │
│  │  │  │   (Isolated)           │  │  │  │
│  │  │  │                        │  │  │  │
│  │  │  │   /workspace (RW)      │  │  │  │
│  │  │  │   /output (RW)         │  │  │  │
│  │  │  └────────────────────────┘  │  │  │
│  │  │                              │  │  │
│  │  │  Resource Limits:            │  │  │
│  │  │  - 2GB Memory                │  │  │
│  │  │  - 1 CPU Core                │  │  │
│  │  │  - No Host Access            │  │  │
│  │  └──────────────────────────────┘  │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

## Performance Characteristics

### Build Latency Breakdown

```
Total Build Time = Queue Wait + Setup + Execution + Cleanup

├─ Queue Wait:      0-60s (depends on concurrency)
├─ Setup:           5-30s (workspace + git clone)
│  ├─ Workspace:    <1s
│  ├─ Git Clone:    2-20s
│  └─ Image Pull:   2-10s (cached)
├─ Execution:       30s-2h (varies by project)
│  ├─ npm install:  10-60s
│  ├─ npm build:    20s-5min
│  └─ cargo build:  5-30min
└─ Cleanup:         1-5s
```

### Throughput Limits

```
Max Builds/Hour (2 concurrent):
├─ Fast builds (1min):  120 builds/hour
├─ Medium (5min):       24 builds/hour
└─ Slow (30min):        4 builds/hour

Recommended Mix:
└─ 2-4 concurrent for balanced throughput
```
