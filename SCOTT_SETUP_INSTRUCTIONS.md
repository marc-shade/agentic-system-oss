# Scott's Cluster Setup Instructions

**Welcome! Here's everything you need to join the agentic cluster. It's literally one command.**

---

## 🚀 The One Command You Need

Open your terminal and run:

```bash
curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- scott-remote
```

**That's it!** This will set up everything automatically.

---

## 📋 What You'll Need First

Before running the command above, make sure you have:

1. **Git installed** - Check with: `git --version`
2. **Python 3.8+** - Check with: `python3 --version`
3. **pip3** - Check with: `pip3 --version`
4. **GitHub Personal Access Token (PAT)**:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scope: `repo` (all sub-scopes)
   - Generate and **save the token somewhere safe!**

---

## 🎬 What Happens During Bootstrap

The script will:

1. ✅ Check that git, python3, and pip3 are installed
2. ✅ Install `psutil` Python package
3. ✅ Create directory structure at `~/agentic-system/`
4. ✅ Download GitMQ daemon and task scripts
5. ✅ Configure your node with ID `scott-remote`
6. ✅ Set up background service (systemd or LaunchAgent)
7. ✅ Show you next steps

**Estimated time**: 1-2 minutes

---

## ▶️ After Bootstrap Completes

The script will tell you to do these steps:

### Step 1: Start the Daemon (Test Mode)

```bash
cd ~/agentic-system/cluster-deployment
./start-daemon.sh
```

**First run**: You'll be prompted for GitHub credentials:
- Username: `scott-techramp` (your GitHub username)
- Password: **Your PAT token** (NOT your GitHub password!)

You should see:
```
[timestamp] INFO - GitMQ daemon initialized for node: scott-remote
[timestamp] INFO - Starting GitMQ daemon for scott-remote
[timestamp] INFO - Repository cloned successfully
[timestamp] INFO - Posted heartbeat
[timestamp] INFO - Polling every 30 seconds
```

**Leave this running!** Open a new terminal for the next steps.

### Step 2: Verify Your Heartbeat (New Terminal)

```bash
cd ~/agentic-system/cluster-deployment
./send-task.sh scott-remote --check-heartbeat
```

You should see your system stats (CPU, memory, disk, uptime).

### Step 3: Send Test Task to Marc

```bash
./send-task.sh macpro51 health_check
```

Wait 30-60 seconds, then check results:

```bash
./send-task.sh macpro51 --check-results
```

If you see results, **you're connected!** 🎉

---

## 🔄 Run as Background Service (Optional but Recommended)

Once you've verified it works, set it up to run automatically:

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

## 📊 Monitor the Daemon

### View Logs
```bash
tail -f ~/agentic-system/logs/github-daemon.log
```

### Stop the Daemon
If running in foreground, press `Ctrl+C`

If running as service:
```bash
# Linux
systemctl --user stop github-node-daemon.service

# macOS
launchctl unload ~/Library/LaunchAgents/com.agentic.github-daemon.plist
```

---

## 🧪 Testing Communication with Marc

### Marc will send you tasks like:

**Health Check**:
```bash
# Marc runs this:
./send-task.sh scott-remote health_check
```

Your daemon will automatically:
1. Detect the task (within 30 seconds)
2. Execute health check
3. Post results to GitHub

You'll see in your logs:
```
[timestamp] INFO - Found new task: abc123 - health_check task
[timestamp] INFO - Executing task: <uuid> (type: health_check)
[timestamp] INFO - Posted result for task abc123
```

**Code Execution**:
```bash
# Marc asks you to run a command:
./send-task.sh scott-remote code_execution --command "uname -a"
```

Your node will execute it and return the output!

---

## 🆘 Troubleshooting

### "Authentication failed"
**Problem**: GitHub credentials rejected

