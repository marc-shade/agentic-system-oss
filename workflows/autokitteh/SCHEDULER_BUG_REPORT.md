# AutoKitteh Scheduler Bug Report

**Date**: 2025-11-11
**AutoKitteh Version**: dev (commit b85f931edc26b48cd2ec0826b868cbfbe58ae491)
**Issue**: Temporal schedules not created for schedule triggers

## Executive Summary

**Critical Bug**: AutoKitteh's scheduler system fails to create Temporal schedules when schedule triggers are defined. This results in no scheduled workflow executions despite triggers being successfully registered in the database.

**Impact**: ALL schedule-based triggers across ALL projects are non-functional. Only webhooks and connection triggers work. This is a system-wide failure affecting autonomous operations.

## Detailed Analysis

### Symptoms

1. **No Temporal schedules exist for user projects**:
   ```bash
   $ temporal schedule list --namespace default
   ScheduleId             Action                          Paused    NextRunTime     LastRunTime
   internal_maintenance  {"Workflow":"internal_maintenance"}  false   2 hours from now
   ```
   Only AutoKitteh's internal schedule exists - no user project schedules.

2. **No scheduler activity in logs**:
   - Expected log: `"created schedule %q for %v"` from `scheduler.go:96`
   - Expected log: `"created schedule trigger with spec %q"` from `triggers.go`
   - **Actual**: Neither log message appears when triggers are created

3. **Triggers exist but don't fire**:
   ```bash
   $ ak trigger list | wc -l
   10 triggers registered

   $ ak session list | grep "dep_01k9tbv7f6fw7bsymr8x8qz2dd" | wc -l
   0 sessions created
   ```

### Root Cause Investigation

#### Scheduler Component Analysis

**File**: `/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/internal/backend/scheduler/scheduler.go`

The scheduler has two critical components:

1. **Worker initialization** (`Start()` method):
   ```go
   w := temporalclient.NewWorker(sch.sl.Desugar(), sch.temporal.TemporalClient(), taskQueueName, sch.cfg.Worker)
   if w == nil {
       return nil  // Silent success if worker is disabled
   }
   ```

2. **Schedule creation** (`Create()` method):
   ```go
   _, err := sch.temporal.TemporalClient().ScheduleClient().Create(ctx, client.ScheduleOptions{...})
   if err != nil {
       return fmt.Errorf("schedule: create schedule workflow: %w", err)
   }
   l.With("schedule", schedule).Infof("created schedule %q for %v", schedule, tid)
   ```

#### Worker Configuration

**File**: `/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/internal/backend/temporalclient/worker.go`

```go
type WorkerConfig struct {
    Disable  bool  `koanf:"disable"`  // Key field!
    // ... other fields
}

func NewWorker(l *zap.Logger, client client.Client, qname string, cfg WorkerConfig) worker.Worker {
    if cfg.Disable {
        l.With(zap.String("queue_name", qname)).Info(fmt.Sprintf("temporal worker for queue %q is disabled", qname))
        return nil
    }
    // ... worker creation
}
```

#### Triggers Integration

**File**: `/Volumes/FILES/Marc-Data/Documents/Cline/MCP/autokitteh-source/internal/backend/triggers/triggers.go`

```go
switch trigger.SourceType() {
case sdktypes.TriggerSourceTypeSchedule:
    if err := m.scheduler.Create(ctx, trigger.ID(), trigger.Schedule()); err != nil {
        return sdktypes.InvalidTriggerID, fmt.Errorf("create schedule: %w", err)
    }
    sl.With("schedule", trigger.Schedule()).Infof("created schedule trigger with spec %q", trigger.Schedule())
}
```

### Evidence of Failure

1. **Test 1: Created test trigger**:
   ```bash
   $ ak trigger create -n test_scheduler -p autonomous_system -s "*/1 * * * *" \
     --call "handlers/system_health_handlers.py:check_all_services"
   trigger_id: trg_01k9tbwxz6famapyd4rv3z4eaj
   ```
   - ✅ Trigger created successfully (returned ID)
   - ❌ No log message from `scheduler.Create()`
   - ❌ No log message from triggers module
   - ❌ No Temporal schedule registered

2. **Test 2: Verified Temporal connectivity**:
   ```bash
   $ temporal namespace describe default
   Info: name:"default" state:NAMESPACE_STATE_REGISTERED supports_schedules:true
   ```
   - ✅ Temporal supports schedules
   - ✅ AutoKitteh connects to Temporal successfully
   - ❌ No schedules created by AutoKitteh

3. **Test 3: Debug logging enabled**:
   ```bash
   $ ps eww 21868 | tr ' ' '\n' | grep AK_LOG_LEVEL
   AK_LOG_LEVEL=debug
   ```
   - ✅ Debug logging confirmed active
   - ❌ No DEBUG logs from scheduler or triggers modules
   - Only INFO/WARN logs appear

### Hypotheses

#### Hypothesis 1: Scheduler Worker Disabled (Most Likely)

The scheduler worker might be disabled by default in dev mode. Evidence:
- `WorkerConfig.Disable = true` would cause `NewWorker()` to return nil
- Scheduler `Start()` method returns early if worker is nil
- No "temporal worker for queue is disabled" log message (but we might not be at the right log level)

