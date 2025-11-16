# Builder Node Artifact Management Design

**Date**: 2025-11-14
**Phase**: 3 - Storage & Artifacts
**Node**: macpro51 (Builder)

## Overview

The artifact management system handles storage, retrieval, and lifecycle management of build artifacts produced by the Builder node.

## Artifact Storage Structure

```
/home/marc/agentic-system/artifacts/
├── builds/                          # Completed builds
│   ├── {project_id}/               # Project-specific builds
│   │   ├── {build_id}/            # Individual build
│   │   │   ├── metadata.json      # Build metadata
│   │   │   ├── build.log          # Build logs
│   │   │   ├── artifacts/         # Build outputs
│   │   │   │   ├── binaries/
│   │   │   │   ├── packages/
│   │   │   │   └── documentation/
│   │   │   └── manifest.json      # Artifact manifest
│   │   └── latest -> {build_id}   # Symlink to latest successful build
├── cache/                          # Build cache (ccache, sccache)
│   ├── compiler/                  # Compiler cache
│   └── dependencies/              # Dependency cache
├── temp/                           # Temporary build workspace
│   └── {build_id}/                # Cleaned after build completion
└── archive/                        # Long-term archived builds
    └── {year}/{month}/            # Date-based archival

/home/marc/mnt/orchestrator/shared-artifacts/  # Orchestrator-accessible artifacts
├── {node_id}/                     # Builder node artifacts
│   ├── latest/                    # Latest builds (symlinks)
│   └── archive/                   # Archived builds
```

## Metadata Formats

### Build Metadata (`metadata.json`)
```json
{
  "build_id": "uuid-v4",
  "project_id": "project-name",
  "build_number": 123,
  "node_id": "macpro51",
  "status": "success|failed|running",
  "start_time": "2025-11-14T15:30:00Z",
  "end_time": "2025-11-14T15:45:00Z",
  "duration_seconds": 900,
  "git_commit": "abc123...",
  "git_branch": "main",
  "build_type": "release|debug|test",
  "compiler": "gcc-13.2",
  "target_platform": "linux-x86_64",
  "build_command": "make -j24",
  "exit_code": 0,
  "artifacts_count": 5,
  "artifacts_size_bytes": 1048576,
  "tags": ["production", "optimized"],
  "webhook_url": "http://orchestrator:9000/api/v1/build/callback"
}
```

### Artifact Manifest (`manifest.json`)
```json
{
  "build_id": "uuid-v4",
  "artifacts": [
    {
      "name": "application",
      "type": "binary",
      "path": "artifacts/binaries/application",
      "size_bytes": 524288,
      "sha256": "abc123...",
      "executable": true,
      "permissions": "0755"
    },
    {
      "name": "libfoo.so",
      "type": "library",
      "path": "artifacts/binaries/libfoo.so.1.0",
      "size_bytes": 102400,
      "sha256": "def456...",
      "symlinks": ["libfoo.so", "libfoo.so.1"]
    },
    {
      "name": "package.tar.gz",
      "type": "package",
      "path": "artifacts/packages/package-1.0.tar.gz",
      "size_bytes": 1048576,
      "sha256": "ghi789..."
    }
  ],
  "total_size_bytes": 1675264,
  "total_artifacts": 3
}
```

## Artifact Retention Policy

### Retention Rules

1. **Latest Builds** (Always Keep)
   - Last 5 successful builds per project
   - Last 2 failed builds per project (for debugging)

2. **Tagged Builds** (Keep Until Tag Removed)
   - Builds tagged "production"
   - Builds tagged "release"
   - Builds tagged "archive"

3. **Time-Based Retention**
   - Successful builds: 30 days
   - Failed builds: 7 days
   - Temporary workspace: 24 hours

4. **Size-Based Cleanup**
   - When artifacts exceed 100GB total, trigger cleanup
   - Remove oldest non-tagged builds first
   - Preserve at least last 3 builds per project

### Archival Strategy

Builds older than 30 days but tagged for archival:
- Compress artifacts (tar.gz)
- Move to `/archive/{year}/{month}/`
- Copy to orchestrator shared storage
- Local copy can be removed after verification

## Artifact Management API

### Endpoints (via Builder API)

**Store Artifact**:
```
POST /api/v1/artifacts/store
{
  "build_id": "uuid",
  "project_id": "project-name",
  "files": [...]
}
```

**Retrieve Artifact**:
```
GET /api/v1/artifacts/{build_id}
GET /api/v1/artifacts/{project_id}/latest
```

**List Artifacts**:
```
GET /api/v1/artifacts?project_id=...&status=success
```

**Delete Artifact**:
```
DELETE /api/v1/artifacts/{build_id}
```

**Cleanup**:
```
POST /api/v1/artifacts/cleanup
{
  "policy": "age|size|count",
  "dry_run": true
}
```

## Webhook System

### Build Completion Webhook

When build completes, send webhook to orchestrator:

