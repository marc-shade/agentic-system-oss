# Workflow Automation Skill

Complete integration for AutoKitteh and Temporal workflow orchestration.

## When to Use This Skill

Use this skill when:
- Managing AutoKitteh workflows (.kitteh files)
- Creating or modifying Temporal workflows
- Orchestrating multi-system automation
- Scheduling autonomous tasks
- Monitoring workflow execution
- Debugging workflow failures
- Integrating Claude Code hooks with workflows

## AutoKitteh Integration

### Project Structure

```
/Volumes/FILES/agentic-system/autokitteh-workflows/
├── autokitteh.yaml          # Main manifest
├── system/                  # System workflows
│   ├── self_healing.kitteh
│   ├── ember_monitoring.kitteh
│   └── overnight_automation.kitteh
├── agi/                     # AGI workflows
│   ├── autonomous_goals.kitteh
│   └── memory_consolidation.kitteh
└── youtube/                 # YouTube workflows
    ├── transcript_extraction.kitteh
    └── video_analysis.kitteh
```

### Common Operations

#### Deploy Workflows

```bash
cd /Volumes/FILES/agentic-system/autokitteh-workflows
ak manifest validate autokitteh.yaml
ak deploy --manifest autokitteh.yaml
```

#### List Deployments

```bash
ak deployment list
ak deployment get <deployment-id>
ak deployment logs <deployment-id>
```

#### Trigger Workflows

```bash
# Manual trigger
ak workflow trigger <trigger-name>

# Via API
curl -X POST http://localhost:9980/api/v1/triggers/<trigger-id>/fire
```

#### Monitor Sessions

```bash
ak session list
ak session get <session-id>
ak session logs <session-id>
```

### Workflow Template

```yaml
version: v1
name: my-workflow

on:
  schedule:
    - cron: "0 0 * * *"
      name: daily_job
  webhook:
    - name: manual_trigger

connections:
  temporal:
    type: http
    url: "http://localhost:7233"
  voice_mode:
    type: http
    url: "http://localhost:3000"

functions:
  main_function:
    description: "Main workflow function"
    code: |
      import json
      import time

      def main():
          print("Workflow started")

          # Your logic here

          return {"status": "success"}
```

## Temporal Integration

### Project Structure

```
/Volumes/FILES/agentic-system/temporal-workflows/
├── infrastructure_health.py
├── ai_agent_monitoring.py
├── overnight_automation_workflow.py
├── start_ai_monitoring.sh
└── start_overnight_automation.sh
```

### Common Operations

#### Start Worker

```bash
cd /Volumes/FILES/agentic-system/temporal-workflows
./start_overnight_automation.sh

# Or manually
python3 overnight_automation_workflow.py
```

#### List Workflows

```bash
temporal workflow list
temporal workflow list --query 'WorkflowType="OvernightAutomationWorkflow"'
```

#### Start Workflow

```bash
temporal workflow start \
  --task-queue overnight-automation-queue \
  --type OvernightAutomationWorkflow \
  --workflow-id overnight-$(date +%Y%m%d)
```

#### Monitor Workflow

```bash
temporal workflow describe --workflow-id overnight-20251025
temporal workflow show --workflow-id overnight-20251025
```

#### Schedule Workflow

```bash
temporal schedule create \
  --schedule-id nightly-research \
  --workflow-id research \
  --task-queue research-queue \
  --workflow-type ResearchWorkflow \
  --cron "0 22 * * *"
```

### Workflow Template

```python
#!/usr/bin/env python3
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from datetime import timedelta

@activity.defn
async def my_activity(input: str) -> str:
    """Activity implementation"""
    activity.logger.info(f"Processing: {input}")
    return f"Processed: {input}"

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        """Workflow implementation"""
        workflow.logger.info("Workflow started")

        result = await workflow.execute_activity(
            my_activity,
            input,
            start_to_close_timeout=timedelta(minutes=5)
        )

        return result

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[MyWorkflow],
        activities=[my_activity]
    )

    await worker.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Integration Patterns

### AutoKitteh → Temporal

Use AutoKitteh to orchestrate Temporal workflows:

```yaml
# autokitteh.yaml
functions:
  trigger_temporal:
    code: |
      import requests

      response = requests.post(
          "http://localhost:7233/api/v1/workflows/start",
          json={
              "workflow_id": f"workflow-{session_id}",
              "workflow_type": "MyWorkflow",
              "task_queue": "my-queue",
              "input": {"triggered_by": "autokitteh"}
          }
      )
