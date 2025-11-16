# Web-Worker Orchestrator Deployment Guide

## Overview

You now have a complete distributed compute backend for your agentic system. This guide walks you through deployment and activation.

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                 YOUR AGENTIC SYSTEM (Complete)                  │
└─────────────────────────────────────────────────────────────────┘

TIER 1: Scheduling & Orchestration
├─ Temporal (scheduled workflows)
├─ AutoKitteh (event-driven automation)
├─ Agent Runtime (persistent task queue)
└─ ✨ Web-Worker Orchestrator (distributed compute) ← NEW

TIER 2: Execution Backends
├─ Local Claude Code CLI (interactive)
├─ Temporal workers (24/7 scheduling)
├─ AutoKitteh workers (event reactions)
└─ ✨ Claude Code Web Workers (5-10 parallel) ← NEW

TIER 3: Knowledge & Memory
├─ Enhanced Memory (semantic storage)
├─ Voice Mode (communication)
└─ Arduino Surface (physical interface)

TIER 4: Results & Persistence
├─ GitHub (PR creation, branch tracking)
├─ S3 (artifact storage)
└─ Enhanced Memory (outcome storage)
```

## Component Checklist

### Core Components ✅
- [x] Task Router (`src/router.ts`) - Intelligent routing decisions
- [x] Web Submitter (`src/submitter.ts`) - Submit to Claude Code web
- [x] Result Collector (`src/collector.ts`) - Gather GitHub results
- [x] Agent Runtime Bridge (`src/agent-runtime-bridge.ts`) - Integration
- [x] Memory Bridge (`src/memory-bridge.ts`) - Store outcomes
- [x] Type Definitions (`src/types.ts`) - TypeScript support
- [x] Main Orchestrator (`src/orchestrator.ts`) - Coordinator

### Configuration ✅
- [x] Routing Rules (`config/routing-rules.json`) - Decision tree
- [x] Worker Templates (`workers/security-audit.prompt`) - Prompts
- [x] Package Config (`package.json`) - Dependencies

### Documentation ✅
- [x] README (`README.md`) - Usage guide
- [x] This Deployment Guide (`DEPLOYMENT.md`)

### Status: 100% Complete
All core infrastructure built and ready for deployment.

## Pre-Deployment Requirements

### 1. Environment Variables

```bash
# Create .env file in orchestrator root
cat > .env <<EOF
CLAUDE_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
WEBHOOK_CALLBACK_URL=http://localhost:9999/webhooks
NODE_ENV=production
EOF
```

### 2. Integration Setup

#### Agent Runtime Integration
You need the Agent Runtime MCP endpoint:
```bash
# This will be provided by your Agent Runtime MCP setup
export AGENT_RUNTIME_URL=http://localhost:4000
```

#### Enhanced Memory Integration
```bash
# Enhanced Memory MCP endpoint
export ENHANCED_MEMORY_URL=http://localhost:4001
```

### 3. GitHub Setup
1. Create GitHub Personal Access Token with:
   - `repo` - Full control of private repositories
   - `workflow` - Update GitHub Action workflows
   - `admin:repo_hook` - Full control of repository hooks

2. Store token in `.env` as `GITHUB_TOKEN`

### 4. Claude API Access
1. Ensure you have access to Claude Code on the web
2. Get API key from Anthropic console
3. Store in `.env` as `CLAUDE_API_KEY`

## Deployment Steps

### Step 1: Build

```bash
cd /Volumes/SSDRAID0/agentic-system/web-worker-orchestrator

# Install dependencies
npm install

# Compile TypeScript
npm run build

# Type check
npm run type-check

# Lint
npm run lint
```

### Step 2: Configure

Edit `config/routing-rules.json` to match your needs:
```json
{
  "workerConfiguration": {
    "maxConcurrentWorkers": 10,
    "creditBudgetPerMonth": 1000
  }
}
```

### Step 3: Test Routing

Before running live, test the routing logic:

```bash
npm run test-routing -- \
  --task-id "test-security-scan" \
  --type "security_scan" \
  --repos 50
```

Expected output:
```
Route: claude_web
Reason: Parallelizable across 50 repos - spawn 5 workers
Worker Count: 5
Estimated Cost: $15
Estimated Duration: 2 hours
```

### Step 4: Deploy

**Option A: Systemd Service (Linux/WSL)**

```bash
sudo tee /etc/systemd/system/web-worker-orchestrator.service <<EOF
[Unit]
Description=Web-Worker Orchestrator
After=network.target

