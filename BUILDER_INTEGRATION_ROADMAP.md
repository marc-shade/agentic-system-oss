# Builder Node - Complete Integration Roadmap

**Node**: macpro51 (Builder)
**Role**: Compilation, Testing, Deployment Specialist
**Orchestrator**: mac-studio (192.168.1.16)
**Status**: Phase 1 Complete, Proceeding to Full Integration
**Date**: 2025-11-14

---

## Current State Assessment

### ✅ Phase 1: Foundation (COMPLETE)

**Network Connectivity**:
- [x] SSH bidirectional access (Builder ↔ Orchestrator)
- [x] Telnet emergency access (port 9999)
- [x] Firewall rules configured
- [x] SELinux policies set

**Build Infrastructure**:
- [x] All compilers installed (GCC, Clang, Rust, Go, Python 3.14, Node.js, Java)
- [x] Build optimization (ccache, sccache with Redis backend)
- [x] Container tools (Docker, Podman, buildah, skopeo)
- [x] Testing tools (pytest, jest, cargo test, valgrind, hyperfine)

**Core Services**:
- [x] Redis running (port 6379)
- [x] Qdrant running (port 6333)
- [x] Builder Task Queue Worker (systemd service)
- [x] Telnet cluster service (port 9999)

**Builder Skills**:
- [x] 5 procedural skills created and stored in enhanced-memory
- [x] Integration tests: 100% pass rate (5/5)

### ❌ Phase 2: Integration (IN PROGRESS)

**Missing Components**:
- [ ] Builder API not responding on port 9000
- [ ] MCP servers not running as systemd services
- [ ] Monitoring stack not deployed
- [ ] Shared storage not mounted
- [ ] Heartbeat monitoring not configured
- [ ] Service discovery not advertising correctly
- [ ] Webhook callbacks not implemented
- [ ] Artifact delivery system not set up

---

## Complete Integration Roadmap

### Phase 2: Service Layer (Priority: CRITICAL)

#### 2.1 Builder API Service ⚠️
**Status**: Exists but not running
**Priority**: HIGH
**Tasks**:
- [ ] Fix Builder API startup (currently failing health check)
- [ ] Configure as systemd service for auto-start
- [ ] Verify all endpoints respond correctly:
  - `GET /api/v1/health` - Health check
  - `GET /api/v1/status` - Full node status
  - `GET /api/v1/builder` - Builder capabilities
  - `POST /api/v1/tasks` - Task submission endpoint (NEW)
  - `GET /api/v1/tasks/{task_id}` - Task status endpoint (NEW)
  - `GET /api/v1/artifacts/{task_id}` - Artifact retrieval (NEW)
- [ ] Add authentication/authorization for orchestrator
- [ ] Enable CORS for cluster access
- [ ] Add rate limiting
- [ ] Log all API requests

**Implementation**:
```bash
# Check why Builder API isn't running
systemctl --user status builder-api.service
# Fix and restart
# Test endpoints
curl http://localhost:9000/api/v1/health
```

#### 2.2 MCP Server Services
**Status**: Installed but not running as services
**Priority**: HIGH
**Tasks**:
- [ ] Create systemd services for MCP servers:
  - `enhanced-memory-mcp.service` (port 8101)
  - `agent-runtime-mcp.service` (port 8102)
  - `ember-mcp.service` (port 8300)
- [ ] Configure auto-start on boot
- [ ] Set up health monitoring
- [ ] Configure memory limits
- [ ] Set up log rotation

**Implementation**:
```bash
# Create systemd service units
# Enable and start all MCP services
# Verify Claude Code can connect
```

#### 2.3 Heartbeat & Health Reporting
**Status**: Not configured
**Priority**: HIGH
**Tasks**:
- [ ] Create heartbeat service that reports to orchestrator
- [ ] Send status every 30 seconds to `http://192.168.1.16:8200/heartbeat`
- [ ] Include in heartbeat:
  - Node ID, status, load average
  - Queue status (active/queued tasks)
  - Resource usage (CPU, memory, disk)
  - Service health (Redis, Qdrant, API)
  - Build cache statistics
- [ ] Implement exponential backoff on failure
- [ ] Alert on heartbeat failure

**Implementation**:
```python
# Create /home/marc/agentic-system/services/builder_heartbeat.py
# Send periodic status updates to orchestrator
# Configure as systemd service
```

---

### Phase 3: Storage & Artifacts (Priority: HIGH)

#### 3.1 Shared Storage Mount
**Status**: Not mounted
**Priority**: HIGH
**Tasks**:
- [ ] Mount orchestrator's shared storage via SMB
- [ ] Mount point: `/mnt/orchestrator-workspace`
- [ ] Source: `//192.168.1.16/agentic-system`
- [ ] Configure auto-mount on boot (`/etc/fstab`)
- [ ] Set up credentials securely
- [ ] Test read/write access
- [ ] Create workspace directories:
  - `/mnt/orchestrator-workspace/build-queue/`
  - `/mnt/orchestrator-workspace/artifacts/`
  - `/mnt/orchestrator-workspace/shared-cache/`

