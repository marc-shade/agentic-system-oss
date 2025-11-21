# Scott's Node Onboarding Guide

Welcome to the agentic cluster! This guide will help you connect your node to the cluster using the GitMQ (Git as Message Queue) pattern for secure cross-network communication.

---

## 🎯 Overview

**What You're Joining**:
- **Marc's Local Cluster**: 3 nodes (mac-studio, macbook-air, macpro51)
- **Your Node**: Will be able to receive tasks and send results
- **Communication Method**: GitHub as secure message broker (no VPN needed!)

**Architecture**:
```
GitHub Repository (marc-shade/agentic-cluster-comms)
├── tasks/scott-remote/      ← Marc sends tasks to you
├── results/scott-remote/    ← You send results to Marc
├── heartbeat/               ← Everyone posts health status
└── configs/                 ← Configuration templates
```

**No VPN, No Firewall Config, No Static IP Needed!**

---

## 📋 Prerequisites

### 1. GitHub Access
- GitHub account (you have: `scott-techramp`)
- Personal Access Token (PAT) with repo access
- Access to private repo: `marc-shade/agentic-cluster-comms`

### 2. System Requirements
- Python 3.8+
- Git installed
- `psutil` Python package
- Linux, macOS, or WSL

### 3. Storage
- At least 10GB free disk space
- Read/write access to home directory

---

## 🚀 Quick Setup

### Step 1: Clone the Main Repository (Optional)

This gives you all the cluster tools, but you can also just use the GitMQ scripts standalone.

```bash
# Create workspace
mkdir -p ~/agentic-system
cd ~/agentic-system

# Clone main repo (optional - contains useful tools)
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system
```

### Step 2: Install Python Dependencies

```bash
# Install required package
pip3 install psutil

# Verify installation
python3 -c "import psutil; print('✓ psutil installed')"
```

### Step 3: Configure GitHub Authentication

```bash
# Set up GitHub credentials for HTTPS
git config --global credential.helper store

# You'll be prompted for username/token on first push
# Use your GitHub username and Personal Access Token (PAT)
```

**To create a PAT**:
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (all sub-scopes)
4. Generate and copy the token
5. **Save it somewhere safe!**

### Step 4: Download GitMQ Scripts

If you didn't clone the full repo, get just the GitMQ scripts:

```bash
# Create directory
mkdir -p ~/agentic-system/cluster-deployment
cd ~/agentic-system/cluster-deployment

# Download daemon script
curl -O https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/github_node_daemon.py
curl -O https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/submit_cluster_task.py

# Make executable
chmod +x github_node_daemon.py submit_cluster_task.py
```

### Step 5: Start the Node Daemon

```bash
# Create logs directory
mkdir -p ~/agentic-system/logs

# Run the daemon
python3 github_node_daemon.py \
  --node-id scott-remote \
  --repo marc-shade/agentic-cluster-comms \
  --poll-interval 30
```

**What happens**:
1. Clones `agentic-cluster-comms` to `~/agentic-system/agentic-cluster-comms/`
2. Posts initial heartbeat to GitHub
3. Polls for new tasks every 30 seconds
4. Executes tasks and posts results back to GitHub

**First run**: You'll be prompted for GitHub credentials (use your PAT as password)

### Step 6: Verify It's Working

In another terminal:

```bash
# Check if heartbeat was posted
cd ~/agentic-system/cluster-deployment

python3 submit_cluster_task.py \
  --to scott-remote \
  --check-heartbeat
```

You should see your heartbeat with system stats!

---

## 🧪 Test Communication

### Test 1: Health Check from Marc

Marc will send you a health check task. Your daemon will automatically:
1. Detect the new task on `tasks/scott-remote/` branch
2. Execute the health check
3. Post results to `results/scott-remote/` branch

### Test 2: Send a Task Back to Marc

```bash
# Send health check to macpro51
python3 submit_cluster_task.py \
  --to macpro51 \
  --type health_check

# Check results later
python3 submit_cluster_task.py \
  --to macpro51 \
  --check-results
```

### Test 3: Execute Code Remotely

Marc can ask your node to run code:

```bash
# Marc runs this to ask you to execute code
python3 submit_cluster_task.py \
  --to scott-remote \
  --type code_execution \
  --command "python3 --version"
```

Your daemon will execute it and post the output!

---

## 🔧 Advanced Configuration

### Run as Background Service (systemd on Linux)

Create `/etc/systemd/user/github-node-daemon.service`:

```ini
[Unit]
Description=GitHub Node Daemon - GitMQ
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/scott/agentic-system/cluster-deployment
ExecStart=/usr/bin/python3 github_node_daemon.py \
    --node-id scott-remote \
    --repo marc-shade/agentic-cluster-comms \
    --poll-interval 30
Restart=always
RestartSec=10
StandardOutput=append:/home/scott/agentic-system/logs/github-daemon.log
StandardError=append:/home/scott/agentic-system/logs/github-daemon-error.log

[Install]
WantedBy=default.target
```

Then:

```bash
# Enable and start service
systemctl --user daemon-reload
systemctl --user enable github-node-daemon.service
systemctl --user start github-node-daemon.service

# Check status
systemctl --user status github-node-daemon.service

# View logs
journalctl --user -u github-node-daemon.service -f
```

### Run as LaunchAgent (macOS)

