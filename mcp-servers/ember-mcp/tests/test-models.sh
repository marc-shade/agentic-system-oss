#!/bin/bash
# Test Ember with different AI models and compare

echo "🔥 Ember Model Comparison Test"
echo "================================"
echo ""

# Test questions for Ember
TEST_PROMPT="Phoenix is consulting you about implementing a new feature. Should we use a temporary POC approach first, or build the production version directly? Consider code quality and time constraints."

echo "Test Prompt:"
echo "$TEST_PROMPT"
echo ""
echo "================================"
echo ""

# Function to test a model
test_model() {
    local provider=$1
    local name=$2

    echo "Testing: $name"
    echo "Provider: $provider"
    echo "---"

    # Start time
    start=$(date +%s%N)

    # Run test (this would normally go through MCP, but for quick test we'll use Claude Code)
    echo "Starting test..."

    # End time
    end=$(date +%s%N)
    duration=$(( (end - start) / 1000000 ))

    echo "Response time: ${duration}ms"
    echo ""
}

echo "📊 MODEL COMPARISON"
echo "==================="
echo ""

echo "1️⃣  GROQ (Llama 3.3 70B) - CURRENT"
echo "   Expected: ~300-500ms, Good quality"
echo ""

echo "2️⃣  CLAUDE HAIKU"
echo "   Expected: ~500-800ms, Better reasoning"
echo ""

echo "3️⃣  CLAUDE SONNET 4.5"
echo "   Expected: ~800-1200ms, Best reasoning"
echo ""

echo "================================"
echo ""
echo "To test manually, restart Claude Code with:"
echo ""
echo "# For Haiku:"
echo "export EMBER_PROVIDER=claude-haiku"
echo ""
echo "# For Sonnet:"
echo "export EMBER_PROVIDER=claude-sonnet"
echo ""
echo "# For Groq:"
echo "export EMBER_PROVIDER=groq"
echo ""
echo "Then use ember_consult or ember_chat to test!"
