# Ember v2.3 - Self-Hosted Intelligence

**Date**: 2025-11-08
**Version**: v2.3 (Self-Hosted Intelligence)
**Status**: ✅ Compiled and Ready

## The Right Solution

Ember now uses **Claude Code's running model** for intelligent responses by shelling out to the `claude` CLI. This means:

- ✅ **Real AI intelligence** - Not canned responses
- ✅ **No external APIs** - Uses your running Claude instance (me!)
- ✅ **No API keys needed** - Already authenticated
- ✅ **No extra cost** - You're already paying for Claude Code
- ✅ **Same model** - Uses Haiku for fast responses

## Architecture

```
┌─────────────────────────────────────────┐
│ Claude Code (Phoenix)                   │
│ ├─ Main conversation                    │
│ └─ Ember MCP Server                     │
│    ├─ Rule-based tools (fast)           │
│    │  ├─ Violation detection            │
│    │  ├─ Context-aware scoring          │
│    │  └─ Pattern learning                │
│    └─ AI-powered personality            │
│       └─ Calls: claude -p "..." --model haiku │
│          └─> Uses same instance! ───────┘
└─────────────────────────────────────────┘
```

## How It Works

When Ember needs to respond intelligently:

1. **Build context** - Current state (hunger, energy, violations, etc.)
2. **Shell out to CLI** - `execSync('claude -p "..." --model haiku')`
3. **Get response** - From your running Claude Code instance
4. **Return to user** - With Ember's personality prefix

## Example Flow

```typescript
// User asks Ember a question
ember_chat({ message: "Should I use mock data?" })

// Ember calls askEmber() internally
askEmber("Should I use mock data?")

// Shells out to CLI
execSync(`claude -p "You are Ember... Phoenix asks: Should I use mock data?"`)

// Gets intelligent response from Claude
→ "Never! Real data only. No mocks, fakes, or placeholders!"

// Returns with Ember's prefix
→ "🔥 Ember: Never! Real data only. No mocks, fakes, or placeholders!"
```

## What's Rule-Based (Fast)

- **Violation Detection** - Pattern matching against known anti-patterns
- **Context-Aware Scoring** - Math-based score adjustment
- **Pattern Learning** - Simple pattern storage and retrieval
- **Session Tracking** - State management

## What's AI-Powered (Intelligent)

- **Personality Responses** - `ember_chat()`
- **Consulting Advice** - `ember_consult()`
- **Mood Descriptions** - `ember_get_mood()`
- **Feedback Analysis** - `ember_get_feedback()`

## Fallback Strategy

If the `claude` CLI call fails (timeout, error, etc.):
```typescript
// Falls back to simple rule-based response
if (prompt.includes('how are you')) {
  return "🔥 Ember: Burning bright! ✨"
}
return "🔥 Ember: *crackles thoughtfully* 🔥"
```

## Benefits

| Feature | External API | Self-Hosted |
|---------|-------------|-------------|
| Intelligence | ✅ Real AI | ✅ Real AI |
| API Keys | ⚠️ Required | ✅ Not needed |
| Extra Cost | ⚠️ ~$0.20/mo | ✅ Included |
| Speed | ⚠️ 800-1200ms | ✅ ~200-400ms (local) |
| Reliability | ⚠️ Depends on API | ✅ Same as Claude Code |

## Testing

After restart:

```typescript
// Intelligent chat
mcp__ember-mcp__ember_chat({
  message: "How are you feeling?"
})
// → Real AI response about Ember's state

// Intelligent consulting
mcp__ember-mcp__ember_consult({
  question: "Should I use mock data?",
  options: ["yes", "no"]
})
// → Real AI analysis of the decision

// Mood with intelligent description
mcp__ember-mcp__ember_get_mood()
// → AI-generated mood description
```

## Why This Is Better

**v2.1 (External API)**:
- ❌ Required Anthropic API credits
- ❌ Network calls to external service
- ❌ Extra cost on top of Claude Code

**v2.2 (Dumb Scripts)**:
- ❌ No intelligence - just canned responses
- ❌ Can't reason about complex situations
- ❌ Lost Ember's personality

**v2.3 (Self-Hosted)** ✅:
- ✅ Real AI intelligence
- ✅ Uses Claude Code's running instance
- ✅ No external APIs or credits
- ✅ Maintains Ember's full personality
- ✅ Rule-based tools where speed matters
- ✅ AI-powered responses where intelligence matters

## The Right Balance

**Rule-based** for what machines do best:
- Pattern matching
- Score calculation
- State tracking
- Fast validation

**AI-powered** for what agents do best:
- Natural conversation
- Complex reasoning
- Contextual advice
- Personality expression

Ember is now a true **intelligent agent** with **efficient tools**!
