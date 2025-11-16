# Deploy 3-Node Local Cluster - Step-by-Step Checklist

**Date**: 2025-11-16
**Current Status**: macpro51 fully operational ✅
**Next Steps**: Deploy to mac-studio and macbook-air

---

## ✅ macpro51 (Builder Node) - COMPLETE

- [x] GitMQ daemon running (PID: 2963168)
- [x] Heartbeat posting every 5 minutes
- [x] Task detection working
- [x] Task execution verified
- [x] Results posting confirmed
- [x] All systems tested and operational

**Current Heartbeat**:
```json
{
  "node_id": "macpro51",
  "status": "online",
  "cpu_percent": 8.2,
  "memory_percent": 13.5,
  "disk_percent": 27.5,
  "uptime_seconds": 74195
}
```

---

## 🔄 mac-studio (Orchestrator Node) - PENDING

### Step 1: Run Bootstrap Script

Open Terminal on **mac-studio** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- mac-studio
```

**What this does**:
- Detects macOS platform
- Installs Python dependencies
- Clones agentic-cluster-comms repository
- Creates helper scripts
- Sets up LaunchAgent for auto-start

**Expected output**:
```
✅ Bootstrap complete for mac-studio!

Next steps:
1. Start daemon: cd ~/agentic-system/cluster-deployment && ./start-daemon.sh
2. Check status: ./send-task.sh mac-studio --check-heartbeat
```

### Step 2: Start the Daemon

```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

**Verify it's running**:
```bash
ps aux | grep github_node_daemon | grep -v grep
```

Should show:
```
marc  <PID> python3 github_node_daemon.py --node-id mac-studio ...
```

### Step 3: Check Heartbeat

```bash
./send-task.sh mac-studio --check-heartbeat
```

**Expected output**:
```
✅ Heartbeat found for mac-studio
   Status: online
   Last update: 2025-11-16T...
```

### Step 4: Process Pending Task

The daemon should automatically detect and process the health_check task that macpro51 already sent.

**Check logs** (wait ~30 seconds):
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

Look for:
```
[timestamp] INFO - Found new task: 19b2a825 - health_check task
[timestamp] INFO - Executing task: ...
[timestamp] INFO - Posted result for task 19b2a825
```

### Step 5: Verify Results

From mac-studio:
```bash
./send-task.sh mac-studio --check-results
```

Should show the health check result:
```json
{
  "task_id": "dbc5de6e-...",
  "node_id": "mac-studio",
  "status": "success",
  "health": { ... }
}
```

---

## 🔄 macbook-air (Researcher Node) - PENDING

### Step 1: Run Bootstrap Script

Open Terminal on **macbook-air** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- macbook-air
```

### Step 2: Start the Daemon

```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

### Step 3: Check Heartbeat

```bash
./send-task.sh macbook-air --check-heartbeat
```

---

## 🧪 Test 3-Node Cluster Communication

Once all three nodes have daemons running, test bidirectional communication.

### From macpro51:

```bash
cd /mnt/agentic-system/cluster-deployment

# Send tasks to all nodes
python3 submit_cluster_task.py --to mac-studio --type health_check
python3 submit_cluster_task.py --to macbook-air --type health_check
python3 submit_cluster_task.py --to macpro51 --type health_check

# Wait 30-60 seconds for processing

# Check all results
python3 submit_cluster_task.py --to mac-studio --check-results
python3 submit_cluster_task.py --to macbook-air --check-results
python3 submit_cluster_task.py --to macpro51 --check-results
```

### From mac-studio:

```bash
cd ~/agentic-system/cluster-deployment

# Send to other nodes
./send-task.sh macpro51 health_check
./send-task.sh macbook-air health_check

# Check results
./send-task.sh macpro51 --check-results
./send-task.sh macbook-air --check-results
```

### From macbook-air:

```bash
cd ~/agentic-system/cluster-deployment

# Send to other nodes
./send-task.sh mac-studio health_check
./send-task.sh macpro51 health_check

# Check results
./send-task.sh mac-studio --check-results
./send-task.sh macpro51 --check-results
```

