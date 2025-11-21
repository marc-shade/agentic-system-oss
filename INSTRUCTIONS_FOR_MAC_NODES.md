# Quick Instructions: Deploy GitMQ on Your Mac

**For**: mac-studio and macbook-air
**Status**: macpro51 is already running and ready ✅

---

## Option 1: One-Line Bootstrap (Recommended)

Open **Terminal** on your Mac and run this **single command**:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- $(hostname | cut -d. -f1)
```

This will:
- Detect your Mac's hostname (mac-studio or macbook-air)
- Install all dependencies
- Download scripts
- Set up directories
- Create helper scripts

Then start the daemon:
```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

---

## Option 2: Manual Deployment Script

If you prefer to review the script first:

### Step 1: Download the deployment script

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/DEPLOY_ON_THIS_MAC.sh -o ~/deploy.sh
chmod +x ~/deploy.sh
```

### Step 2: Review the script (optional)

```bash
cat ~/deploy.sh
```

### Step 3: Run the deployment

```bash
bash ~/deploy.sh
```

### Step 4: Start the daemon

```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

---

## Verify It's Working

### Check daemon is running

```bash
ps aux | grep github_node_daemon | grep -v grep
```

Should show:
```
marc  <PID>  python3 github_node_daemon.py --node-id <your-node> ...
```

### Check heartbeat

```bash
cd ~/agentic-system/cluster-deployment
./send-task.sh $(hostname | cut -d. -f1) --check-heartbeat
```

Should show:
```
✅ Heartbeat found for <your-node>
   Status: online
   Last update: 2025-11-16T...
```

### View logs

```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

Should see polling messages every 30 seconds:
```
[timestamp] INFO - Checking for new tasks...
```

---

## Test Cluster Communication

### From your Mac, send a task to macpro51

```bash
cd ~/agentic-system/cluster-deployment
./send-task.sh macpro51 health_check
```

Wait 30-60 seconds, then check results:
```bash
./send-task.sh macpro51 --check-results
```

Should show health stats from macpro51.

### From macpro51, a task will be sent to you

The macpro51 node has already sent a health check task to mac-studio. When you start your daemon, it will automatically:
1. Detect the pending task (within 30 seconds)
2. Execute it
3. Post results to GitHub

Check your daemon logs to see this happen:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

---

## Common Issues

### "Authentication failed" when cloning

**Fix**: Enter your GitHub credentials:
- Username: Your GitHub username
- Password: **Your GitHub Personal Access Token** (NOT your password!)

To create a PAT:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `repo` (full control)
4. Copy the token and use it as your password

### Daemon not starting

**Check Python**:
```bash
python3 --version  # Should be 3.8+
```

**Check dependencies**:
```bash
pip3 install psutil GitPython
```

### Tasks not being detected

**Verify daemon is polling**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log | grep "Checking for new tasks"
```

Should see a line every 30 seconds.

---

## Quick Commands Reference

**Start daemon**:
```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

**Stop daemon**:
```bash
./stop-daemon.sh
```

**Check heartbeat**:
```bash
./send-task.sh <node-id> --check-heartbeat
```

**Send task**:
```bash
./send-task.sh <target-node> health_check
```

**Check results**:
```bash
./send-task.sh <target-node> --check-results
```

**View logs**:
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

---

## Node IDs

- **mac-studio**: Orchestrator node
- **macbook-air**: Researcher node
- **macpro51**: Builder node (already running ✅)

---

## What Happens After Deployment

1. **Daemon starts polling** GitHub every 30 seconds for new tasks
2. **Heartbeat posts** to GitHub every 5 minutes with system health
3. **Pending tasks execute** automatically (mac-studio has one waiting!)
4. **Results post** to GitHub for retrieval by other nodes

You're joining a cluster that communicates entirely through GitHub - no VPN, no firewall config, no static IPs needed!

---

## Need Help?

**Documentation**:
- Quick Start: https://github.com/marc-shade/agentic-cluster-comms/blob/main/docs/QUICK_START.md
- Full Guide: https://github.com/marc-shade/agentic-cluster-comms/blob/main/docs/SCOTT_NODE_ONBOARDING.md

**Logs**:
- `~/agentic-system/logs/github-daemon.log`

**macpro51 status**:
- Daemon running: PID 2963168 ✅
- Heartbeat active: Every 5 minutes ✅
- Ready to receive tasks: Yes ✅

---

**You're 1 command away from joining the cluster!** 🚀
