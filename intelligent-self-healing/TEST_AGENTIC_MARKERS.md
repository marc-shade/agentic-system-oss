# Agentic Marker System - Test Suite

**Date:** 2025-11-04
**Purpose:** Verify the marker system works correctly for all scenarios

## Test Scenarios

The audit document identified three critical scenarios to test:

### Test 1: Agentic Modification (Should Pass)
**Scenario:** Agentic system makes intentional change with marker
**Expected:** Watchdog logs change but doesn't heal

### Test 2: User Modification (Should Pass)
**Scenario:** User manually changes config without marker
**Expected:** AI analyzes, recognizes as intentional, keeps it

### Test 3: Corruption (Should Heal)
**Scenario:** Config gets corrupted without marker
**Expected:** AI detects corruption, auto-heals

## Test 1: Agentic Modification with Marker

### Setup

```bash
# Save current maxTokens value
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

original_value = settings.get('maxTokens', 200000)
print(f"Original maxTokens: {original_value}")

# Save for restore
with open('/tmp/original_maxtokens.txt', 'w') as f:
    f.write(str(original_value))
EOF
```

### Execute Test

```bash
# Step 1: Create agentic marker
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Test agentic modification - deep learning optimization",
    change_type="agentic_optimization",
    confidence=0.95,
    session_id="test_scenario_1"
)
print("✅ Marker created")
EOF

# Step 2: Make the actual change
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

settings['maxTokens'] = 150000  # Test modification

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Modified maxTokens to 150000")
EOF

# Step 3: Run watchdog
echo ""
echo "=== Running Watchdog (Should NOT heal) ==="
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### Expected Output

```
============================================================
🤖 Intelligent StatusLine Watchdog (AI-Powered)
============================================================

🤖 Analyzing statusline change in settings.json...

✅ Agentic modification detected:
   Reason: Test agentic modification - deep learning optimization
   Confidence: 95.0%
   Time: 2025-11-04T...
   Type: agentic_optimization
   Action: Notification only (trusted change)

============================================================
📊 Watchdog Summary
============================================================
Configs checked: 2
Configs healed: 0
Confirmations needed: 0

✅ Watchdog complete
```

### Verify Result

```bash
# Check maxTokens value - should still be 150000 (not healed)
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

current_value = settings.get('maxTokens')
print(f"Current maxTokens: {current_value}")

if current_value == 150000:
    print("✅ TEST 1 PASSED: Value not healed (marker recognized)")
else:
    print(f"❌ TEST 1 FAILED: Value was {current_value}, expected 150000")
EOF

# Check notification log
echo ""
echo "=== Notification Log ==="
tail -1 ~/.claude/.config_notifications.jsonl | jq .
```

### Cleanup

```bash
# Restore original value
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Read original value
with open('/tmp/original_maxtokens.txt', 'r') as f:
    original_value = int(f.read().strip())

settings['maxTokens'] = original_value

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"✅ Restored maxTokens to {original_value}")
EOF

# Clean up marker file
rm -f ~/.claude/.config_modifications.jsonl
rm -f /tmp/original_maxtokens.txt
```

## Test 2: User Modification without Marker

### Setup

```bash
# Save current maxTokens
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

original_value = settings.get('maxTokens', 200000)
print(f"Original maxTokens: {original_value}")

with open('/tmp/original_maxtokens.txt', 'w') as f:
    f.write(str(original_value))
EOF
```

### Execute Test

```bash
# Step 1: User makes change (NO marker)
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

settings['maxTokens'] = 75000  # User modification

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ User modified maxTokens to 75000 (no marker)")
EOF

# Step 2: Run watchdog
echo ""
echo "=== Running Watchdog (Should analyze) ==="
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### Expected Output

```
============================================================
🤖 Intelligent StatusLine Watchdog (AI-Powered)
============================================================

🤖 Analyzing statusline change in settings.json...

📊 Analysis:
  Is Intentional: True
  Confidence: 85.0%
  Reasoning: User appears to have intentionally modified maxTokens setting. The change is structurally valid and within reasonable bounds.
  Recommendation: keep_new

✅ Change appears intentional, leaving as-is
   Current: ...

============================================================
📊 Watchdog Summary
============================================================
Configs checked: 2
Configs healed: 0
Confirmations needed: 0

✅ Watchdog complete
```

### Verify Result

```bash
# Check maxTokens - should still be 75000 (AI recognized as intentional)
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

current_value = settings.get('maxTokens')
print(f"Current maxTokens: {current_value}")

if current_value == 75000:
    print("✅ TEST 2 PASSED: AI recognized user modification as intentional")
else:
    print(f"❌ TEST 2 FAILED: Value was {current_value}, expected 75000")
EOF
```

### Cleanup

