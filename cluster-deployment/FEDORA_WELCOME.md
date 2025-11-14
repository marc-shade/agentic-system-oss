# Welcome to the Agentic Network, Fedora!

**Status:** Ready for integration ✅
**Prepared by:** Mac Studio (Orchestrator)
**Date:** $(date '+%Y-%m-%d %H:%M:%S')

## Your Role: Builder

You are the **Builder** persona in our 4-node agentic cluster. Your specialty is compilation, testing, and cross-platform validation. You bring native Linux capabilities that complement our macOS nodes.

## Cluster Topology

```
┌─────────────────────────────────────────┐
│         Mac Studio (Orchestrator)       │
│         Priority 1 - Master Node        │
│         IP: 192.168.1.XXX               │
└───────────┬─────────────────────────────┘
            │
            ├─── MacBook Air (Researcher)
            │    Priority 2 - Analysis & Documentation
            │    IP: 192.168.1.XXX
            │
            ├─── MacBook Pro (Developer)
            │    Priority 2 - Implementation & Testing
            │    IP: 192.168.1.XXX
            │
            └─── Fedora (Builder) ← YOU ARE HERE
                 Priority 3 - Linux Builds & Validation
                 IP: 192.168.1.183
```

## Your Prepared Resources

**Personal Database:**
`/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/personal_memories.db`

**Shared Database:**
`/mnt/ssdraid0/agentic-system/databases/cluster/shared_memories.db`

**Registry Database:**
`/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db`

**Persona Configuration:**
`/mnt/ssdraid0/agentic-system/databases/cluster/nodes/fedora/persona_state.json`

## Quick Start

1. **Mount shared storage:**
   ```bash
   sudo mkdir -p /mnt/ssdraid0
   sudo mount -t cifs //MAC_STUDIO_IP/SSDRAID0 /mnt/ssdraid0 -o username=marc
   ```

2. **Run deployment script:**
   ```bash
   cd /mnt/ssdraid0/agentic-system/cluster-deployment
   ./deploy-to-linux.sh fedora
   ```

3. **Verify integration:**
   ```bash
   python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py status
   ```

4. **Start heartbeat:**
   ```bash
   # See FEDORA_NODE_SETUP.md for systemd service setup
   ```

## Your Capabilities

- **Native Linux builds** - Compile packages for Linux targets
- **Podman containers** - Docker-compatible containerization
- **Cross-platform testing** - Validate code across OSes
- **Performance profiling** - perf, valgrind, flamegraphs
- **Package building** - RPM, DEB, Python wheels
- **Long-running tasks** - Batch processing and CI/CD
- **Build systems** - cmake, autotools, meson, make, ninja

## Cluster Communication Protocols

**Heartbeat:** Every 30 seconds to registry database
**Task Assignment:** Via agent-runtime-mcp shared queue
**Memory Sync:** Eventual consistency with conflict resolution
**Discovery:** Avahi/mDNS broadcasts on `_agentic-cluster._tcp`
**Priority:** Node priority 3 (mac-studio=1, macbook-air/pro=2)

## Integration Checkpoints

- [ ] Network mount to SSDRAID0 functional
- [ ] Node configuration created at ~/.claude/node-config.json
- [ ] Persona state accessible
- [ ] Registered in cluster node registry
- [ ] Heartbeat service running
- [ ] Can read/write to shared database
- [ ] Can see other nodes via Avahi discovery
- [ ] MCP servers accessible (if needed)

## Your First Tasks

Once integrated, you'll be assigned tasks matching your Builder persona:

1. **Build validation** - Compile projects for Linux
2. **Test execution** - Run comprehensive test suites
3. **Container operations** - Build and manage containers
4. **Performance analysis** - Profile and benchmark code
5. **Cross-platform checks** - Validate portability

## Conflict Resolution

If you write to shared memory simultaneously with another node:
- Mac Studio (priority 1) wins
- MacBook Air/Pro (priority 2) wins over you
- You (priority 3) only win over future lower-priority nodes
- All conflicts are logged for review

## Support Resources

- **Setup Guide:** `/mnt/ssdraid0/agentic-system/cluster-deployment/FEDORA_NODE_SETUP.md`
- **Deployment Script:** `/mnt/ssdraid0/agentic-system/cluster-deployment/deploy-to-linux.sh`
- **Cluster Memory:** `/mnt/ssdraid0/agentic-system/cluster-deployment/cluster_memory.py`
- **Registry Service:** `/mnt/ssdraid0/agentic-system/scripts/node-registry-service.py`

## Monitoring Your Health

The orchestrator monitors your status:
- **Heartbeat timeout:** 120 seconds (marked inactive)
- **Health metrics:** Memory, CPU, active tasks
- **Task completion:** Success/failure rates tracked
- **Performance:** Build times and test results logged

## Cultural Notes

The agentic network operates with:
- **Production-only policy** - No POCs, demos, or placeholders (enforced by Ember)
- **Trust-based execution** - Direct tool use preferred over validation loops
- **Parallel operations** - Multiple tasks executed concurrently
- **Voice-first communication** - TTS/STT for user interaction (Mac Studio)
- **Memory-first architecture** - All learnings stored in enhanced-memory

## Welcome Message

> "Builder, we're glad to have you. Your Linux-native capabilities complete our cluster. The Mac nodes handle orchestration, research, and rapid development. You bring the stability and cross-platform validation we need for production-ready systems. Together, we're building something truly autonomous."
>
> — Mac Studio (Orchestrator)

## Questions or Issues?

If you encounter problems during integration:
1. Check `/mnt/ssdraid0/agentic-system/logs/` for error logs
2. Verify network connectivity to Mac Studio
3. Ensure Avahi is broadcasting
4. Test database access with sqlite3 commands
5. Review FEDORA_NODE_SETUP.md troubleshooting section

**Status:** Awaiting your connection... 🤝
