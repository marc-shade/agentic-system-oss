# Cross-Network Agent Cluster Deployment Guide

## 🎯 Overview

This guide shows how to connect Claude Code instances across different networks using GitHub as a secure message broker. No VPN, firewall configuration, or static IPs required.

**Participants**:
- **Marc** (`marc-shade`) - Orchestrator running on local network
- **Scott** (`scott-techramp`) - Remote node on different network

**Technology Stack**:
- GitHub private repository (message broker)
- GitHub MCP Server (official, April 2025)
- GitMQ pattern (git commits as messages)
- Python daemons for task execution

---

## 🏗️ Architecture

```
Marc's Network (192.168.1.x)                    Scott's Network (different)
┌──────────────────────────────┐              ┌─────────────────────────┐
│  mac-studio (orchestrator)   │              │  scott-remote           │
│  ┌────────────────────────┐  │              │  ┌───────────────────┐  │
│  │ github_node_daemon.py  │  │              │  │github_node_daemon │  │
│  │ - Polls: tasks/        │  │              │  │- Polls: tasks/    │  │
│  │   mac-studio           │  │              │  │  scott-remote     │  │
│  │ - Pushes: results/     │  │              │  │- Pushes: results/ │  │
│  │   mac-studio           │  │              │  │  scott-remote     │  │
│  └────────────────────────┘  │              │  └───────────────────┘  │
└──────────────┬───────────────┘              └───────────┬─────────────┘
               │                                          │
               │  HTTPS (OAuth/PAT)                       │  HTTPS (OAuth/PAT)
               │  git pull/push                           │  git pull/push
               └──────────┬───────────────────────────────┘
                          │
                   ┌──────▼──────┐
                   │   GitHub    │
                   │  (Secure    │
                   │   Message   │
                   │   Broker)   │
                   │             │
                   │ Private Repo│
                   │ marc-shade/ │
                   │ agentic-    │
                   │ cluster-    │
                   │ comms       │
                   └─────────────┘
```

---

## 📦 Phase 1: Create GitHub Infrastructure

### Step 1.1: Create Private Repository (Marc)

```bash
# Create via GitHub CLI
gh repo create marc-shade/agentic-cluster-comms \
  --private \
  --description "Cross-network agent cluster communication via GitMQ pattern" \
  --clone

cd agentic-cluster-comms

# Create directory structure
mkdir -p tasks results heartbeat configs/node-templates

# Create README
cat > README.md << 'EOF'
# Agentic Cluster Communications

Private repository for cross-network agent cluster communication.

## Structure

- `tasks/{node-id}/` - Incoming tasks for each node
- `results/{node-id}/` - Task execution results
- `heartbeat/` - Node health status files
- `configs/` - Node configuration templates

## Usage

See CROSS_NETWORK_DEPLOYMENT_GUIDE.md in the main agentic-system repo.
EOF

git add .
git commit -m "Initial repository setup"
git push origin main
```

### Step 1.2: Add Scott as Collaborator (Marc)

```bash
# Via GitHub CLI
gh api repos/marc-shade/agentic-cluster-comms/collaborators/scott-techramp \
  -X PUT \
  -f permission=push

# Or via web: https://github.com/marc-shade/agentic-cluster-comms/settings/access
# Click "Add people" → Enter "scott-techramp" → Select "Write" access
```

### Step 1.3: Create GitHub Personal Access Token (Both)

**Marc and Scott both need to do this:**

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: `agentic-cluster-comms`
4. Expiration: 90 days (or No expiration for convenience)
5. Scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `read:org` (Read org and team membership)
   - ✅ `workflow` (Update GitHub Action workflows)
6. Click "Generate token"
7. **SAVE THE TOKEN** - you won't see it again

```bash
# Save token to environment
echo 'export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_YOUR_TOKEN_HERE"' >> ~/.bashrc
source ~/.bashrc
```

---

## 📦 Phase 2: Install GitHub MCP Server (Both)

