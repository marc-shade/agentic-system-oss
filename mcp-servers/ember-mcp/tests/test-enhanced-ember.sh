#!/bin/bash
# Test Enhanced Ember MCP in isolated tmux session
# This tests the improvements without affecting production

set -e

echo "🔥 Enhanced Ember Test Suite"
echo "=============================="
echo ""

# Test directory
TEST_DIR="/tmp/ember-enhanced-test-$$"
mkdir -p "$TEST_DIR"

echo "Test directory: $TEST_DIR"
echo ""

# Create test file with intentional violations (for testing detection)
cat > "$TEST_DIR/test-violations.md" << 'EOF'
# Ember Enhancement Test Cases

## Test Case 1: Context-Aware Scoring
Try writing to hooks directory vs project directory
- Hooks: Should score ~5.0 (system interference)
- Project: Should score ~2.0-3.0 (utility development)

## Test Case 2: Inline Suggestions
Trigger violation and verify message includes:
- ✅ Reason
- ✅ Suggestion
- ✅ Risk explanation
- ✅ Safe alternative

## Test Case 3: Progressive Warnings
- Score 5.0-7.9: Warning but allow
- Score 8.0+: Block

## Test Case 4: Learning from Corrections
1. Trigger false positive
2. Call ember_learn_from_correction
3. Verify score adjustment
4. Check ember_get_learning_stats

## Test Case 5: Session Context
1. Set taskType='monitoring'
2. Same violation should score lower
EOF

echo "Created test cases: $TEST_DIR/test-violations.md"
echo ""

# Create tmux session for testing
SESSION_NAME="ember-enhanced-test"

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Killing existing test session..."
    tmux kill-session -t "$SESSION_NAME"
fi

echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME" -n test

# Setup test environment
tmux send-keys -t "$SESSION_NAME" "cd $TEST_DIR" C-m
tmux send-keys -t "$SESSION_NAME" "clear" C-m
tmux send-keys -t "$SESSION_NAME" "echo '🔥 Enhanced Ember Test Environment'" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Test directory: $TEST_DIR'" C-m
tmux send-keys -t "$SESSION_NAME" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME" "cat test-violations.md" C-m
tmux send-keys -t "$SESSION_NAME" "echo ''" C-m
tmux send-keys -t "$SESSION_NAME" "echo 'Ready for testing. You can now:'" C-m
tmux send-keys -t "$SESSION_NAME" "echo '1. Test Ember MCP tools manually'" C-m
tmux send-keys -t "$SESSION_NAME" "echo '2. Launch Claude Code in this directory'" C-m
tmux send-keys -t "$SESSION_NAME" "echo '3. Run test cases from test-violations.md'" C-m
tmux send-keys -t "$SESSION_NAME" "echo ''" C-m

echo ""
echo "✅ Test session created!"
echo ""
echo "To attach: tmux attach -t $SESSION_NAME"
echo "To kill:   tmux kill-session -t $SESSION_NAME"
echo ""
echo "Test cases are in: $TEST_DIR/test-violations.md"
echo ""