**Implementation**:
```bash
# Create mount point
sudo mkdir -p /mnt/orchestrator-workspace

# Create SMB credentials file
sudo tee /etc/samba/orchestrator-creds << EOF
username=marc
password=<password>
domain=WORKGROUP
EOF
sudo chmod 600 /etc/samba/orchestrator-creds

# Add to /etc/fstab
//192.168.1.16/agentic-system /mnt/orchestrator-workspace cifs credentials=/etc/samba/orchestrator-creds,uid=marc,gid=marc 0 0

# Mount
sudo mount -a
```

#### 3.2 Artifact Management System
**Status**: Not implemented
**Priority**: MEDIUM
**Tasks**:
- [ ] Create artifact storage structure
- [ ] Implement artifact versioning
- [ ] Add artifact metadata (build info, checksums)
- [ ] Create artifact delivery API endpoints
- [ ] Set up artifact retention policies
- [ ] Implement artifact cleanup (30-day retention)
- [ ] Create artifact indexing for quick retrieval

**Storage Structure**:
```
/home/marc/agentic-system/artifacts/
├── {task_id}/
│   ├── metadata.json
│   ├── build.log
│   ├── artifacts/
│   │   ├── binary
│   │   ├── packages/
│   │   └── containers/
│   └── checksums.sha256
```

---

### Phase 4: Monitoring & Observability (Priority: MEDIUM)

#### 4.1 Prometheus Metrics
**Status**: Not installed
**Priority**: MEDIUM
**Tasks**:
- [ ] Install Prometheus
- [ ] Configure scraping:
  - Builder API metrics (port 9000)
  - Redis exporter (port 6379)
  - Qdrant metrics (port 6333)
  - Node exporter (system metrics)
  - Custom build metrics
- [ ] Set 30-day retention
- [ ] Create alerting rules:
  - Queue backlog > 10 tasks
  - Build failure rate > 20%
  - Disk usage > 80%
  - Service down
- [ ] Configure remote write to orchestrator (optional)

#### 4.2 Loki Log Aggregation
**Status**: Not installed
**Priority**: MEDIUM
**Tasks**:
- [ ] Install Loki
- [ ] Configure Promtail to ship logs:
  - Builder API logs
  - Task queue worker logs
  - Build execution logs
  - System logs (journald)
- [ ] Set 7-day retention
- [ ] Create log parsing rules
- [ ] Set up log-based alerts

#### 4.3 Grafana Dashboards
**Status**: Not installed
**Priority**: MEDIUM
**Tasks**:
- [ ] Install Grafana
- [ ] Configure Prometheus data source
- [ ] Configure Loki data source
- [ ] Create Builder dashboard:
  - Queue metrics (active, queued, completed)
  - Build success/failure rates
  - Build duration trends
  - Cache hit rates
  - Resource utilization
  - Service health status
- [ ] Create alerting dashboard
- [ ] Share dashboards with orchestrator

---

### Phase 5: Advanced Integration (Priority: LOW)

#### 5.1 Service Discovery (Avahi/mDNS)
**Status**: Avahi running but not advertising Builder service
**Priority**: LOW
**Tasks**:
- [ ] Create Avahi service file for Builder
- [ ] Advertise `_agentic-builder._tcp` service
- [ ] Include TXT records:
  - node_id=macpro51
  - node_type=builder
  - capabilities=build,test,container,benchmark
  - api_port=9000
  - queue_port=6379
- [ ] Verify discovery from orchestrator

**Implementation**:
```xml
<!-- /etc/avahi/services/agentic-builder.service -->
<service>
  <type>_agentic-builder._tcp</type>
  <port>9000</port>
  <txt-record>node_id=macpro51</txt-record>
  <txt-record>node_type=builder</txt-record>
  <txt-record>capabilities=build,test,container,benchmark</txt-record>
</service>
```

#### 5.2 Webhook Callback System
**Status**: Not implemented
**Priority**: LOW
**Tasks**:
- [ ] Add callback URL support to task queue
- [ ] Implement HTTP POST on task completion
- [ ] Include in callback:
  - Task ID, status, duration
  - Build output summary
  - Artifact locations
  - Error messages (if failed)
- [ ] Implement retry logic with exponential backoff
- [ ] Log all callbacks
- [ ] Support custom headers/authentication

