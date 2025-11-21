# Local Nodes Setup Guide (mac-studio & macbook-air)

**For**: Setting up GitMQ daemons on your other Mac nodes
**Tested on**: macpro51 (fully working ✅)

---

## ✅ Confirmed Working on macpro51

The GitMQ system has been tested and confirmed working:
- ✅ Daemon polls every 30 seconds
- ✅ Tasks detected within 30 seconds
- ✅ Health checks execute successfully
- ✅ Results posted to GitHub
- ✅ Heartbeat posting every 5 minutes

**Example Results**:
```json
{
  "task_id": "dbc5de6e-6a3f-47c6-b5ac-91e7c9b5fae",
  "node_id": "macpro51",
  "task_type": "health_check",
  "status": "success",
  "health": {
    "cpu_percent": 10.7,
    "memory_percent": 13.2,
    "disk_percent": 27.5,
    "uptime_seconds": 73825.76
  }
}
```

---

## 🚀 Setup for mac-studio (Orchestrator Node)

### Quick Setup

Open Terminal on mac-studio and run:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- mac-studio
```

### After Bootstrap

1. **Start the daemon**:
   ```bash
   cd ~/agentic-system/cluster-deployment
   ./start-daemon.sh
   ```

2. **Verify it's working**:
   ```bash
   # Check heartbeat
   ./send-task.sh mac-studio --check-heartbeat

   # Should show system stats
   ```

3. **Test receiving the task we already sent**:
   ```bash
   # Wait 30 seconds for daemon to poll
   # Then check logs:
   tail -f ~/agentic-system/logs/github-daemon.log

   # Look for:
   # [timestamp] INFO - Found new task: 19b2a825 - health_check task
   # [timestamp] INFO - Executing task: ...
   # [timestamp] INFO - Posted result for task 19b2a825
   ```

4. **Check results from macpro51**:
   ```bash
   ./send-task.sh mac-studio --check-results
   ```

---

## 🚀 Setup for macbook-air (Researcher Node)

### Quick Setup

Open Terminal on macbook-air and run:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- macbook-air
```

### After Bootstrap

1. **Start the daemon**:
   ```bash
   cd ~/agentic-system/cluster-deployment
   ./start-daemon.sh
   ```

2. **Test sending a task to macpro51**:
   ```bash
   ./send-task.sh macpro51 health_check
   ```

3. **Wait 30 seconds, then check results**:
   ```bash
   ./send-task.sh macpro51 --check-results
   ```

---

## 🔄 Run as LaunchAgent (Background Service)

After verifying the daemon works in foreground, set it up to run automatically.

The bootstrap script already created the LaunchAgent plist file. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.agentic.github-daemon.plist
```

**Verify it's running**:
```bash
launchctl list | grep github-daemon
```

**Check logs**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

**Stop if needed**:
```bash
launchctl unload ~/Library/LaunchAgents/com.agentic.github-daemon.plist
```

---

## 🧪 Testing Inter-Node Communication

Once all nodes have daemons running, test the full cluster:

### From mac-studio:
```bash
# Send tasks to all nodes
./send-task.sh macpro51 health_check
./send-task.sh macbook-air health_check
./send-task.sh mac-studio health_check

# Wait 30-60 seconds, then check all results
./send-task.sh macpro51 --check-results
./send-task.sh macbook-air --check-results
./send-task.sh mac-studio --check-results
```

### From macbook-air:
```bash
# Test sending to other nodes
./send-task.sh mac-studio health_check
./send-task.sh macpro51 health_check

# Check results
./send-task.sh mac-studio --check-results
./send-task.sh macpro51 --check-results
```

### From macpro51:
```bash
# Test receiving tasks (already working!)
./send-task.sh mac-studio health_check
./send-task.sh macbook-air health_check