---

## ✅ Success Criteria

All nodes should show:

- [x] **Daemon running**: `ps aux | grep github_node_daemon`
- [x] **Heartbeat posting**: Visible on GitHub heartbeat branch
- [x] **Tasks received**: Can receive tasks from other nodes
- [x] **Tasks executed**: Health checks complete successfully
- [x] **Results posted**: Results committed to GitHub
- [x] **Results retrievable**: Can check results from any node

---

## 📊 Monitor Cluster Health

### Check All Heartbeats

From any node:
```bash
./send-task.sh mac-studio --check-heartbeat
./send-task.sh macbook-air --check-heartbeat
./send-task.sh macpro51 --check-heartbeat
```

### View GitHub Branches

Go to: https://github.com/marc-shade/agentic-cluster-comms

Click "branches" - should see:
- `heartbeat` - All nodes posting status
- `tasks/mac-studio/` - Tasks for mac-studio
- `tasks/macbook-air/` - Tasks for macbook-air
- `tasks/macpro51/` - Tasks for macpro51
- `results/mac-studio/` - Results from mac-studio
- `results/macbook-air/` - Results from macbook-air
- `results/macpro51/` - Results from macpro51

### View Daemon Logs

**mac-studio**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

**macbook-air**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

**macpro51**:
```bash
tail -f /mnt/agentic-system/logs/github-daemon.log
```

---

## 🔧 Troubleshooting

### Daemon Not Starting

**Check Python**:
```bash
python3 --version  # Should be 3.8+
which python3
```

**Check Dependencies**:
```bash
pip3 list | grep -E 'psutil|GitPython'
```

**If missing**:
```bash
pip3 install psutil GitPython
```

### Authentication Errors

**Clear credentials**:
```bash
rm ~/.git-credentials
```

**Restart daemon** - will prompt for credentials:
- Username: Your GitHub username
- Password: Your Personal Access Token (NOT your password!)

### Tasks Not Detected

**Verify daemon is polling**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log | grep "Checking for new tasks"
```

Should see line every 30 seconds.

**Check branch exists**:
```bash
cd ~/agentic-system/agentic-cluster-comms
git branch -a | grep tasks/$(hostname | cut -d. -f1)
```

### Results Not Appearing

**Check daemon logs**:
```bash
grep "Posted result" ~/agentic-system/logs/github-daemon.log
```

**Verify on GitHub**:
```bash
cd ~/agentic-system/agentic-cluster-comms
git fetch --all
git checkout results/$(hostname | cut -d. -f1)
ls -la
```

---

## 🎯 After 3-Node Cluster is Working

Once all three local nodes are communicating:

1. **Verify end-to-end latency** (should be 10-35 seconds)
2. **Monitor for 1 hour** to ensure stability
3. **Test LaunchAgent auto-start** (reboot one node, verify daemon restarts)
4. **Invite Scott to GitHub repo**
5. **Send Scott the bootstrap command**
6. **Test cross-network communication** with Scott's remote node

---

## 📋 Quick Command Reference

**Start daemon**:
```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

**Send task**:
```bash
./send-task.sh <node-id> health_check
```

**Check results**:
```bash
./send-task.sh <node-id> --check-results
```

**Check heartbeat**:
```bash
./send-task.sh <node-id> --check-heartbeat
```

**View logs**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

**Stop daemon**:
```bash
pkill -f github_node_daemon
```

---

## 🎉 Current Status Summary

- ✅ **macpro51**: Fully operational, daemon running, tested end-to-end
- ⏳ **mac-studio**: Bootstrap script ready, pending execution
- ⏳ **macbook-air**: Bootstrap script ready, pending execution
- ⏳ **Scott's node**: Onboarding documentation complete, awaiting invitation

**All code pushed to GitHub ✅**
**All documentation complete ✅**
**Testing verified on macpro51 ✅**

**Next Action**: Run bootstrap on mac-studio and macbook-air to complete local cluster deployment.
