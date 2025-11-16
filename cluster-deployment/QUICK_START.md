# Quick Start - Join the Agentic Cluster

**One command to join the cluster from any machine!**

---

## 🚀 For Scott (or any new node)

### Option 1: One-Line Bootstrap (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- scott-remote
```

Replace `scott-remote` with your desired node ID.

**That's it!** The script will:
- ✅ Install dependencies (psutil)
- ✅ Create directory structure
- ✅ Download GitMQ scripts
- ✅ Configure the node
- ✅ Set up background service
- ✅ Provide next steps

---

### Option 2: Manual Download and Run

```bash
# Download bootstrap script
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh -o bootstrap-node.sh

# Make executable
chmod +x bootstrap-node.sh

# Run with your node ID
./bootstrap-node.sh scott-remote
```

---

## 📋 Prerequisites

Before running the bootstrap script, ensure you have:

1. **Git** installed
2. **Python 3.8+** installed
3. **pip3** installed
4. **GitHub Personal Access Token** with `repo` scope
   - Create at: https://github.com/settings/tokens
   - Save it somewhere safe!

---

## ⚡ After Bootstrap

The script will give you instructions, but here's the quick version:

### Start the Daemon (Foreground - for testing)

```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

You'll see:
- Initial clone of communication repository
- GitHub credentials prompt (use your PAT)
- Heartbeat posted
- Daemon polling for tasks

### Send a Test Task

In another terminal:

```bash
cd ~/agentic-system/cluster-deployment

# Health check to macpro51
./send-task.sh macpro51 health_check

# Check results
./send-task.sh macpro51 --check-results

# Check your own heartbeat
./send-task.sh scott-remote --check-heartbeat
```

### Run as Background Service

**Linux (systemd)**:
```bash
systemctl --user enable github-node-daemon.service
systemctl --user start github-node-daemon.service
systemctl --user status github-node-daemon.service
```

**macOS (LaunchAgent)**:
```bash
launchctl load ~/Library/LaunchAgents/com.agentic.github-daemon.plist
launchctl list | grep github-daemon
```

---

## 🔍 Verify It's Working

### Check Heartbeat on GitHub

1. Go to: https://github.com/marc-shade/agentic-cluster-comms
2. Click on "branches"
3. Look for `heartbeat` branch
4. Check for your node's heartbeat file

### Check Daemon Logs

```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

You should see:
```
[timestamp] INFO - GitMQ daemon initialized for node: scott-remote
[timestamp] INFO - Posted heartbeat
[timestamp] INFO - Checking for new tasks...
```

### Send Test Task from Marc

Marc will send you a health check:
```bash
# Marc runs this
./send-task.sh scott-remote health_check
```

Your daemon will:
1. Detect the task
2. Execute health check
3. Post results to GitHub

---

## 📁 What Gets Installed

```
~/agentic-system/
├── cluster-deployment/
│   ├── github_node_daemon.py      # Task polling daemon
│   ├── submit_cluster_task.py     # Task submission tool
│   ├── cluster_memory.py          # Cluster memory manager
│   ├── start-daemon.sh            # Start script
│   └── send-task.sh               # Helper for sending tasks
├── agentic-cluster-comms/         # Cloned on first daemon run
│   ├── tasks/
│   ├── results/
│   └── heartbeat/
├── logs/
│   ├── github-daemon.log          # Daemon logs
│   └── github-daemon-error.log    # Error logs
└── databases/
    └── cluster/
        ├── nodes/scott-remote/    # Your personal memories
        └── shared_memories.db     # Cluster-wide memories

~/.claude/
└── node-config.json               # Node configuration
```

---

## 🆘 Troubleshooting

### "Authentication failed"

**Problem**: Git credentials not accepted

**Solution**:
```bash
# Clear credentials and try again
rm ~/.git-credentials
./start-daemon.sh

# When prompted:
# Username: your-github-username
# Password: your-personal-access-token (not your GitHub password!)
```

### "Repository not found"

**Problem**: Not added as collaborator

**Solution**: Ask Marc to invite you to `marc-shade/agentic-cluster-comms`

### "Command not found: python3"

**Problem**: Python not installed or not in PATH

**Solution**:
```bash
# Linux
sudo apt-get install python3 python3-pip  # Debian/Ubuntu
sudo dnf install python3 python3-pip      # Fedora/RHEL

# macOS
brew install python3
```

### Daemon not receiving tasks

**Problem**: Polling but no tasks detected

**Solution**:
1. Check daemon logs: `tail -f ~/agentic-system/logs/github-daemon.log`
2. Verify GitHub access: `cd ~/agentic-system/agentic-cluster-comms && git fetch --all`
3. Check branch exists: Look for `tasks/scott-remote` on GitHub
4. Increase poll interval verbosity in logs

---

## 🎓 For Claude Code Users

If you're using Claude Code, just paste this into your chat:

```
Please bootstrap this node into the agentic cluster with node ID "scott-remote":

curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- scott-remote

Then start the daemon in the background and verify it's working.
```

Claude Code will:
1. Run the bootstrap script
2. Handle the setup
3. Start the daemon
4. Verify connectivity
5. Post initial heartbeat

---

## 📞 Need Help?

- **Check logs**: `~/agentic-system/logs/github-daemon.log`
- **View configuration**: `cat ~/.claude/node-config.json`
- **Test GitHub access**: `git ls-remote https://github.com/marc-shade/agentic-cluster-comms.git`
- **Contact Marc**: Create issue in main repo

---

## ✅ Success Checklist

- [ ] Bootstrap script completed without errors
- [ ] Node configuration created (`~/.claude/node-config.json`)
- [ ] GitMQ scripts downloaded
- [ ] Daemon started successfully
- [ ] Heartbeat posted to GitHub
- [ ] Can receive health check task from Marc
- [ ] Can send task to other nodes
- [ ] Background service configured (optional)

**Welcome to the cluster! 🎉**