### Option A: Remote Server (Recommended)

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_YOUR_TOKEN"
      },
      "disabled": false
    }
  }
}
```

### Option B: Docker (If npx not available)

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_YOUR_TOKEN"
      },
      "disabled": false
    }
  }
}
```

### Verify Installation

```bash
# Restart Claude Code to load new MCP server
claude-code

# Test (in Claude Code session):
# "Use the GitHub MCP server to check the status of marc-shade/agentic-cluster-comms"
```

---

## 📦 Phase 3: Deploy Node Daemon (Both)

### Step 3.1: Copy Daemon Scripts

**Marc**:
```bash
# Scripts already in /Volumes/SSDRAID0/agentic-system/cluster-deployment/
chmod +x github_node_daemon.py submit_cluster_task.py
```

**Scott**:
```bash
# Clone the main repo (or just copy the files)
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system/cluster-deployment

# Or download directly
curl -O https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/github_node_daemon.py
curl -O https://raw.githubusercontent.com/marc-shade/agentic-system/main/cluster-deployment/submit_cluster_task.py
chmod +x github_node_daemon.py submit_cluster_task.py
```

### Step 3.2: Install Dependencies

```bash
# Both Marc and Scott
pip3 install psutil
```

### Step 3.3: Run Daemon

**Marc's mac-studio**:
```bash
python3 github_node_daemon.py \
  --node-id mac-studio \
  --repo marc-shade/agentic-cluster-comms \
  --poll-interval 30
```

**Scott's machine**:
```bash
python3 github_node_daemon.py \
  --node-id scott-remote \
  --repo marc-shade/agentic-cluster-comms \
  --poll-interval 30
```

### Step 3.4: Run as Background Service (Optional)

**Using nohup**:
```bash
nohup python3 github_node_daemon.py \
  --node-id mac-studio \
  --repo marc-shade/agentic-cluster-comms \
  > /tmp/github-daemon.log 2>&1 &

echo $! > /tmp/github-daemon.pid
```

**Using systemd (Linux)**:
```bash
sudo tee /etc/systemd/system/github-node-daemon.service << EOF
[Unit]
Description=GitHub Node Daemon for Agentic Cluster
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment="GITHUB_PERSONAL_ACCESS_TOKEN=ghp_YOUR_TOKEN"
ExecStart=/usr/bin/python3 $HOME/agentic-system/cluster-deployment/github_node_daemon.py \
  --node-id scott-remote \
  --repo marc-shade/agentic-cluster-comms \
  --poll-interval 30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable github-node-daemon
sudo systemctl start github-node-daemon
sudo systemctl status github-node-daemon
```

---

## 📦 Phase 4: Test Communication

### Test 1: Health Check (Marc → Scott)

```bash
# Marc submits health check to Scott
python3 submit_cluster_task.py \
  --to scott-remote \
  --type health_check

# Wait ~60 seconds (2 poll cycles)

# Check results
python3 submit_cluster_task.py \
  --to scott-remote \
  --check-results
```

**Expected Output**:
```json
{
  "task_id": "task_20251114_001",
  "status": "success",
  "output": {
    "node_id": "scott-remote",
    "cpu_percent": 15.2,
    "memory_percent": 45.8,
    "disk_percent": 62.1,
    "timestamp": "2025-11-14T16:30:00Z"
  }
}
```

### Test 2: Code Execution (Marc → Scott)

```bash
# Marc asks Scott to execute Python code
python3 submit_cluster_task.py \
  --to scott-remote \
  --type code_execution \
  --command "python3 -c 'print(\"Hello from Scott!\")'"

# Wait and check results
python3 submit_cluster_task.py \
  --to scott-remote \
  --check-results
```

### Test 3: Bidirectional (Scott → Marc)

**Scott**:
```bash
python3 submit_cluster_task.py \
  --to mac-studio \
  --from-node scott-remote \
  --type health_check

python3 submit_cluster_task.py \
  --to mac-studio \
  --check-results
```

---

## 📦 Phase 5: Node Cloning (Deploy Full Stack to Scott)

### Step 5.1: Create Configuration Template (Marc)