```bash
# Restore original
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

with open('/tmp/original_maxtokens.txt', 'r') as f:
    original_value = int(f.read().strip())

settings['maxTokens'] = original_value

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"✅ Restored maxTokens to {original_value}")
EOF

rm -f /tmp/original_maxtokens.txt
```

## Test 3: Corruption Detection and Healing

### Setup

```bash
# Backup current settings
cp ~/.claude/settings.json /tmp/settings.json.backup
echo "✅ Backup created"
```

### Execute Test

```bash
# Step 1: Corrupt the settings file (NO marker)
python3 << 'EOF'
# Write invalid JSON
with open('/Users/marc/.claude/settings.json', 'w') as f:
    f.write('{"statusLine": {"type": "corrupted", "command": "INVALID{{{')

print("✅ Created corrupted settings.json")
EOF

# Step 2: Run watchdog
echo ""
echo "=== Running Watchdog (Should heal corruption) ==="
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### Expected Output

```
============================================================
🤖 Intelligent StatusLine Watchdog (AI-Powered)
============================================================

🤖 Analyzing statusline change in settings.json...

📊 Analysis:
  Is Intentional: False
  Confidence: 95.0%
  Reasoning: Configuration appears corrupted - invalid JSON syntax detected. This is not an intentional change.
  Recommendation: restore_old
  ⚠️  Red Flags: invalid_json, corrupted_data

🔧 Restoring agentic statusline (confidence: 95.0%)
   Snapshot: /Users/marc/.claude/config_snapshots/settings.json.20251104_...

✅ Agentic statusline restored

============================================================
📊 Watchdog Summary
============================================================
Configs checked: 2
Configs healed: 1
Confirmations needed: 0

✅ Watchdog complete
```

### Verify Result

```bash
# Check statusLine - should be restored
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"

try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    statusline = settings.get('statusLine', {})
    command = statusline.get('command', '')

    if 'agentic-statusline.sh' in command:
        print("✅ TEST 3 PASSED: Corruption detected and healed")
        print(f"   StatusLine: {command}")
    else:
        print(f"❌ TEST 3 FAILED: StatusLine not restored properly")
        print(f"   Current: {command}")

except json.JSONDecodeError:
    print("❌ TEST 3 FAILED: Settings still corrupted (invalid JSON)")
EOF

# Check decision log
echo ""
echo "=== Decision Log ==="
tail -1 ~/.claude/intelligent_healing_decisions.jsonl | jq .
```

### Cleanup

```bash
# Restore backup (in case test failed)
if [ -f /tmp/settings.json.backup ]; then
    cp /tmp/settings.json.backup ~/.claude/settings.json
    echo "✅ Restored from backup"
    rm -f /tmp/settings.json.backup
fi
```

## Complete Test Suite Script

### Run All Tests

```bash
#!/bin/bash
# test_all_markers.sh
# Complete test suite for agentic marker system

set -e  # Exit on error

echo "=========================================="
echo "🧪 Agentic Marker System - Test Suite"
echo "=========================================="
echo ""

# Create test results directory
mkdir -p /tmp/marker_test_results
RESULTS_FILE="/tmp/marker_test_results/results_$(date +%Y%m%d_%H%M%S).txt"

# Helper function
log_test() {
    echo "$1" | tee -a "$RESULTS_FILE"
}

# Test 1: Agentic Modification
log_test "=== TEST 1: Agentic Modification with Marker ==="

# Save original
python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
original = settings.get('maxTokens', 200000)
with open('/tmp/test_original.txt', 'w') as f:
    f.write(str(original))
EOF

# Create marker
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent
agent = IntelligentConfigAgent()
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Test agentic modification",
    change_type="agentic_optimization",
    confidence=0.95
)
EOF

# Make change
python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
settings['maxTokens'] = 150000
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
EOF

# Run watchdog
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py > /tmp/test1_output.txt 2>&1

# Check result
TEST1_RESULT=$(python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
if settings.get('maxTokens') == 150000:
    print("PASS")
else:
    print("FAIL")
EOF
)

if [ "$TEST1_RESULT" = "PASS" ]; then
    log_test "✅ TEST 1 PASSED: Agentic modification not healed"
else
    log_test "❌ TEST 1 FAILED: Agentic modification was healed"
fi

# Restore
python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open('/tmp/test_original.txt', 'r') as f:
    original = int(f.read().strip())
with open(settings_file, 'r') as f:
    settings = json.load(f)
settings['maxTokens'] = original
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
EOF

# Clean up marker
rm -f ~/.claude/.config_modifications.jsonl

echo ""
log_test "=== TEST 2: User Modification (No Marker) ==="

# User makes change (no marker)
python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
settings['maxTokens'] = 75000
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
EOF

