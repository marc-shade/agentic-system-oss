# Web-Worker Orchestrator

Transform your local agentic system into a distributed compute backend using Claude Code on the web.

## Overview

The Web-Worker Orchestrator enables you to:
- **Parallelize** code tasks across 5-10 workers simultaneously
- **Offload** long-running tasks to cloud (zero local machine impact)
- **Automate** security scanning, migrations, testing at scale
- **Track** results and cost in enhanced-memory
- **Route** tasks intelligently based on characteristics

**Key Benefit**: $1000 in credits = 500+ hours of parallel, autonomous code execution

## Architecture

```
Agent Runtime (Task Queue)
        ↓
   Web-Worker Orchestrator
        ↓
    ┌───┴───────────────────┐
    ↓         ↓         ↓    ↓
  Temporal AutoKitteh Local Claude Code Web
                      Workers (5-10 parallel)
    ↓
  Results Aggregation (GitHub PRs + Enhanced Memory)
```

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/web-worker-orchestrator

# Install dependencies
npm install

# Set environment variables
export CLAUDE_API_KEY="sk-..."
export GITHUB_TOKEN="ghp_..."
export WEBHOOK_CALLBACK_URL="http://localhost:9999/webhooks"
```

## Usage

### 1. Task Submission

Submit tasks to Agent Runtime with web metadata:

```typescript
const task = {
  id: "audit-50-repos",
  type: "security_scan",
  description: "Audit all 50 client repos for vulnerabilities",
  repos: ["client-1", "client-2", /* ... 48 more */],
  estimatedDurationHours: 2,
  requiresLocalFiles: false,
  metadata: {
    web_eligible: true,
  },
};

await agentRuntime.createTask(task);
```

### 2. Automatic Routing

The orchestrator detects eligible tasks and routes them:

```bash
# Start the orchestrator
npm run start

# It will:
# 1. Poll Agent Runtime for pending tasks
# 2. Analyze task characteristics
# 3. Route to optimal backend (Temporal/AutoKitteh/Web/Local)
# 4. Submit to Claude Code web if routed there
# 5. Collect results when complete
# 6. Store in enhanced-memory
# 7. Mark task complete in Agent Runtime
```

### 3. Monitor Progress

```bash
# Check orchestrator status
npm run status

# View active web sessions
npm run sessions

# Check enhanced-memory for results
npm run results
```

## Routing Rules

The router automatically decides where to execute each task:

| Condition | Route | Parallelization |
|-----------|-------|-----------------|
| Deterministic schedule | Temporal | 1 worker |
| Event-driven trigger | AutoKitteh | Event-based |
| 5+ repos, parallelizable | Claude Web | 5+ workers |
| 2+ hours duration | Claude Web | 1 worker |
| No local files needed | Claude Web | 1+ workers |
| Needs immediate feedback | Local CLI | Interactive |

See `config/routing-rules.json` for complete rules.

## Common Offloading Scenarios

### Security Scanning (5-10 workers)

```typescript
const task = {
  type: "security_scan",
  repos: allClientRepos, // 50 repos
  description: "Nightly security audit with Checkov + trivy + semgrep",
  schedule: "0 2 * * *", // 2 AM daily
  metadata: { web_eligible: true },
};

// Router spawns 5 workers, each scans 10 repos
// Total time: 2 hours (vs 10 hours serial)
// Cost: ~$15-20
```

### Multi-Repo Code Migration (3 workers)

```typescript
const task = {
  type: "code_migration",
  repos: ["repo-1", ..., "repo-30"],
  description: "Add TypeScript to 30 JavaScript repos",
  estimatedDurationHours: 3,
  metadata: { web_eligible: true },
};

// Router spawns 3 workers
// Each handles 10 repos
// Total time: 1.5 hours (vs 30 hours serial)
// Cost: ~$15-20
```

### ML Model Training (1 worker, long-running)

```typescript
const task = {
  type: "ml_training",
  repos: ["ml-pipeline"],
  description: "Train Q4 forecasting model",
  estimatedDurationHours: 4,
  requiresLocalFiles: false,
  metadata: { web_eligible: true },
};

