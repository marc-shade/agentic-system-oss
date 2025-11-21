#!/bin/bash
set -e

echo "=========================================="
echo " Persistent Agent SDK Setup"
echo " Multi-Provider AI Agent Runtime"
echo "=========================================="
echo

# Check for required Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install required packages
echo "📦 Installing SDK dependencies..."
pip install anthropic openai google-generativeai asyncio > /dev/null 2>&1

echo "✅ All dependencies installed"
echo

# Check for API keys
echo "🔑 Checking API keys..."
KEYS_FOUND=0

if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✅ ANTHROPIC_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND + 1))
else
    echo "⚠️  ANTHROPIC_API_KEY not set"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ OPENAI_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND + 1))
else
    echo "⚠️  OPENAI_API_KEY not set"
fi

if [ -n "$GOOGLE_API_KEY" ] || [ -n "$GEMINI_API_KEY" ]; then
    echo "✅ GEMINI_API_KEY found"
    KEYS_FOUND=$((KEYS_FOUND + 1))
else
    echo "⚠️  GEMINI_API_KEY not set"
fi

echo
echo "API Keys configured: $KEYS_FOUND/3"

if [ $KEYS_FOUND -eq 0 ]; then
    echo "❌ Error: No API keys configured"
    echo
    echo "Please set at least one of the following environment variables:"
    echo "  - ANTHROPIC_API_KEY (for Claude Code)"
    echo "  - OPENAI_API_KEY (for Codex)"
    echo "  - GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini)"
    exit 1
fi

echo
echo "✅ Setup complete!"
echo
echo "To test the runtime:"
echo "  source venv/bin/activate"
echo "  python3 unified_agent_runtime.py"
echo
echo "To use in your code:"
echo "  from unified_agent_runtime import UnifiedAgentRuntime, AgentTask, TaskType"
echo
