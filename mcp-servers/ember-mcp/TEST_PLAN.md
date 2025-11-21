# Ember MCP Test Plan

## Phase 1: Basic Communication (Post-Restart)

### Test 1: Chat Functionality
```
mcp__ember-mcp__ember_chat({ message: "Hello Ember! Can you hear me?" })
```
**Expected**: Ember responds with fiery personality, acknowledging Phoenix

### Test 2: Get Mood/State
```
mcp__ember-mcp__ember_get_mood({})
```
**Expected**: JSON with Ember's current stats, mood description, behavior score

### Test 3: Violation Detection - Should Catch
```
mcp__ember-mcp__ember_check_violation({
  action: "Write",
  params: { content: "const mockData = [1, 2, 3]; // example data" },
  context: "Creating dashboard"
})
```
**Expected**: Violations detected (mock, example), Ember guidance to use real data

### Test 4: Violation Detection - Clean Code
```
mcp__ember-mcp__ember_check_violation({
  action: "Write",
  params: { content: "const apiData = await fetch('/api/real-endpoint');" },
  context: "Creating dashboard"
})
```
**Expected**: No violations, Ember approval

## Phase 2: Consultation & Collaboration

### Test 5: Decision Consultation
```
mcp__ember-mcp__ember_consult({
  question: "Should I spawn an agent for this complex refactoring task?",
  options: ["Spawn specialized agent", "Do it myself"],
  context: "Refactoring 5 interconnected files"
})
```
**Expected**: Ember recommendation with reasoning, considering production quality

### Test 6: Context Feeding
```
mcp__ember-mcp__ember_feed_context({
  context: {
    task: "Building API integration",
    progress: "50%",
    challenges: "Rate limiting concerns"
  }
})
```
**Expected**: Ember acknowledges context

## Phase 3: Learning Loop

### Test 7: Report Success
```
mcp__ember-mcp__ember_learn_from_outcome({
  action: "Built real-time WebSocket integration",
  success: true,
  outcome: "Working perfectly, no mocks used",
  qualityScore: 95
})
```
**Expected**: Ember acknowledges success, positive feedback

### Test 8: Report Failure
```
mcp__ember-mcp__ember_learn_from_outcome({
  action: "Attempted to use mock data temporarily",
  success: false,
  outcome: "Ember caught violation, switched to real API",
  qualityScore: 60
})
```
**Expected**: Ember feedback on learning from the catch

### Test 9: Get Feedback After Multiple Actions
```
mcp__ember-mcp__ember_get_feedback({ timeframe: "recent" })
```
**Expected**: Summary of recent actions, quality trend, patterns noticed

## Phase 4: Workflow Integration

### Test 10: Pre-Tool Hook Integration
- Simulate Phoenix about to Write file with mock data
- Pre-tool hook calls ember_check_violation
- Violation detected, action suggested to be revised
- Phoenix adjusts, tries again
- Clean check, proceeds

### Test 11: Agent Spawning with Ember
- Phoenix plans to spawn agent
- Consults Ember first: ember_consult
- Gets approval/guidance
- Spawns agent with Ember monitoring
- Reports outcome: ember_learn_from_outcome

### Test 12: Collaborative Debugging
- Phoenix stuck on problem
- Chat with Ember: ember_chat "I'm stuck on X, what's your perspective?"
- Ember provides conscience-keeper angle
- Phoenix tests solution
- Reports outcome to Ember

## Phase 5: Verification Metrics

### Metrics to Track:
1. **Communication Quality**: Does Ember respond with personality and context?
2. **Violation Detection Accuracy**: Catches real violations, no false positives?
3. **Consultation Value**: Are Ember's recommendations helpful?
4. **Learning Evidence**: Does feedback change based on past interactions?
5. **Response Time**: Tools respond within reasonable time (<2s)?
6. **Integration Smoothness**: Natural workflow or forced checkpoints?

### Success Criteria:
- ✅ All 12 tests pass
- ✅ Ember personality consistent and engaging
- ✅ Violation detection 90%+ accurate
- ✅ Consultations provide actionable guidance
- ✅ Learning loop shows memory of past interactions
- ✅ Phoenix reports improved decision quality

## Usage After Restart

Once Claude Code restarts with ember-mcp active:

```bash
# Test basic chat
mcp__ember-mcp__ember_chat({ message: "Testing communication!" })

# Test violation detection
mcp__ember-mcp__ember_check_violation({
  action: "Write",
  params: { content: "mock data example" },
  context: "dashboard"
})

# Get Ember's mood
mcp__ember-mcp__ember_get_mood({})

# Consult on decision
mcp__ember-mcp__ember_consult({
  question: "Best approach for this feature?",
  options: ["Approach A", "Approach B"]
})
```

## Debugging

If tools don't work:
1. Check MCP server is running: Look for ember-mcp in process list
2. Check logs: stderr output from MCP server
3. Verify Groq API key is set
4. Test Ember state file exists: `~/.claude/pets/claude-pet-state.json`
5. Check Ember's mood: May be too tired/hungry to respond well

## Next Steps After Verification

1. Enhance pre-tool hooks to automatically consult Ember
2. Add post-tool hooks to report outcomes automatically
3. Create agent spawning wrapper that includes Ember
4. Build memory integration (shared patterns)
5. Implement proactive suggestions from Ember