// Router sends to single web worker
// Runs unattended in cloud VM
// Zero local machine impact
// Cost: ~$5-10
```

## Worker Prompt Templates

Located in `workers/`:
- `security-audit.prompt` - Security scanning across repos
- `code-migration.prompt` - Framework/language migration
- `test-generation.prompt` - Add tests to repos (coming soon)
- `ml-training.prompt` - Model training pipeline (coming soon)
- `documentation.prompt` - Auto-generate API docs (coming soon)

Each prompt includes:
- Setup instructions
- Execution phases
- Quality assurance checks
- Error handling
- Output expectations

## Cost Optimization

The orchestrator tracks costs and helps optimize:

```json
{
  "estimatedCostWeb": 50,
  "estimatedCostLocal": 200,
  "parallelizationFactor": 5,
  "timeSavingsHours": 18,
  "recommendation": "Use web workers - 75% cheaper"
}
```

### Budget Management

```typescript
// Monthly budget: $1000
// Configuration limits:
// - Max workers: 10
// - Warn at: $800 spent
// - Stop at: $950 spent
```

## Integration with Enhanced Memory

All results stored for analysis:

```typescript
// Stored entities:
{
  name: "web-session-${sessionId}",
  entityType: "web_worker_session",
  observations: {
    taskId, sessionId, repo, branch,
    status, cost, createdAt, completedAt
  }
}

{
  name: "task-result-${taskId}",
  entityType: "task_result",
  observations: {
    status, outcome, costActual, durationActual
  }
}

{
  name: "routing-stats-${timestamp}",
  entityType: "routing_statistics",
  observations: {
    totalTasks, routedToWeb, totalSavingsHours
  }
}
```

## Monitoring & Alerting

### Key Metrics

```bash
npm run metrics

# Output:
# Web Workers Active: 3
# Total Tasks Completed: 127
# Average Cost per Task: $8.50
# Average Time per Task: 1.2 hours
# Total Hours Saved: 380 hours
# Total Cost: $876.50 / $1000
```

### Alerts

- Task failure detected
- Cost threshold warning ($800/$1000)
- Worker timeout
- GitHub API rate limit

## Workflow: Complete Example

**Monday morning**: "Audit all 50 client repos for security issues"

```bash
# 1. Submit task
voice: "Audit all repos"
→ Agent Runtime task created
→ Router detects: security_scan, 50 repos
→ Spawns 5 workers (10 repos each)

# 2. Workers execute in parallel
Worker 1: Repos 1-10 (Checkov + trivy + semgrep)
Worker 2: Repos 11-20
Worker 3: Repos 21-30
Worker 4: Repos 31-40
Worker 5: Repos 41-50

# 3. Timeline
9:05 AM - Task submitted
11:05 AM - All workers complete (2 hours)
11:06 AM - Results aggregated
11:07 AM - 50 PRs created with findings

# 4. Review
Tuesday morning - Marc reviews PRs at leisure
Cost: $15-20 (vs $200+ if done locally)
Time saved: 40 hours of local machine time
```

## Debugging

```bash
# Check orchestrator logs
npm run logs

# Test routing decision for specific task
npm run test-routing -- --task-id task-123

# View Claude Code web session details
npm run session -- --session-id abc123

# Analyze cost for task
npm run cost-analysis -- --task-id task-123
```

## Limitations & Future

### Current Limitations
- Max 10 concurrent workers (cluster limit)
- Max 8 hours per task (timeout)
- GitHub API rate limits apply
- No GPU support yet

### Roadmap
- [ ] S3 artifact storage integration
- [ ] Email notifications on completion
- [ ] Slack/Discord notifications
- [ ] Cost forecasting
- [ ] Worker health monitoring
- [ ] Automatic retry on failure
- [ ] GPU-accelerated workers

## Configuration

Edit `config/routing-rules.json` to customize:
- Worker count per task type
- Cost thresholds
- Timeouts
- Task type mappings

Edit `src/router.ts` to add custom routing logic.

## Support

For issues:
1. Check logs: `npm run logs`
2. Test routing: `npm run test-routing`
3. Check memory: `npm run memory-status`
4. Review cost tracking: `npm run cost-analysis`

---

**You're now running a distributed compute layer for your agentic system.**

With $1000 in Claude Code web credits, you have:
- 500+ hours of parallel compute
- 5-10x parallelization
- Zero local resource consumption
- 24/7 autonomous execution capability