# Check results
./send-task.sh mac-studio --check-results
./send-task.sh macbook-air --check-results
```

---

## 📊 Monitor All Nodes

### Check All Heartbeats

```bash
./send-task.sh mac-studio --check-heartbeat
./send-task.sh macbook-air --check-heartbeat
./send-task.sh macpro51 --check-heartbeat
```

Should show:
- CPU, memory, disk usage
- Uptime
- Last update timestamp
- Status: online

### View Daemon Logs

```bash
# Real-time logs
tail -f ~/agentic-system/logs/github-daemon.log

# Search logs
grep "task" ~/agentic-system/logs/github-daemon.log
grep "ERROR" ~/agentic-system/logs/github-daemon.log
```

---

## 🔍 Verify on GitHub

1. Go to: https://github.com/marc-shade/agentic-cluster-comms
2. Click "branches" tab
3. You should see:
   - `heartbeat` - All nodes posting
   - `tasks/{node-id}/` - Task branches for each node
   - `results/{node-id}/` - Results from each node

4. Check heartbeat branch:
   - `heartbeat/mac-studio.json` - mac-studio's status
   - `heartbeat/macbook-air.json` - macbook-air's status
   - `heartbeat/macpro51.json` - macpro51's status

---

## 🐛 Troubleshooting

### Daemon not starting
**Check**:
```bash
# Verify prerequisites
python3 --version  # Should be 3.8+
pip3 list | grep psutil  # Should be installed

# Try running directly
cd ~/agentic-system/cluster-deployment
python3 github_node_daemon.py --node-id <your-node-id> --repo marc-shade/agentic-cluster-comms
```

### Tasks not being detected
**Check**:
```bash
# Verify daemon is running
ps aux | grep github_node_daemon

# Check logs
tail -f ~/agentic-system/logs/github-daemon.log

# Should see every 30 seconds:
# [timestamp] INFO - Checking for new tasks...
```

### Authentication errors
**Fix**:
```bash
# Clear credentials
rm ~/.git-credentials

# Restart daemon - it will prompt for credentials
./start-daemon.sh

# Use:
# Username: your GitHub username
# Password: Your Personal Access Token (NOT password!)
```

---

## ✅ Success Checklist

**For each node**:
- [ ] Bootstrap script completed
- [ ] Daemon running (foreground or background)
- [ ] Heartbeat visible on GitHub
- [ ] Can receive tasks from other nodes
- [ ] Can send tasks to other nodes
- [ ] Results posted successfully
- [ ] LaunchAgent configured (optional)

---

## 📁 Directory Structure (After Setup)

```
~/agentic-system/
├── cluster-deployment/
│   ├── github_node_daemon.py       # Daemon
│   ├── submit_cluster_task.py      # Task submitter
│   ├── start-daemon.sh             # Start script
│   └── send-task.sh                # Helper
├── agentic-cluster-comms/          # Cloned on first run
│   ├── tasks/{node-id}/
│   ├── results/{node-id}/
│   └── heartbeat/
├── logs/
│   └── github-daemon.log           # Daemon logs
└── databases/
    └── cluster/
        ├── nodes/{node-id}/
        └── shared_memories.db

~/Library/LaunchAgents/
└── com.agentic.github-daemon.plist # Auto-start service
```

---

## 🎯 Next Steps

Once all 3 local nodes are running:

1. **Verify cluster communication** between all nodes
2. **Test advanced tasks**:
   - Code execution
   - File operations
   - Multi-node workflows

3. **Monitor cluster health**:
   - Check heartbeats regularly
   - Review daemon logs
   - Monitor task queue on GitHub

4. **Add Scott's remote node**:
   - Scott runs same bootstrap with `scott-remote` node ID
   - Tests communication with all 3 local nodes

---

## 📞 Support

- **Logs**: `~/agentic-system/logs/github-daemon.log`
- **Config**: `~/.claude/node-config.json`
- **GitHub Repo**: https://github.com/marc-shade/agentic-cluster-comms
- **Documentation**: See docs/ directory

---

**The GitMQ system is tested and working!** 🎉

Just bootstrap the other nodes and you'll have a fully operational 3-node cluster ready for Scott to join remotely!