```

### Temporal → AutoKitteh

Signal AutoKitteh from Temporal workflows:

```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self):
        result = await workflow.execute_activity(...)

        # Signal AutoKitteh
        requests.post(
            "http://localhost:9980/api/v1/events",
            json={
                "event_type": "workflow.completed",
                "data": {"result": result}
            }
        )
```

### Claude Code Hooks → Both

From pre-tool-use.py or post-tool-use.py:

```python
import requests

# Trigger AutoKitteh event
requests.post(
    "http://localhost:9980/api/v1/events",
    json={"event_type": "tool.execution", "data": {...}}
)

# Signal Temporal workflow
from temporalio.client import Client

client = await Client.connect("localhost:7233")
handle = client.get_workflow_handle("monitor-workflow")
await handle.signal("tool-executed", {...})
```

## Active Workflows

### System Workflows

1. **self_healing.kitteh** (Every 5 min)
   - Checks config integrity
   - Restores from preservation_rules.json
   - Sends voice notifications

2. **ember_monitoring.kitteh** (Every 2 min)
   - Monitors Ember health
   - Auto-care (feed, play, clean)
   - Violation tracking

3. **overnight_automation.kitteh** (Daily 10 PM)
   - Triggers Temporal workflow
   - Monitors 9-hour execution window
   - Sends morning report

### Temporal Workflows

1. **infrastructure_health.py** (Continuous)
   - Service health monitoring
   - HTTP/port health checks
   - Voice alerts

2. **ai_agent_monitoring.py** (Continuous)
   - AI hook health checks
   - Test executions
   - System status monitoring

3. **overnight_automation_workflow.py** (Daily 10 PM)
   - Research discovery (4 cycles)
   - System maintenance
   - Morning report generation
   - Voice notifications

## Troubleshooting

### AutoKitteh Issues

```bash
# Check server status
ak status
ak health

# View logs
ak logs --follow

# Validate manifest
ak manifest validate autokitteh.yaml

# Check deployment
ak deployment list
ak deployment logs <deployment-id>

# Restart server
pkill -f "ak up"
nohup ak up --mode dev > /tmp/autokitteh.log 2>&1 &
```

### Temporal Issues

```bash
# Check server
curl http://localhost:7233/api/v1/health

# View workflows
temporal workflow list

# Check workers
temporal task-queue describe --task-queue my-queue

# View worker logs
tail -f /Volumes/FILES/agentic-system/temporal-workflows/overnight_automation.log

# Restart worker
kill $(cat overnight_automation.pid)
./start_overnight_automation.sh
```

## MCP Integration

Once the workflow-automation MCP is created, use these tools:

```typescript
// List AutoKitteh deployments
mcp__workflow-automation__list_deployments()

// Start Temporal workflow
mcp__workflow-automation__start_workflow({
  type: "MyWorkflow",
  taskQueue: "my-queue",
  input: {...}
})

// Monitor workflow
mcp__workflow-automation__get_workflow_status({
  workflowId: "my-workflow-123"
})

// Trigger AutoKitteh workflow
mcp__workflow-automation__trigger_autokitteh({
  triggerName: "my-trigger",
  eventData: {...}
})
```

## CLI Integration

Once the workflow CLI is created:

```bash
# AutoKitteh operations
workflow ak deploy
workflow ak list
workflow ak logs <deployment-id>
workflow ak trigger <name>

# Temporal operations
workflow temporal start MyWorkflow --queue my-queue
workflow temporal list
workflow temporal describe <workflow-id>
workflow temporal cancel <workflow-id>

# Combined operations
workflow status  # Shows both AutoKitteh and Temporal status
workflow health  # Health check on all systems
workflow monitor <workflow-id>  # Monitor specific workflow
```

## Best Practices

1. **Always validate manifests** before deploying
2. **Use versioned workflow IDs** for traceability
3. **Implement proper error handling** in workflows
4. **Set appropriate timeouts** on activities
5. **Use signals for communication** between workflows
6. **Log extensively** for debugging
7. **Monitor task queue depth** for scaling
8. **Use schedules** for recurring tasks
9. **Test workflows** in development first
10. **Implement retry logic** in activities

## References

- Complete CLI/API reference: `/Volumes/SSDRAID0/agentic-system/AUTOKITTEH_TEMPORAL_CLI_API_REFERENCE.md`
- Overnight automation: `/Volumes/FILES/agentic-system/OVERNIGHT_AUTOMATION_INTEGRATION.md`
- Full system integration: `/Volumes/SSDRAID0/agentic-system/AUTOMATION_SYSTEMS_COMPLETE.md`
- AutoKitteh docs: https://github.com/marc-shade/autokitteh
- Temporal docs: https://github.com/marc-shade/temporal
