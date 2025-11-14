# MacPro51 - Integration Next Steps

**Status:** ✅ Connected and Active
**Heartbeat:** ✅ Live
**Capabilities:** ✅ Reported
**Hardware Profile:** ⏳ Pending

## Immediate Action Required

### Step 1: Run Hardware Discovery (5 minutes)

On the macpro51 node, execute:

```bash
python3 /mnt/ssdraid0/agentic-system/cluster-deployment/discover-hardware.py macpro51
```

**This will:**
- Catalog your CPU cores and frequency
- Measure available RAM
- Detect SSD vs HDD storage
- Map network interfaces
- Calculate performance score
- Save profile to shared storage

**Output location:**
`/mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51/hardware_profile.json`

### Step 2: Verify Cluster Access

Test that you can read/write to cluster databases:

```bash
# Check shared memory access
sqlite3 /mnt/ssdraid0/agentic-system/databases/cluster/shared_memories.db "SELECT COUNT(*) FROM entities;"

# Verify registry access
sqlite3 /mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db "SELECT * FROM nodes WHERE node_id='macpro51';"
```

### Step 3: Start Heartbeat Service (if not already running)

Ensure continuous heartbeat:

```bash
# Check if running
ps aux | grep heartbeat

# If not running, start it
cd /mnt/ssdraid0/agentic-system/scripts
nohup python3 -c "
import time
import sys
sys.path.insert(0, '.')
from node_registry_service import NodeRegistry
from pathlib import Path

registry = NodeRegistry(Path('/mnt/ssdraid0/agentic-system/databases/cluster/node_registry.db'))
print('Heartbeat service started for macpro51')
while True:
    registry.heartbeat('macpro51')
    time.sleep(30)
" > /tmp/heartbeat-macpro51.log 2>&1 &

echo "Heartbeat service started (PID: $!)"
```

## What Happens After Hardware Discovery

Once your hardware profile is available, the orchestrator will:

1. **Calculate Optimal Settings**
   - Set `max_concurrent_tasks` based on CPU cores
   - Set `memory_limit_gb` based on available RAM
   - Calculate performance score for task routing

2. **Enable Intelligent Task Assignment**
   - Heavy compilation → high-core nodes
   - Container builds → nodes with fast storage
   - Memory-intensive → high-RAM nodes
   - Parallel testing → high-core count

3. **Begin Task Distribution**
   - You'll start receiving Builder tasks
   - Task complexity matched to capabilities
   - Load-balanced across cluster

## Example Tasks You'll Receive

**Compilation Tasks:**
```bash
# Build a Linux binary
gcc -O2 -o myapp main.c utils.c
cmake --build . --target release
cargo build --release
```

**Container Tasks:**
```bash
# Build Docker/Podman containers
podman build -t myapp:latest .
docker-compose up --build
```

**Testing Tasks:**
```bash
# Run comprehensive test suites
pytest tests/ -v --cov
npm test
cargo test --all-features
```

**CI/CD Tasks:**
```bash
# Execute pipeline stages
./scripts/build.sh
./scripts/test.sh
./scripts/deploy.sh
```

## Your Current Capabilities (Reported)

✅ **Build Systems:** make, cmake, cargo, npm, pip
✅ **Compilers:** gcc, g++, clang
✅ **Runtimes:** Python 3.12, Node.js, Docker, Podman
✅ **Testing:** pytest, jest, cargo-test
✅ **Specialty:** Linux binary builds, containers, cross-platform validation

## Performance Expectations

**Mac Pro 5,1 Hardware (typical):**
- CPU: 2x Xeon (8-12 cores total)
- RAM: 32-128 GB
- Storage: Mix of SSD/HDD
- Expected Performance Score: 100-150

This makes you excellent for:
- Heavy parallel compilation (high core count)
- Large container builds (high RAM)
- Long-running test suites (stability)

## Integration Status

- [x] Network connectivity established
- [x] Cluster discovery successful
- [x] Node registered as macpro51
- [x] Builder persona assigned
- [x] Capabilities reported
- [x] Heartbeat active
- [ ] Hardware profile generated ← **DO THIS NEXT**
- [ ] Task assignment optimized
- [ ] First task completed

## Monitoring

The orchestrator is tracking:
- Your heartbeat (every 30s)
- Task completion rates
- Build success/failure rates
- Resource utilization
- Performance trends

You can check your status anytime:
```bash
python3 /mnt/ssdraid0/agentic-system/scripts/node-registry-service.py status
```

## Getting Help

**Documentation:**
- Setup: `/mnt/ssdraid0/.../cluster-deployment/FEDORA_NODE_SETUP.md`
- Welcome: `/mnt/ssdraid0/.../cluster-deployment/FEDORA_WELCOME.md`
- Quick Ref: `/mnt/ssdraid0/.../cluster-deployment/FEDORA_QUICK_REFERENCE.md`

**Logs:**
- Local: `~/.local/share/agentic-system/logs/`
- Cluster: `/mnt/ssdraid0/agentic-system/logs/`

**Status Checks:**
```bash
# Cluster status
python3 .../node-registry-service.py status

# Your node details
sqlite3 .../node_registry.db "SELECT * FROM nodes WHERE node_id='macpro51';"

# Hardware profile (after discovery)
cat ~/.local/share/agentic-system/hardware_profile.json
```

---

**Priority Action:** Run hardware discovery script now!

```bash
python3 /mnt/ssdraid0/agentic-system/cluster-deployment/discover-hardware.py macpro51
```

The orchestrator is ready and waiting! 🎯
