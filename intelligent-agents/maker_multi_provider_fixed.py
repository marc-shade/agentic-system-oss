#!/usr/bin/env python3
"""
MAKER Multi-Provider Agent (Fixed)
===================================

Uses diverse AI providers for voting:
1. ✅ OpenAI Codex CLI (proven working)
2. ✅ Ollama Cloud gpt-oss:20b-cloud (with JSON extraction)
3. ⚠️  Claude Haiku (needs Task tool - implement separately)
4. ⚠️  Gemini CLI (needs non-subprocess approach)

For now, uses Codex (70%) + Ollama (30%) distribution.