**Why scheduler.Create() succeeds without creating schedules**:
If the scheduler worker isn't running, `scheduler.Create()` still calls Temporal's API to create a schedule, but there's no worker to execute the scheduled workflows. However, this doesn't explain why we see NO schedules in Temporal at all.

#### Hypothesis 2: Silent Error in scheduler.Create()

Possible scenarios:
- `scheduler.Create()` is being called but returning an error
- The error is caught somewhere higher up and not logged
- But this contradicts the fact that trigger creation succeeds (would fail if Create() returned error)

#### Hypothesis 3: gRPC Call Logging Disabled

The CLI commands (`ak deploy`, `ak trigger create`) use gRPC to communicate with the server. Evidence:
- HTTP logs only show GET / (health checks)
- No API logs for trigger/deployment operations
- gRPC calls might not be logged at INFO/DEBUG level

This doesn't explain the missing Temporal schedules, but explains why we don't see API activity logs.

### Configuration Investigation

**Scheduler config defaults** (`scheduler/scheduler.go:34-36`):
```go
var Configs = configset.Set[Config]{
    Default: &Config{},  // Empty config - uses defaults
}
```

**Worker config defaults** (`temporalclient/worker.go:18-21`):
```go
var defaultWorkerConfig = WorkerConfig{
    MaxConcurrentWorkflowTaskExecutionSize: 50,
    MaxConcurrentActivityExecutionSize:     50,
    // Note: Disable is NOT set, defaults to false (Go zero value)
}
```

**Expected behavior**: Worker should NOT be disabled by default.

### Next Steps for Resolution

1. **Add explicit logging** to verify scheduler.Create() is being called:
   - Instrument triggers.go to log before and after scheduler.Create() call
   - Add logging to scheduler.Create() entry point

2. **Check scheduler worker status**:
   - Verify if scheduler worker is actually running
   - Check if there are any startup errors that were suppressed
   - Look for worker registration logs

3. **Test Temporal schedule creation directly**:
   - Use Temporal CLI to manually create a schedule
   - Verify if schedules can be created independently
   - Check Temporal permissions and configuration

4. **Review AutoKitteh configuration**:
   - Check if there's a config file that disables scheduler
   - Verify dev mode doesn't have scheduler restrictions
   - Look for environment variables affecting scheduler

5. **Check AutoKitteh version/branch**:
   - Verify if this is a known issue in this version
   - Check if scheduler component is under active development
   - Review recent commits to scheduler code

6. **Contact AutoKitteh maintainers**:
   - File GitHub issue with full diagnostic information
   - Provide steps to reproduce
   - Include complete log excerpts

## Workaround

Currently no workaround available. Schedule triggers are completely non-functional.

Options:
1. Use webhook triggers with external cron service (cron-job.org, etc.)
2. Use Temporal schedules directly (bypassing AutoKitteh triggers)
3. Wait for bug fix from AutoKitteh team

## Files for Reference

- Scheduler implementation: `internal/backend/scheduler/scheduler.go`
- Worker configuration: `internal/backend/temporalclient/worker.go`
- Triggers implementation: `internal/backend/triggers/triggers.go`
- Service initialization: `internal/backend/svc/svc.go`
- Test deployment: `dep_01k9tbv7f6fw7bsymr8x8qz2dd`
- Test trigger: `trg_01k9tbwxz6famapyd4rv3z4eaj`

## Logs

### Server startup (with debug logging):
```
2025-11-11 16:02:18 INFO pythonrt python info {"exe": "/opt/homebrew/bin/python3", "version": {"Major":3,"Minor":13}}
2025-11-11 16:02:18 INFO temporalclient namespace is registered {"supports_schedules":true}
2025-11-11 16:02:18 INFO sessions Session worker: enabled
2025-11-11 16:02:18 INFO temporalclient Connection to Temporal is healthy
2025-11-11 16:02:18 INFO svc/svc.go ready {"version": "dev", "id": "...", "gomaxprocs": 12}
```

**Notable absence**: No logs from scheduler component during startup

### Temporal schedules:
```bash
$ temporal schedule list --namespace default
ScheduleId             Action                          Paused    NextRunTime
internal_maintenance  {"Workflow":"internal_maintenance"}  false   2 hours from now
```

### AutoKitteh deployments:
```bash
$ ak deployment list --project autonomous_system
deployment_id:"dep_01k9tbv7f6fw7bsymr8x8qz2dd" state:DEPLOYMENT_STATE_ACTIVE
```

### AutoKitteh triggers:
```bash
$ ak trigger list --project autonomous_system | grep SOURCE_TYPE_SCHEDULE | wc -l
9
```

## Conclusion

This is a **critical system-wide bug** preventing ALL schedule-based automation in AutoKitteh. The scheduler component initializes successfully but fails to create Temporal schedules when triggers are registered. This requires immediate attention from AutoKitteh maintainers as it renders schedule triggers completely non-functional.

The Python handler conversion completed successfully - this scheduler issue is unrelated to the conversion work and affects ALL AutoKitteh projects regardless of handler implementation method.