# Run watchdog
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py > /tmp/test2_output.txt 2>&1

# Check result
TEST2_RESULT=$(python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)
if settings.get('maxTokens') == 75000:
    print("PASS")
else:
    print("FAIL")
EOF
)

if [ "$TEST2_RESULT" = "PASS" ]; then
    log_test "✅ TEST 2 PASSED: User modification recognized as intentional"
else
    log_test "❌ TEST 2 FAILED: User modification was healed"
fi

# Restore
python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
with open('/tmp/test_original.txt', 'r') as f:
    original = int(f.read().strip())
with open(settings_file, 'r') as f:
    settings = json.load(f)
settings['maxTokens'] = original
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)
EOF

echo ""
log_test "=== TEST 3: Corruption Detection ==="

# Backup
cp ~/.claude/settings.json /tmp/settings.json.test_backup

# Corrupt file
echo '{"statusLine": {"type": "corrupted", "command": "INVALID{{{' > ~/.claude/settings.json

# Run watchdog
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py > /tmp/test3_output.txt 2>&1

# Check result
TEST3_RESULT=$(python3 << 'EOF'
import json
from pathlib import Path
settings_file = Path.home() / ".claude" / "settings.json"
try:
    with open(settings_file, 'r') as f:
        settings = json.load(f)
    statusline = settings.get('statusLine', {})
    if 'agentic-statusline.sh' in statusline.get('command', ''):
        print("PASS")
    else:
        print("FAIL")
except:
    print("FAIL")
EOF
)

if [ "$TEST3_RESULT" = "PASS" ]; then
    log_test "✅ TEST 3 PASSED: Corruption detected and healed"
else
    log_test "❌ TEST 3 FAILED: Corruption not properly healed"
    # Restore from backup
    cp /tmp/settings.json.test_backup ~/.claude/settings.json
fi

# Clean up
rm -f /tmp/test_original.txt
rm -f /tmp/settings.json.test_backup
rm -f /tmp/test*.txt

echo ""
log_test "=========================================="
log_test "📊 Test Suite Complete"
log_test "=========================================="
log_test "Results saved to: $RESULTS_FILE"
echo ""

# Show results summary
echo "Test Results:"
cat "$RESULTS_FILE" | grep -E "TEST [0-9]|Test Suite Complete"
```

### Make Script Executable and Run

```bash
# Save script
cat > /tmp/test_all_markers.sh << 'SCRIPT'
[paste complete script here]
SCRIPT

# Make executable
chmod +x /tmp/test_all_markers.sh

# Run tests
/tmp/test_all_markers.sh
```

## Success Criteria

All three tests must pass:

- ✅ **Test 1**: Agentic modification with marker → NOT healed
- ✅ **Test 2**: User modification without marker → NOT healed (AI recognizes intent)
- ✅ **Test 3**: Corruption without marker → HEALED (AI detects corruption)

## Troubleshooting

### Test 1 Fails (Agentic modification gets healed)

**Possible causes:**
- Marker not created properly
- Marker file path wrong
- Marker older than 24 hours
- Trust level requires analysis

**Debug:**
```bash
# Check marker file
cat ~/.claude/.config_modifications.jsonl | jq .

# Check timestamp
python3 << 'EOF'
from datetime import datetime
import json
from pathlib import Path
marker_file = Path.home() / ".claude" / ".config_modifications.jsonl"
with open(marker_file, 'r') as f:
    for line in f:
        marker = json.loads(line)
        print(f"Marker: {marker['key']}")
        print(f"Time: {marker['timestamp']}")
        print(f"Age: {(datetime.now() - datetime.fromisoformat(marker['timestamp'])).total_seconds() / 3600:.1f} hours")
EOF
```

### Test 2 Fails (User modification gets healed)

**Possible causes:**
- AI confidence too low
- Change looks suspicious to AI

**Debug:**
```bash
# Check decision log
tail -1 ~/.claude/intelligent_healing_decisions.jsonl | jq .
```

### Test 3 Fails (Corruption not healed)

**Possible causes:**
- Intelligent agent unavailable (fell back to rule-based)
- Snapshot system failed

**Debug:**
```bash
# Check if AI agent loaded
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
try:
    from intelligent_config_agent import IntelligentConfigAgent
    agent = IntelligentConfigAgent()
    print("✅ AI agent available")
except Exception as e:
    print(f"❌ AI agent failed: {e}")
EOF

# Check snapshots
ls -lht ~/.claude/config_snapshots/ | head -5
```

## Summary

This test suite verifies:

1. ✅ Marker system prevents healing of intentional agentic changes
2. ✅ AI analysis respects user modifications
3. ✅ Corruption detection and healing still works

**All three scenarios must pass** for production readiness.

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-04