```json
{
  "event": "build.completed",
  "timestamp": "2025-11-14T15:45:00Z",
  "node_id": "macpro51",
  "build_id": "uuid",
  "project_id": "project-name",
  "status": "success",
  "duration_seconds": 900,
  "artifacts": {
    "count": 5,
    "size_bytes": 1048576,
    "location": "/home/marc/mnt/orchestrator/shared-artifacts/macpro51/uuid"
  },
  "logs_url": "http://macpro51.local:9000/api/v1/artifacts/uuid/logs",
  "download_url": "http://macpro51.local:9000/api/v1/artifacts/uuid/download"
}
```

### Webhook Delivery

- **Retry Policy**: 3 attempts with exponential backoff (1s, 5s, 15s)
- **Timeout**: 10 seconds per attempt
- **Failure Handling**: Log failure, continue (don't block build completion)
- **Delivery Log**: Store in `webhooks.log` with timestamps and responses

## Build Process Integration

### Build Workflow

1. **Receive Build Request** (via API or Redis queue)
   ```json
   {
     "build_id": "uuid",
     "project_id": "project-name",
     "git_url": "https://...",
     "git_commit": "abc123",
     "build_command": "make -j24",
     "webhook_url": "http://orchestrator:9000/callback"
   }
   ```

2. **Prepare Workspace**
   - Create `/artifacts/temp/{build_id}/`
   - Clone repository
   - Set up build environment

3. **Execute Build**
   - Run build command
   - Capture stdout/stderr to `build.log`
   - Track start/end times

4. **Collect Artifacts**
   - Identify build outputs
   - Calculate checksums
   - Generate manifest

5. **Store Artifacts**
   - Move to `/artifacts/builds/{project_id}/{build_id}/`
   - Copy to orchestrator shared storage
   - Create metadata.json

6. **Send Webhook**
   - Notify orchestrator of completion
   - Include artifact locations and metadata

7. **Cleanup Workspace**
   - Remove `/artifacts/temp/{build_id}/`
   - Update retention policies

## Shared Storage Integration

### Orchestrator Access

Artifacts are made available to orchestrator via:

1. **Direct SSHFS Mount Access**
   - Orchestrator can read from Builder's artifact storage
   - Path: `/Volumes/SSDRAID0/agentic-system/artifacts/`

2. **Shared Directory** (Preferred)
   - Builder writes to `/home/marc/mnt/orchestrator/shared-artifacts/macpro51/`
   - Orchestrator reads from local path
   - Reduces network traffic for artifact retrieval

3. **HTTP Download** (Fallback)
   - Builder API provides download endpoints
   - Useful for external systems or direct downloads

## Cleanup Automation

### Systemd Timer

Create `artifact-cleanup.timer` to run daily:

```ini
[Unit]
Description=Daily Artifact Cleanup Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### Cleanup Service

```bash
#!/bin/bash
# Run cleanup with policies
python3 /home/marc/agentic-system/services/artifact-cleanup.py \
  --age-days 30 \
  --max-size-gb 100 \
  --keep-last 5 \
  --keep-tagged
```

## Monitoring & Metrics

### Artifact Metrics

Track via Builder API `/api/v1/artifacts/stats`:

```json
{
  "total_artifacts": 150,
  "total_size_gb": 45.2,
  "by_project": {
    "project-a": {"count": 50, "size_gb": 20.1},
    "project-b": {"count": 100, "size_gb": 25.1}
  },
  "by_status": {
    "success": 140,
    "failed": 10
  },
  "oldest_artifact": "2024-10-15T12:00:00Z",
  "newest_artifact": "2025-11-14T15:45:00Z",
  "cache_hit_rate": "87%"
}
```

## Security Considerations

1. **Access Control**
   - Artifacts owned by `marc:marc`
   - Permissions: 0755 for directories, 0644 for files
   - Executables: 0755 when needed

2. **Validation**
   - SHA256 checksums for all artifacts
   - Verify integrity before archival
   - Validate webhook URLs (no localhost bypass)

3. **Isolation**
   - Build workspace isolated per build
   - Cleanup after completion
   - No cross-build contamination

## Implementation Priority

**Phase 3.1**: Core Storage (This Phase)
- ✅ Directory structure
- [ ] Metadata formats
- [ ] Basic storage/retrieval
- [ ] Manifest generation

**Phase 3.2**: Webhook System
- [ ] Webhook delivery
- [ ] Retry logic
- [ ] Callback logging

**Phase 3.3**: Retention & Cleanup
- [ ] Retention policies
- [ ] Cleanup automation
- [ ] Archival system

**Phase 3.4**: Integration
- [ ] Build API endpoints
- [ ] Shared storage sync
- [ ] Metrics and monitoring

## Next Steps

1. Create artifact directory structure
2. Implement artifact manager Python module
3. Add artifact endpoints to Builder API
4. Create webhook delivery system
5. Implement cleanup automation
6. Test with sample builds

---
**Status**: Design Complete, Ready for Implementation