**Solution**:
```bash
# Delete stored credentials
rm ~/.git-credentials

# Run daemon again, it will prompt for credentials
./start-daemon.sh

# When prompted:
# Username: scott-techramp
# Password: <your-PAT-token>
```

### "Repository not found"
**Problem**: Not added as collaborator to `marc-shade/agentic-cluster-comms`

**Solution**: Ask Marc to invite you to the repository

### "Command not found: python3"
**Solution**: Install Python 3:
```bash
# Linux (Debian/Ubuntu)
sudo apt-get install python3 python3-pip

# Linux (Fedora/RHEL)
sudo dnf install python3 python3-pip

# macOS
brew install python3
```

### Daemon not receiving tasks
**Check**:
1. Daemon is running: `ps aux | grep github_node_daemon`
2. Logs show polling: `tail -f ~/agentic-system/logs/github-daemon.log`
3. Branch exists on GitHub: Go to repo and check `tasks/scott-remote/`

---

## 📁 What Gets Installed

```
~/agentic-system/
├── cluster-deployment/
│   ├── github_node_daemon.py       # Main daemon (polls for tasks)
│   ├── submit_cluster_task.py      # Send tasks to other nodes
│   ├── start-daemon.sh             # Start script
│   └── send-task.sh                # Helper for sending tasks
├── agentic-cluster-comms/          # Cloned on first run
│   ├── tasks/scott-remote/         # Your incoming tasks
│   ├── results/scott-remote/       # Your task results
│   └── heartbeat/                  # Health status
├── logs/
│   ├── github-daemon.log           # Daemon activity logs
│   └── github-daemon-error.log     # Error logs
└── databases/
    └── cluster/
        ├── nodes/scott-remote/     # Your personal memories
        └── shared_memories.db      # Cluster-wide memories

~/.claude/
└── node-config.json                # Node configuration

~/.config/systemd/user/             # Linux only
└── github-node-daemon.service      # Background service

~/Library/LaunchAgents/             # macOS only
└── com.agentic.github-daemon.plist # Background service
```

---

## 🔗 Important Links

- **Repository**: https://github.com/marc-shade/agentic-cluster-comms
- **Quick Start Guide**: https://github.com/marc-shade/agentic-cluster-comms/blob/main/docs/QUICK_START.md
- **Detailed Onboarding**: https://github.com/marc-shade/agentic-cluster-comms/blob/main/docs/SCOTT_NODE_ONBOARDING.md
- **Main Agentic System**: https://github.com/marc-shade/agentic-system

---

## 📞 Need Help?

- **Check logs**: `~/agentic-system/logs/github-daemon.log`
- **View configuration**: `cat ~/.claude/node-config.json`
- **Test GitHub access**: `git ls-remote https://github.com/marc-shade/agentic-cluster-comms.git`
- **Contact Marc**: Create issue or reach out directly

---

## ✅ Success Checklist

- [ ] Prerequisites installed (git, python3, pip3, PAT created)
- [ ] Bootstrap script completed without errors
- [ ] Daemon started and heartbeat posted
- [ ] Can see your heartbeat with `--check-heartbeat`
- [ ] Sent test task to macpro51
- [ ] Received results from macpro51
- [ ] (Optional) Background service configured

---

## 🎓 For Claude Code

If you're using Claude Code on your machine, just paste this:

```
Please bootstrap this node into the agentic cluster with node ID "scott-remote":

curl -fsSL https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/bootstrap-node.sh | bash -s -- scott-remote

Then start the daemon and verify connectivity.
```

Claude Code will handle everything automatically!

---

## 🎉 Welcome to the Cluster!

Once you're connected, you'll be able to:
- **Receive tasks** from Marc's nodes (mac-studio, macbook-air, macpro51)
- **Send tasks** to any cluster node
- **Contribute resources** to distributed builds and tests
- **Participate** in multi-node workflows

**All without VPN, firewall config, or static IPs - just git commits as messages!**

Looking forward to having you in the cluster! 🚀