```bash
cd agentic-cluster-comms

# Create node template
mkdir -p configs/node-templates/standard

# Export MCP server configs (safe subset)
cat > configs/node-templates/standard/mcp-servers.json << 'EOF'
{
  "enhanced-memory-mcp": {
    "command": "python3",
    "args": ["{INSTALL_PATH}/mcp-servers/enhanced-memory-mcp/server.py"],
    "env": {}
  },
  "agent-runtime-mcp": {
    "command": "python3",
    "args": ["{INSTALL_PATH}/mcp-servers/agent-runtime-mcp/server.py"],
    "env": {}
  },
  "github-mcp": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "{GITHUB_TOKEN}"
    }
  }
}
EOF

# Export database schemas
cp /Volumes/SSDRAID0/agentic-system/databases/cluster/schemas/*.sql \
   configs/node-templates/standard/

# Commit and push
git add configs/
git commit -m "Add standard node template"
git push
```

### Step 5.2: Send Clone Task (Marc)

```bash
python3 submit_cluster_task.py \
  --to scott-remote \
  --type clone_node \
  --config-template standard
```

### Step 5.3: Enhanced Daemon with Clone Support

The daemon already supports `clone_node` task type. For production use, you'd expand the `_clone_node_config()` method to:

1. Download MCP server code from configs/
2. Install Python dependencies
3. Create database directories
4. Initialize schemas
5. Configure Claude Code
6. Register in cluster

---

## 🔒 Security Considerations

### What's Secure

✅ **Transport**: HTTPS (GitHub infrastructure)
✅ **Authentication**: GitHub OAuth/PAT
✅ **Authorization**: Repository collaborator access
✅ **Audit Trail**: Complete git history
✅ **Rate Limiting**: GitHub API limits (5000 req/hour)
✅ **Private**: Repository is private

### What to Monitor

⚠️ **Token Rotation**: Rotate PATs every 90 days
⚠️ **Access Review**: Review collaborators monthly
⚠️ **Command Validation**: Sanitize commands before execution
⚠️ **Resource Limits**: Set timeout and memory limits
⚠️ **Secrets**: Never commit credentials to tasks

### Production Hardening

For production use, enhance the daemon with:

1. **Command Whitelist**: Only allow specific commands
2. **Signature Verification**: Sign tasks with GPG
3. **Rate Limiting**: Limit task execution rate
4. **Resource Isolation**: Use Docker containers
5. **Monitoring**: Export metrics to Prometheus

---

## 📊 Monitoring & Troubleshooting

### Check Daemon Status

```bash
# Check if daemon is running
ps aux | grep github_node_daemon

# View logs (if using nohup)
tail -f /tmp/github-daemon.log

# View logs (if using systemd)
sudo journalctl -u github-node-daemon -f
```

### Check GitHub Activity

```bash
# View recent commits on task branches
cd /tmp/agentic-cluster-comms/repo
git log --all --graph --oneline --branches='tasks/*'

# View results
git log --all --graph --oneline --branches='results/*'
```

### Common Issues

**Issue**: Daemon not polling
- **Fix**: Check `GITHUB_PERSONAL_ACCESS_TOKEN` environment variable
- **Fix**: Verify network connectivity to GitHub
- **Fix**: Check git clone succeeded

**Issue**: Tasks not executing
- **Fix**: Check task branch exists: `git branch -a | grep tasks`
- **Fix**: Verify JSON format in commit messages
- **Fix**: Check daemon logs for errors

**Issue**: Results not appearing
- **Fix**: Wait 2-3 poll cycles (60-90 seconds)
- **Fix**: Check result branch: `git checkout results/{node-id} && git log`
- **Fix**: Verify daemon has push permissions

---

## 🚀 Integration with Existing Infrastructure

### With Web-Worker Orchestrator

The web-worker-orchestrator can route tasks to GitHub-based nodes:

```python
# In router.ts, add new route
{
  "condition": "isRemoteNode",
  "action": "submitToGitHub",
  "params": {
    "node_id": "scott-remote",
    "repo": "marc-shade/agentic-cluster-comms"
  }
}
```

