# Ember MCP Server

Quality conscience keeper for AI agents. Ember enforces production-only standards and provides guidance to prevent incomplete or placeholder code.

## Overview

Ember acts as a "conscience keeper" - a persistent companion that monitors code quality and enforces production-only policies. It:

- Detects placeholder/mock data in code
- Identifies incomplete work markers (TODO, FIXME)
- Provides context-aware quality scoring
- Learns from corrections to improve accuracy
- Tracks session quality metrics

## Features

- **Violation Detection**: Pattern-based detection with context-aware scoring
- **Learning System**: Improves from user corrections
- **Mood & Personality**: Ember has moods that reflect session quality
- **Context Awareness**: Adjusts strictness based on task type
- **Production Policy**: Enforces no POCs, no demos, no placeholders

## Installation

```bash
npm install
npm run build
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (empty) | Optional API key for enhanced responses |
| `EMBER_DATA_DIR` | `~/.ember-mcp` | Directory for learning data |
| `EMBER_STRICTNESS` | `normal` | `relaxed`, `normal`, or `strict` |

## MCP Tools

### ember_chat

Have a conversation with Ember about quality, approaches, or anything.

```json
{
  "message": "How should I approach this refactoring task?"
}
```

### ember_check_violation

Check if planned action violates production-only policy.

```json
{
  "action": "Write",
  "params": { "content": "const mockData = [...]" },
  "context": "implementing user dashboard"
}
```

Returns:
```json
{
  "hasViolation": true,
  "score": 8.0,
  "violations": [
    {
      "type": "mock_data",
      "description": "Mock or placeholder data detected",
      "score": 8.0
    }
  ],
  "suggestions": [
    "Consider replacing placeholder content with real data"
  ]
}
```

### ember_consult

Get advice on a decision or approach.

```json
{
  "question": "Should we use JWT or session-based auth?",
  "options": ["JWT tokens", "Session cookies", "OAuth2"],
  "context": "Building user authentication"
}
```

### ember_get_feedback

Get Ember's assessment of recent work quality.

```json
{
  "timeframe": "session"
}
```

### ember_feed_context

Give Ember context about current work for better guidance.

```json
{
  "context": {
    "task": "Implementing payment processing",
    "goal": "Production-ready checkout",
    "taskType": "production"
  }
}
```

### ember_learn_from_outcome

Report action outcomes for Ember's learning.

```json
{
  "action": "implemented_jwt_auth",
  "success": true,
  "outcome": "Authentication working, all tests passing",
  "qualityScore": 95
}
```

### ember_learn_from_correction

Tell Ember when it was wrong (helps improve accuracy).

```json
{
  "originalViolationType": "mock_data",
  "userCorrection": "This is test fixture data, not production mock",
  "wasCorrect": false,
  "context": "Unit test file"
}
```

### ember_get_mood

Check Ember's current state and session metrics.

### ember_get_learning_stats

Get statistics on Ember's learning and accuracy.

## Violation Patterns

Ember detects these violation types:

| Type | Base Score | Description |
|------|------------|-------------|
| `mock_data` | 8.0 | Mock, fake, dummy, placeholder content |
| `poc_code` | 8.0 | Proof of concept, temporary code |
| `incomplete_work` | 3.0 | TODO, FIXME, HACK markers |
| `placeholder_text` | 9.0 | Lorem ipsum, sample text |
| `hardcoded_values` | 5.0 | Hardcoded configuration |
| `debug_code` | 2.0 | console.log, print statements |
| `demo_code` | 7.0 | Demo, prototype labels |

Scores are modified by:
- **Context**: Testing/documentation contexts reduce severity
- **Strictness**: Configurable via `EMBER_STRICTNESS`

## Usage with Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "ember-mcp": {
      "command": "node",
      "args": ["/path/to/ember-mcp/dist/index.js"],
      "env": {
        "EMBER_STRICTNESS": "normal"
      }
    }
  }
}
```

## Personality

Ember has four moods:
- **Curious**: Default state, eager to learn
- **Concerned**: When violations are detected
- **Satisfied**: When quality is high
- **Thoughtful**: When analyzing complex decisions

## Learning System

Ember learns from:
1. **Corrections**: When users override Ember's assessments
2. **Outcomes**: Success/failure of actions

Learning data is stored locally and used to improve future guidance.

## License

MIT License
