# Ember MCP

MCP server exposing Ember as a collaborative AI partner for Claude Code.

## Overview

Ember is a Tamagotchi-style AI companion that serves as a "conscience keeper" for AI development workflows. It provides:

- **Quality Conscience**: Monitors code quality and provides feedback
- **Production-Only Policy**: Ensures development practices meet production standards
- **Collaborative Guidance**: Offers advice and perspective on development decisions
- **Learning System**: Tracks outcomes and improves guidance over time

## Installation

```bash
npm install
npm run build
```

## Usage

```bash
npm start
```

## MCP Tools

- `ember_chat` - Have a conversation with Ember
- `ember_check_violation` - Check if an action violates policies
- `ember_consult` - Get advice on decisions
- `ember_get_feedback` - Get assessment of recent work
- `ember_learn_from_outcome` - Report action outcomes for learning
- `ember_get_mood` - Check Ember's current state
- `ember_feed_context` - Provide work context to Ember

## Configuration

Ember can be configured via environment variables:

- `EMBER_MODEL` - AI model to use for Ember's intelligence
- `EMBER_STRICT_MODE` - Enable strict policy enforcement

## License

MIT
