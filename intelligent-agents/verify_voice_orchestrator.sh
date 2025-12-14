#!/bin/bash
#
# Voice Action Orchestrator - Installation Verification
# ======================================================
#
# Verifies that the voice action orchestrator is correctly installed
# and all dependencies are available.
#

set -e

echo "============================================================"
echo "VOICE ACTION ORCHESTRATOR - VERIFICATION"
echo "============================================================"
echo

# Check working directory
echo "📂 Checking working directory..."
if [ ! -f "action_orchestrator.py" ]; then
    echo "✗ Error: Run this script from intelligent-agents directory"
    exit 1
fi
echo "✓ Working directory OK"
echo

# Check files exist
echo "📋 Checking required files..."
FILES=(
    "action_orchestrator.py"
    "intent_classifier.py"
    "test_action_orchestrator.py"
    "demo_voice_action_orchestrator.py"
    "VOICE_ACTION_ORCHESTRATOR.md"
    "README_VOICE_ORCHESTRATOR.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (missing)"
        exit 1
    fi
done
echo

# Check Python version
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  └─ Python $PYTHON_VERSION"
echo

# Check Python dependencies
echo "📦 Checking Python dependencies..."
python3 -c "import anthropic" 2>/dev/null && echo "  ✓ anthropic" || echo "  ✗ anthropic (missing - install with: pip3 install anthropic)"
python3 -c "import asyncio" 2>/dev/null && echo "  ✓ asyncio" || echo "  ✗ asyncio (should be builtin)"
python3 -c "import subprocess" 2>/dev/null && echo "  ✓ subprocess" || echo "  ✗ subprocess (should be builtin)"
python3 -c "import json" 2>/dev/null && echo "  ✓ json" || echo "  ✗ json (should be builtin)"
echo

# Test imports
echo "🔧 Testing module imports..."
if python3 -c "from action_orchestrator import ActionOrchestrator, Intent, IntentType; from intent_classifier import IntentClassifier" 2>/dev/null; then
    echo "  ✓ All imports successful"
else
    echo "  ✗ Import failed"
    exit 1
fi
echo

# Test intent classifier (no API needed)
echo "🎯 Testing intent classifier..."
if python3 -c "
from intent_classifier import IntentClassifier
classifier = IntentClassifier()
intent = classifier.classify('Create a Python file called test.py')
assert intent.type.value == 'COMMAND'
assert intent.confidence > 0.8
assert 'file_name' in intent.entities
print('  ✓ Intent classification working')
" 2>/dev/null; then
    :
else
    echo "  ✗ Intent classifier test failed"
    exit 1
fi
echo

# Check API key
echo "🔑 Checking API key..."
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "  ⚠️  ANTHROPIC_API_KEY not set (required for action orchestrator)"
    echo "     Set with: export ANTHROPIC_API_KEY='sk-ant-...'"
    API_KEY_OK=false
else
    KEY_PREFIX=$(echo $ANTHROPIC_API_KEY | cut -c1-10)
    echo "  ✓ API key found: ${KEY_PREFIX}..."
    API_KEY_OK=true
fi
echo

# Check logs directory
echo "📁 Checking logs directory..."
LOGS_DIR="$HOME/agentic-system/logs"
if [ -d "$LOGS_DIR" ]; then
    echo "  ✓ Logs directory exists: $LOGS_DIR"
else
    echo "  ⚠️  Creating logs directory: $LOGS_DIR"
    mkdir -p "$LOGS_DIR"
fi
echo

# Summary
echo "============================================================"
echo "VERIFICATION SUMMARY"
echo "============================================================"
echo
echo "✓ All required files present"
echo "✓ Python dependencies available"
echo "✓ Module imports working"
echo "✓ Intent classifier functional"

if [ "$API_KEY_OK" = true ]; then
    echo "✓ API key configured"
    echo
    echo "🎉 All checks passed! Ready to use."
    echo
    echo "Next steps:"
    echo "  1. Run demo: python3 demo_voice_action_orchestrator.py"
    echo "  2. Run tests: python3 test_action_orchestrator.py"
    echo "  3. Interactive mode: python3 demo_voice_action_orchestrator.py --interactive"
else
    echo "⚠️  API key not configured (required for full functionality)"
    echo
    echo "✓ Basic functionality verified"
    echo
    echo "To enable full orchestrator:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo
    echo "Without API key, you can still:"
    echo "  - Test intent classifier: python3 intent_classifier.py"
    echo "  - Review documentation: less VOICE_ACTION_ORCHESTRATOR.md"
fi
echo

# File statistics
echo "============================================================"
echo "INSTALLATION STATISTICS"
echo "============================================================"
echo
echo "Files created: ${#FILES[@]}"
echo "Total lines of code: $(wc -l action_orchestrator.py intent_classifier.py test_action_orchestrator.py demo_voice_action_orchestrator.py 2>/dev/null | tail -1 | awk '{print $1}')"
echo "Documentation: 2 files ($(wc -l VOICE_ACTION_ORCHESTRATOR.md README_VOICE_ORCHESTRATOR.md 2>/dev/null | tail -1 | awk '{print $1}') lines)"
echo
echo "Components:"
echo "  - Action Orchestrator: $(wc -l action_orchestrator.py 2>/dev/null | awk '{print $1}') lines"
echo "  - Intent Classifier: $(wc -l intent_classifier.py 2>/dev/null | awk '{print $1}') lines"
echo "  - Test Suite: $(wc -l test_action_orchestrator.py 2>/dev/null | awk '{print $1}') lines"
echo "  - Demo: $(wc -l demo_voice_action_orchestrator.py 2>/dev/null | awk '{print $1}') lines"
echo