#### 5.3 Cluster Memory Synchronization
**Status**: Installed but not syncing
**Priority**: LOW
**Tasks**:
- [ ] Configure enhanced-memory cluster sync
- [ ] Sync Builder memories to orchestrator every 5 minutes
- [ ] Use conflict resolution: orchestrator wins
- [ ] Implement delta sync (only changed entities)
- [ ] Monitor sync errors
- [ ] Create sync health check

#### 5.4 Advanced Build Features
**Status**: Future enhancements
**Priority**: LOW
**Tasks**:
- [ ] Distributed compilation (distcc/icecream)
- [ ] GPU-accelerated builds (use GTX 680)
- [ ] Build artifact caching beyond ccache/sccache
- [ ] Incremental builds tracking
- [ ] Build dependency graphing
- [ ] Parallel pipeline execution

---

## Implementation Priority Matrix

### Must Have (Week 1)
1. **Fix Builder API** - Critical for orchestrator communication
2. **Start MCP services** - Required for memory and runtime
3. **Mount shared storage** - Required for artifact delivery
4. **Heartbeat service** - Required for cluster health

### Should Have (Week 2)
5. **Artifact management system** - Needed for production builds
6. **Webhook callbacks** - Orchestrator needs notifications
7. **Service discovery** - Proper cluster integration
8. **Monitoring stack** - Observability and debugging

### Nice to Have (Week 3+)
9. **Cluster memory sync** - Enhanced coordination
10. **Advanced build features** - Performance optimization
11. **Build analytics** - Metrics and insights
12. **Auto-scaling** - Dynamic resource allocation

---

## Success Criteria

### Phase 2 Complete When:
- [ ] Builder API responds to all health checks
- [ ] All MCP servers running as systemd services
- [ ] Heartbeat sending status every 30s
- [ ] Shared storage mounted and accessible

### Phase 3 Complete When:
- [ ] Artifacts stored with proper structure
- [ ] Artifacts retrievable via API
- [ ] Artifact retention working
- [ ] Shared cache operational

### Phase 4 Complete When:
- [ ] Prometheus scraping all metrics
- [ ] Loki receiving all logs
- [ ] Grafana dashboards operational
- [ ] Alerts configured and firing

### Phase 5 Complete When:
- [ ] Service discovery functional
- [ ] Webhooks delivering to orchestrator
- [ ] Cluster memory syncing
- [ ] All advanced features operational

---

## Resource Requirements

**Disk Space**:
- Monitoring stack: ~5GB (Prometheus + Loki + Grafana)
- Artifacts storage: 50GB initial (expandable)
- Build cache: 40GB (ccache 20GB + sccache 20GB)
- Shared cache: 20GB
- Total: ~115GB (have 930GB available ✅)

**Memory**:
- Prometheus: ~500MB
- Loki: ~200MB
- Grafana: ~150MB
- MCP servers: ~150MB (3 x 50MB)
- Existing services: ~1GB
- Total: ~2GB (have 126GB available ✅)

**Network**:
- Heartbeat: ~1KB every 30s (~3MB/day)
- Metrics: ~10MB/day
- Logs: ~50MB/day
- Artifact transfers: Variable (10-100MB per build)
- Total: ~100MB/day + builds

---

## Risk Assessment

**High Risk**:
- Builder API failure could block orchestrator integration
- Shared storage mount failure prevents artifact delivery
- MCP server failures break memory/runtime functionality

**Medium Risk**:
- Monitoring stack failure reduces observability
- Heartbeat failure triggers false node-down alerts
- Service discovery issues cause connection problems

**Low Risk**:
- Webhook failures (orchestrator can poll instead)
- Cluster sync delays (eventual consistency OK)
- Advanced features (nice-to-have, not critical)

**Mitigation**:
- Comprehensive health checks
- Fallback mechanisms (telnet, direct API calls)
- Automated recovery scripts
- Good logging and alerting

---

## Next Actions

### Immediate (Today):
1. Fix Builder API and get it running
2. Start MCP servers as systemd services
3. Configure and test heartbeat service
4. Mount shared storage from orchestrator

### Short-term (This Week):
5. Implement artifact management
6. Set up webhook callbacks
7. Configure Avahi service discovery
8. Deploy monitoring stack basics

### Medium-term (Next 2 Weeks):
9. Complete monitoring dashboards
10. Implement cluster memory sync
11. Add advanced build features
12. Create comprehensive runbooks

---

## Estimated Timeline

- **Phase 2 (Service Layer)**: 2-3 days
- **Phase 3 (Storage & Artifacts)**: 2-3 days
- **Phase 4 (Monitoring)**: 3-4 days
- **Phase 5 (Advanced)**: 1-2 weeks

**Total**: 2-3 weeks to full production readiness

---

**Current Phase**: Phase 2.1 - Fixing Builder API
**Next Milestone**: All Phase 2 tasks complete (Service Layer operational)
**Goal**: Fully integrated Builder node ready for production workloads from Orchestrator