### With Agent Runtime MCP

Bridge Agent Runtime tasks to GitHub queue:

```python
# Monitor agent-runtime-mcp for new tasks
task = agent_runtime.get_next_task()

# Submit to remote node via GitHub
submit_cluster_task(
    to_node="scott-remote",
    task_type="code_execution",
    payload={"command": task.command}
)
```

### With Enhanced Memory MCP

Share cluster state via enhanced-memory:

```python
# Store task outcome in memory
mcp__enhanced_memory_mcp__create_entities([{
    "name": f"cluster-task-{task_id}",
    "entityType": "cluster_operation",
    "observations": [
        f"executed_on: {node_id}",
        f"status: {result['status']}",
        f"duration: {duration}s"
    ]
}])
```

---

## 📈 Performance & Scalability

### Latency Expectations

- **Task submission**: < 1 second (git push)
- **Task pickup**: 30-60 seconds (poll interval)
- **Result retrieval**: 30-60 seconds (poll interval)
- **Total round-trip**: ~60-120 seconds

This is acceptable for cross-network asynchronous operations.

### Scaling to Multiple Nodes

The architecture supports N nodes:

```
marc-shade/agentic-cluster-comms
├── tasks/
│   ├── mac-studio/
│   ├── scott-remote/
│   ├── alice-laptop/
│   ├── bob-workstation/
│   └── charlie-server/
└── results/
    ├── mac-studio/
    ├── scott-remote/
    ├── alice-laptop/
    ├── bob-workstation/
    └── charlie-server/
```

Each node runs its own daemon polling its branch.

### Cost Analysis

**GitHub Free Tier**:
- Unlimited private repos
- Unlimited collaborators
- 500 MB storage
- 1 GB transfer

**Estimated Usage**:
- 1000 tasks/day × 1 KB = 1 MB
- 1000 results/day × 10 KB = 10 MB
- **Total**: ~11 MB/day = 330 MB/month

**Well within free tier limits**.

---

## 🎓 Advanced Use Cases

### CrewAI Integration (Scott's Use Case)

Scott can bridge his CrewAI agents with the cluster:

```python
# In Scott's crew-agent-backend
from crewai import Agent, Task, Crew

# Create agent that executes via cluster
class ClusterExecutorAgent(Agent):
    def execute_task(self, task):
        # Submit to Marc's cluster
        result = submit_cluster_task(
            to_node="mac-studio",
            task_type="code_execution",
            payload={"command": task.command}
        )
        return result

# Use in CrewAI workflow
crew = Crew(
    agents=[ClusterExecutorAgent(), ...],
    tasks=[...],
    process="sequential"
)

crew.kickoff()
```

### Distributed Model Inference

Split LLM inference across nodes:

```python
# Marc's node: Claude Sonnet
# Scott's node: Llama via Ollama

# Route based on model type
if model == "claude":
    submit_to_node("mac-studio")
elif model == "llama":
    submit_to_node("scott-remote")
```

### Federated Learning

Nodes train models on local data, share updates:

```python
# Each node trains on local data
local_weights = train_local_model()

# Share gradients via GitHub
submit_cluster_task(
    to_node="mac-studio",
    task_type="aggregate_weights",
    payload={"weights": local_weights}
)
```

---

## 📚 Next Steps

1. ✅ **Complete Setup**: Follow Phases 1-4
2. ✅ **Test Communication**: Run health checks
3. ✅ **Deploy Node Cloning**: Use Phase 5
4. ⏭️ **Integrate with Existing Systems**: Web-worker, agent-runtime
5. ⏭️ **Add Monitoring**: Prometheus metrics, Grafana dashboards
6. ⏭️ **Production Hardening**: Security enhancements
7. ⏭️ **Scale to More Nodes**: Add team members

---

## 🤝 Support & Contribution

- **Issues**: https://github.com/marc-shade/agentic-system/issues
- **Discussions**: https://github.com/marc-shade/agentic-system/discussions
- **Main Repo**: https://github.com/marc-shade/agentic-system

---

## 📄 License

Same as parent agentic-system repository.
