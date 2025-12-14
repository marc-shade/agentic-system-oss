#!/bin/bash
# Claude Code Security Hooks Installation Script
# CRITICAL: Installs comprehensive security hook system for agentic enforcement

set -e  # Exit on any error

echo "🎛️ Claude Code Security Hooks Installer"
echo "========================================"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration paths
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SECURITY_DIR="$HOOKS_DIR/security"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

echo -e "${BLUE}📍 Installation paths:${NC}"
echo "   Claude directory: $CLAUDE_DIR"
echo "   Hooks directory: $HOOKS_DIR"
echo "   Settings file: $SETTINGS_FILE"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi
print_status "Python 3 available: $(python3 --version)"

# Check if Claude directory exists
if [ ! -d "$CLAUDE_DIR" ]; then
    print_error "Claude directory not found: $CLAUDE_DIR"
    print_error "Please initialize Claude Code first"
    exit 1
fi
print_status "Claude directory found"

# Verify hook files exist
echo ""
echo -e "${BLUE}📋 Verifying hook files...${NC}"

HOOK_FILES=(
    "security/delegation_enforcer_hook.py"
    "security/privacy_scanner_hook.py" 
    "security/resource_monitor_hook.py"
    "security/agent_capability_validator_hook.py"
    "hook_config_generator.py"
    "security/test_security_hooks.py"
)

MISSING_FILES=()
for file in "${HOOK_FILES[@]}"; do
    if [ -f "$HOOKS_DIR/$file" ]; then
        print_status "Found: $file"
    else
        print_error "Missing: $file"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    print_error "Missing ${#MISSING_FILES[@]} required hook files"
    exit 1
fi

# Make hook scripts executable
echo ""
echo -e "${BLUE}🔧 Setting permissions...${NC}"

for file in "${HOOK_FILES[@]}"; do
    if [[ $file == *.py ]]; then
        chmod +x "$HOOKS_DIR/$file"
        print_status "Made executable: $file"
    fi
done

# Test hook scripts can be executed
echo ""
echo -e "${BLUE}🧪 Testing hook functionality...${NC}"

# Test each hook individually with safe parameters
test_hook() {
    local hook_file="$1"
    local hook_name="$2"
    
    # Set safe test environment variables
    export CLAUDE_TOOL_NAME="Read"
    export CLAUDE_TOOL_INPUT="test_file.txt"
    export CLAUDE_CONTEXT="testing hook functionality"
    
    if python3 "$HOOKS_DIR/$hook_file" > /dev/null 2>&1; then
        print_status "$hook_name hook test passed"
        return 0
    else
        print_error "$hook_name hook test failed"
        return 1
    fi
}

HOOK_TEST_FAILURES=0

test_hook "security/delegation_enforcer_hook.py" "Delegation Enforcer" || ((HOOK_TEST_FAILURES++))
test_hook "security/privacy_scanner_hook.py" "Privacy Scanner" || ((HOOK_TEST_FAILURES++))  
test_hook "security/resource_monitor_hook.py" "Resource Monitor" || ((HOOK_TEST_FAILURES++))
test_hook "security/agent_capability_validator_hook.py" "Capability Validator" || ((HOOK_TEST_FAILURES++))

# Clear test environment variables
unset CLAUDE_TOOL_NAME CLAUDE_TOOL_INPUT CLAUDE_CONTEXT

if [ $HOOK_TEST_FAILURES -gt 0 ]; then
    print_error "$HOOK_TEST_FAILURES hook tests failed"
    echo "Check the hook files for errors before proceeding"
    exit 1
fi

# Backup existing settings
echo ""
echo -e "${BLUE}💾 Creating settings backup...${NC}"

if [ -f "$SETTINGS_FILE" ]; then
    BACKUP_FILE="$SETTINGS_FILE.backup_$(date +%Y%m%d_%H%M%S)"
    cp "$SETTINGS_FILE" "$BACKUP_FILE"
    print_status "Backup created: $(basename $BACKUP_FILE)"
else
    print_warning "No existing settings file found"
fi

# Generate and apply hook configuration
echo ""
echo -e "${BLUE}⚙️  Generating hook configuration...${NC}"

if python3 "$HOOKS_DIR/hook_config_generator.py"; then
    print_status "Hook configuration generated and applied"
else
    print_error "Failed to generate hook configuration"
    if [ -f "$BACKUP_FILE" ]; then
        print_warning "Restore backup with: cp $BACKUP_FILE $SETTINGS_FILE"
    fi
    exit 1
fi

# Run comprehensive test suite
echo ""
echo -e "${BLUE}🧪 Running comprehensive test suite...${NC}"

if python3 "$HOOKS_DIR/security/test_security_hooks.py"; then
    print_status "All security hooks tests passed"
else
    print_warning "Some tests failed - check test report for details"
    print_warning "Installation will continue, but review test output"
fi

# Verify final configuration
echo ""
echo -e "${BLUE}🔍 Verifying installation...${NC}"

# Check if settings.json contains hooks
if [ -f "$SETTINGS_FILE" ] && grep -q '"hooks"' "$SETTINGS_FILE"; then
    print_status "Hooks configuration found in settings"
else
    print_error "Hooks configuration not properly applied"
    exit 1
fi

# Count hook configurations
if command -v jq &> /dev/null; then
    HOOK_COUNT=$(jq -r '.hooks | to_entries | length' "$SETTINGS_FILE" 2>/dev/null || echo "unknown")
    print_status "Hook types configured: $HOOK_COUNT"
else
    print_warning "jq not available - cannot count hook configurations"
fi

# Create log directories
mkdir -p "$CLAUDE_DIR/logs/hooks"
print_status "Log directories created"

# Installation summary
echo ""
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo "========================================"
echo ""
echo -e "${BLUE}📊 Security Features Installed:${NC}"
echo "   ✅ Delegation enforcement for orchestrators"
echo "   ✅ Privacy-sensitive data detection and blocking"
echo "   ✅ Resource monitoring and limits"
echo "   ✅ Agent capability validation"
echo "   ✅ Comprehensive test suite"
echo ""
echo -e "${BLUE}📁 Files installed:${NC}"
for file in "${HOOK_FILES[@]}"; do
    echo "   • $HOOKS_DIR/$file"
done
echo "   • $SETTINGS_FILE (updated)"
if [ -f "$BACKUP_FILE" ]; then
    echo "   • $BACKUP_FILE (backup)"
fi
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo "   1. Restart Claude Code to activate hooks"
echo "   2. Monitor logs in: $CLAUDE_DIR/logs/hooks/"
echo "   3. Test with: claude 'help me write some code'"
echo "   4. Verify delegation enforcement works"
echo ""
echo -e "${YELLOW}⚠️  Important Notes:${NC}"
echo "   • Hooks will enforce strict agentic system rules"
echo "   • Orchestrators will be blocked from direct implementation"
echo "   • Privacy-sensitive data will be redirected to Local Privacy Agent"
echo "   • Resource limits will be enforced to prevent overload"
echo "   • Test thoroughly before using in production workflows"
echo ""
echo -e "${GREEN}🛡️  Security hooks system is now ACTIVE!${NC}"

# Voice confirmation
if [ -f "/Users/marc/.claude/siobhan_voice.py" ]; then
    python3 /Users/marc/.claude/siobhan_voice.py "Security hooks installation completed successfully. The agentic system is now fully protected." confident 2>/dev/null || true
fi

exit 0