[Service]
Type=simple
User=marc
WorkingDirectory=/Volumes/SSDRAID0/agentic-system/web-worker-orchestrator
EnvironmentFile=/Volumes/SSDRAID0/agentic-system/web-worker-orchestrator/.env
ExecStart=/usr/bin/node /Volumes/SSDRAID0/agentic-system/web-worker-orchestrator/dist/src/orchestrator.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable web-worker-orchestrator
sudo systemctl start web-worker-orchestrator
sudo systemctl status web-worker-orchestrator
```

**Option B: macOS LaunchAgent**

```bash
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.marcshade.web-worker-orchestrator.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.marcshade.web-worker-orchestrator</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/node</string>
    <string>/Volumes/SSDRAID0/agentic-system/web-worker-orchestrator/dist/src/orchestrator.js</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/web-worker-orchestrator.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/web-worker-orchestrator.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAUDE_API_KEY</key>
    <string>sk-...</string>
    <key>GITHUB_TOKEN</key>
    <string>ghp_...</string>
  </dict>
</dict>
</plist>
EOF

# Load
launchctl load ~/Library/LaunchAgents/com.marcshade.web-worker-orchestrator.plist
launchctl list | grep web-worker
```

**Option C: Docker Container**

```bash
cat > Dockerfile <<EOF
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install && npm run build
CMD ["node", "dist/src/orchestrator.js"]
EOF

docker build -t web-worker-orchestrator .
docker run -d \
  -e CLAUDE_API_KEY=$CLAUDE_API_KEY \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -v /Volumes/SSDRAID0/agentic-system/web-worker-orchestrator/logs:/app/logs \
  web-worker-orchestrator
```

### Step 5: Verify Deployment

```bash
# Check service status
npm run status

# Tail logs
npm run logs

# Test a task submission
voice: "Security audit all repos"
# Should appear in logs as routed to web workers
```

## Integration with Agent Runtime

To make tasks automatically routable:

```typescript
// In your Agent Runtime task creation
const task = {
  id: "audit-all-repos",
  type: "security_scan",
  description: "Audit all 50 client repositories",
  repos: getAllRepos(), // 50 repos
  metadata: {
    web_eligible: true, // Signal for orchestrator
  },
};

await agentRuntime.createTask(task);

// Orchestrator will:
// 1. Detect the task is pending
// 2. Route to: claude_web
// 3. Spawn 5 workers
// 4. Collect results
// 5. Mark task complete
```

## Monitoring & Maintenance

### Daily Checks

```bash
# Check status
npm run status

# Monitor active sessions
npm run sessions

# View results
npm run results
```

### Weekly Maintenance

```bash
# Review cost
npm run cost-analysis

# Check memory system
npm run memory-status

# Review routing statistics
npm run routing-stats
```

### Monthly Review

```bash
# Generate cost report
npm run monthly-report

# Review worker performance
npm run worker-metrics

# Plan next month's budget
npm run cost-forecast
```

## Cost Tracking

The orchestrator tracks all spending:

```
Budget: $1000/month
Status: $450 spent (45%)
Active workers: 3
Estimated monthly spend: $600

Top expenses:
- Security scanning: $150
- Code migrations: $120
- ML training: $80
- Other: $100
```

To set alerts:

```json
{
  "costAlerts": {
    "warningThreshold": 800,
    "criticalThreshold": 950,
    "notificationChannels": ["email", "slack", "voice"]
  }
}
```

## Troubleshooting

### Orchestrator won't start

```bash
# Check logs
npm run logs

# Verify environment variables
echo $CLAUDE_API_KEY
echo $GITHUB_TOKEN

# Test API connectivity
curl https://api.github.com -H "Authorization: Bearer $GITHUB_TOKEN"
```

### Tasks not routing to web workers

```bash
# Test routing logic
npm run test-routing -- --task-id your-task-id

# Check Agent Runtime is accessible
npm run status
```

### Claude Code web submissions failing

```bash
# Check API key is valid
npm run test-claude-api

# Verify GitHub token permissions
npm run test-github-api

# Check web session status
npm run session -- --session-id abc123
```

## Next Steps

1. **Deploy orchestrator** (this guide)
2. **Submit first test task** to Agent Runtime
3. **Monitor execution** in logs
4. **Verify results** in GitHub
5. **Review cost** and performance
6. **Scale up** to production workloads

## Success Criteria

✅ Orchestrator running 24/7
✅ Tasks automatically routing to web workers
✅ 5-10 parallel workers executing
✅ Results aggregated in enhanced-memory
✅ PRs created automatically
✅ Cost tracking functioning
✅ Zero local machine impact

## Support

For issues, check:
1. Logs: `npm run logs`
2. Status: `npm run status`
3. Routing: `npm run test-routing`
4. API connectivity: `npm run test-claude-api` and `npm run test-github-api`

---

**Your distributed compute layer is now ready for deployment.**

With the web-worker orchestrator deployed, your agentic system is complete:
- Temporal + AutoKitteh (scheduling/events)
- ✨ Web-Worker Orchestrator (distributed compute)
- Agent Runtime (task persistence)
- Enhanced Memory (knowledge storage)
- Voice Mode (communication)

You have $1000 in credits for 500+ hours of parallel, autonomous code execution.