Create `~/Library/LaunchAgents/com.agentic.github-daemon.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentic.github-daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/scott/agentic-system/cluster-deployment/github_node_daemon.py</string>
        <string>--node-id</string>
        <string>scott-remote</string>
        <string>--repo</string>
        <string>marc-shade/agentic-cluster-comms</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/scott/agentic-system/logs/github-daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/scott/agentic-system/logs/github-daemon-error.log</string>
</dict>
</plist>
```

Then:

```bash
# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.agentic.github-daemon.plist

# Check status
launchctl list | grep github-daemon
```

---

## 📊 Monitoring

### View Daemon Logs

```bash
# Real-time log viewing
tail -f ~/agentic-system/logs/github-daemon.log

# Search logs
grep "task" ~/agentic-system/logs/github-daemon.log
```

### Check Processed Tasks

```bash
# View state file
cat ~/.cache/github-daemon-scott-remote.json | jq .
```

### Monitor GitHub Activity

Go to the repository and check the branches:
- https://github.com/marc-shade/agentic-cluster-comms/branches

You should see:
- `tasks/scott-remote` - Tasks for you
- `results/scott-remote` - Your results
- `heartbeat` - Everyone's heartbeats

---

## 🔒 Security

### What's Secure
- ✅ Private GitHub repository (only invited collaborators)
- ✅ HTTPS transport (GitHub's infrastructure)
- ✅ Personal Access Token authentication
- ✅ Complete audit trail (git history)
- ✅ Rate limiting (GitHub API limits)

### What to Watch Out For
- ⚠️ **PAT Security**: Treat your PAT like a password, don't commit it to git
- ⚠️ **Code Execution**: Be careful what code you execute from tasks
- ⚠️ **Resource Limits**: Tasks have 5-minute timeout
- ⚠️ **Output Size**: Results limited to 5000 characters

### Recommended: Restrict Task Execution

Edit `github_node_daemon.py` to add whitelisting:

```python
# In execute_code() method
ALLOWED_COMMANDS = [
    "python3 --version",
    "uname -a",
    "uptime",
]

if command not in ALLOWED_COMMANDS:
    return {
        "status": "error",
        "error": "Command not whitelisted"
    }
```

---

## 🐛 Troubleshooting

### Daemon Won't Start

**Problem**: `RuntimeError: Failed to clone repository`

**Solution**: Check GitHub credentials
```bash
# Test git access
git clone https://github.com/marc-shade/agentic-cluster-comms.git /tmp/test
# If this fails, check your PAT
```

### No Tasks Appearing

**Problem**: Daemon running but no tasks detected

**Solution**:
1. Check logs: `tail -f ~/agentic-system/logs/github-daemon.log`
2. Verify branch exists: Go to GitHub and check `tasks/scott-remote` branch
3. Ensure daemon is polling: Should see "Checking for new tasks" in logs

### Authentication Errors

**Problem**: `Authentication failed`

**Solution**:
```bash
# Clear stored credentials
rm ~/.git-credentials

# Run daemon again, enter credentials when prompted
# Username: scott-techramp
# Password: <your PAT>
```

### Tasks Not Executing

**Problem**: Tasks detected but not running

**Solution**: Check permissions
```bash
# Ensure scripts are executable
chmod +x ~/agentic-system/cluster-deployment/*.py

# Check Python path
which python3

# Verify psutil is installed
python3 -c "import psutil"
```

---

## 💡 Usage Examples

### Example 1: Receive Health Check

Marc runs:
```bash
python3 submit_cluster_task.py --to scott-remote --type health_check
```

Your daemon automatically:
1. Detects the task
2. Runs health check
3. Posts results with CPU%, memory%, disk%, uptime

### Example 2: Execute Code

Marc runs:
```bash
python3 submit_cluster_task.py \
  --to scott-remote \
  --type code_execution \
  --command "ls -la ~"
```

You get:
- Task detected
- Code executed safely
- Output posted to results

### Example 3: Build Project

Marc runs:
```bash
python3 submit_cluster_task.py \
  --to scott-remote \
  --type build \
  --project my-app
```

Your node can trigger builds (if configured).

---

## 📞 Support

**Issues**:
- Check logs first: `~/agentic-system/logs/github-daemon.log`
- Review GitHub commits: See what tasks were sent
- Contact Marc: Create issue in main repo

**Documentation**:
- Main repo: https://github.com/marc-shade/agentic-system
- GitMQ repo: https://github.com/marc-shade/agentic-cluster-comms
- This guide: `cluster-deployment/SCOTT_NODE_ONBOARDING.md`

---

## ✅ Success Checklist

- [ ] Python 3.8+ installed
- [ ] `psutil` package installed
- [ ] GitHub PAT created with `repo` scope
- [ ] Added as collaborator to `marc-shade/agentic-cluster-comms`
- [ ] GitMQ scripts downloaded
- [ ] Daemon started successfully
- [ ] Heartbeat posted to GitHub
- [ ] Can receive and execute health check task
- [ ] Can post results back to GitHub
- [ ] (Optional) Set up as background service

Once all checked, you're part of the cluster! 🎉

---

## 🚀 What's Next

1. **Test Tasks**: Marc will send test tasks to verify communication
2. **Resource Contribution**: Your node can help with builds, tests, research
3. **Expand Capabilities**: Add specialized task types for your node
4. **Multi-Node Workflows**: Participate in distributed workflows

Welcome aboard! 🤖
