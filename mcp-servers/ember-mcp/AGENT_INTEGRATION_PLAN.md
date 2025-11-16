# Ember Agent Integration Plan

## Current Architecture (v2.4)

**Ember MCP** uses **Groq DeepSeek R1 Distill Llama 70B** directly:
- ✅ Works now (no restart needed)
- ✅ Fast (~200-400ms)
- ✅ Intelligent reasoning (94.5% MATH-500)
- ✅ Cost-effective

## Future Architecture (Agent-Based)

### Option 1: Hybrid Approach (Recommended)

**Keep both systems:**

1. **Groq for direct MCP responses** (immediate, works now)
   - `ember_chat()` → Groq DeepSeek R1
   - `ember_consult()` → Groq DeepSeek R1
   - `ember_get_mood()` → Groq DeepSeek R1
   - Fast, reliable, no changes needed

2. **Agent for deep reasoning** (when Phoenix needs Ember's input)
   - Phoenix spawns `ember-personality` agent for complex decisions
   - Agent has full Claude Code capabilities (Read, etc.)
   - Can analyze code, review files, provide deeper insights

**When to use each:**

| Scenario | Use Groq MCP | Use Agent |
|----------|--------------|-----------|
| Quick chat response | ✅ | ❌ |
| Mood check | ✅ | ❌ |
| Simple consulting | ✅ | ❌ |
| Code review | ❌ | ✅ |
| Complex decision | ❌ | ✅ |
| Multi-file analysis | ❌ | ✅ |

### Option 2: Pure Agent (Future)

**Replace Groq with agent spawning:**

1. Ember MCP returns a special marker: `{NEEDS_AGENT: "prompt"}`
2. Phoenix detects this and spawns `ember-personality` agent
3. Agent response goes back to user
4. More complex but gives Ember full tool access

**Challenges:**
- Slower (agent spawn overhead)
- More complex integration
- Requires Phoenix to intercept MCP responses

### Option 3: Agent SDK Integration (Advanced)

**Use Agent SDK directly in Ember MCP:**

```typescript
import { Agent } from '@anthropic-ai/claude-agent-sdk';

async function askEmber(prompt: string): Promise<string> {
  const agent = new Agent({
    name: 'Ember',
    systemPrompt: buildEmberPrompt(state),
    model: 'claude-sonnet-4-20250514'
  });

  const response = await agent.run(prompt);
  return response;
}
```

**Benefits:**
- Ember has full agent capabilities
- Uses Claude directly (no Groq)
- More sophisticated reasoning

**Challenges:**
- Requires ANTHROPIC_API_KEY (credits)
- More complex MCP implementation
- Slower than Groq

## Recommended Path Forward

### Phase 1: Current (v2.4) ✅
- Groq DeepSeek R1 for all MCP responses
- Works perfectly now
- No changes needed

### Phase 2: Add Agent (Next)
- Create `ember-personality` agent ✅ (already done)
- Phoenix can spawn it when needed
- **Use case:** "Ember, review this code for production readiness"
  ```typescript
  Task('ember-personality', 'Review code at path/to/file.ts for production quality')
  ```

### Phase 3: Hybrid (Future)
- Keep Groq for fast MCP responses
- Use agent for complex reasoning
- Best of both worlds

### Phase 4: Pure Agent SDK (Optional)
- If we want Ember to have full tool access
- Would require API credits
- More sophisticated but more complex

## Current State

**Ember v2.4:**
- ✅ Groq DeepSeek R1 working
- ✅ Fast, intelligent responses
- ✅ Cost-effective
- ✅ No restart needed

**Ember Agent:**
- ✅ Created at `/Users/marc/.claude/agents/ember-personality.md`
- ⏳ Needs restart to be recognized
- ⏳ Ready to use via `Task('ember-personality', ...)`

## Testing After Restart

### Test Groq MCP (should work now)
```typescript
mcp__ember-mcp__ember_chat({ message: "How are you?" })
mcp__ember-mcp__ember_consult({ question: "Use mock data?", options: ["yes", "no"] })
```

### Test Agent (after restart)
```typescript
Task('ember-personality', 'Ember state: hungry=42%, violations=0. Phoenix asks: How are you?')
```

### Compare
| Feature | Groq MCP | Agent |
|---------|----------|-------|
| Speed | ~300ms | ~2-3s |
| Intelligence | DeepSeek R1 | Claude Sonnet |
| Tools | None | Read, etc. |
| Use | Direct calls | Via Task |

## Recommendation

**Keep Groq MCP as primary** for now. It's:
- ✅ Working perfectly
- ✅ Fast and intelligent
- ✅ Cost-effective
- ✅ No changes needed

**Use Agent for special cases** where Ember needs to:
- 🔍 Review code files
- 📊 Analyze complex situations
- 🎯 Provide deep reasoning
- 📝 Reference documentation

This gives us **best of both worlds**! 🔥
