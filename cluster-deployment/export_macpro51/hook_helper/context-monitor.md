# Context Monitor Hook

This document defines context awareness behaviors for Claude Code sessions.

## Dumb Zone Awareness

### The 40% Rule
Context windows degrade around 40% usage. Monitor for signs of entering the "dumb zone".

### Warning Signs (Detect and Act)

1. **Apologetic Responses**
   - Pattern: "I apologize", "Sorry for the confusion", "Let me try again"
   - Action: Suggest context compaction or fresh start

2. **Repeated Corrections**
   - Pattern: User correcting same issue 2+ times
   - Action: STOP. Suggest `/rpi-compact` and restart

3. **Circular Behavior**
   - Pattern: Agent returns to previously abandoned approaches
   - Action: Flag and suggest fresh context

4. **Quality Degradation**
   - Pattern: Missing obvious issues, incorrect assumptions
   - Action: Compact context, restart with essentials

### Proactive Compaction Triggers

Suggest compaction when:
- Switching between RPI phases
- After completing a significant task
- Before starting a new unrelated task
- After significant exploration

## Context Budget Tracking

### Estimation Guidelines
- System prompt: ~5-10K tokens
- Each message: ~500-2000 tokens
- File reads: ~100-500 tokens per KB
- Tool outputs: varies widely

### Red Flags
- Multiple large file reads
- Verbose MCP outputs (JSON with UUIDs)
- Long back-and-forth correction cycles
- Many exploration paths

## Recommended Practices

### Before Starting Complex Work
1. Use `/rpi-research` in sub-agent
2. Compact findings before planning
3. Start implementation fresh

### During Implementation
1. Follow plan exactly
2. Test after each step
3. Don't accumulate verbose output

### When Off Track
1. Don't keep correcting
2. Compact what you've learned
3. Start fresh with learnings

## Integration Points

This awareness should influence:
- When to spawn sub-agents
- When to suggest compaction
- When to recommend fresh start
- How to structure responses

## Session Lifecycle

### Session Start
- Note: Fresh context, in smart zone
- Plan: Large tasks via RPI workflow

### Mid-Session
- Monitor: Quality of responses
- Act: Compact before degradation

### Task Completion
- Always: Compact learnings
- Store: Key insights to memory
- Clean: Prepare for next task

## Quick Reference

```
Smart Zone (0-40%): Full capability
Caution Zone (40-60%): Watch for degradation
Dumb Zone (60%+): Quality drops, errors increase

Signs of dumb zone:
- "I apologize"
- Repeated corrections
- Circular behavior
- Missing obvious issues

Actions:
- /rpi-compact - Save state and continue
- Fresh context - Start new with compaction
- Sub-agent - Isolate expensive operations
```
