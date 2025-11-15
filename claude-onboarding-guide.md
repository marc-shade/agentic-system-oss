# Claude Code Onboarding Orchestration Guide

**Purpose**: This guide is for Claude Code instances to orchestrate human onboarding.

## Overview

When a new node is being set up, Claude Code will run on that node and **autonomously install and configure** the complete agentic system. Claude Code has the ability to:

- ✅ Execute scripts and check system status
- ✅ **Install components automatically** (Ollama, Temporal, AutoKitteh, Qdrant, etc.)
- ✅ Communicate with the human via voice or text
- ✅ Wait for human input only when absolutely necessary (OAuth, API keys)
- ✅ Verify that steps were completed correctly
- ✅ Configure MCP across all AI platforms

## Installation Philosophy

**Autonomous First**: Claude Code should install and configure everything it can automatically. The human should only be involved for tasks that require their credentials or manual interaction:

- ✅ **Claude Code Can Install**: Ollama, Temporal, AutoKitteh, Qdrant, monitoring stack, Python dependencies, Gemini CLI (if npm exists)
- ⚠️ **Requires Human**: GitHub tokens, OpenAI API keys, Google Cloud auth, Claude Code itself (must already be installed)

## Complete Requirements

For a full list of all components and their installation methods, see: **SYSTEM_REQUIREMENTS.md**

## Onboarding Flow

### 1. Initial Check (Automated)

```bash
cd /path/to/agentic-system
./check-platforms.sh
```

This outputs a JSON file that Claude Code can parse to see what's installed.

**Claude Code should say** (via voice-mode MCP):
"I've checked your system. You have [X] of 4 required platforms installed. [List missing platforms]. Would you like me to guide you through installing the missing ones?"

### 2. Autonomous Component Installation

Claude Code can now install components automatically! Use the master installer:

#### Installation Flow

**Say** (via voice-mode): "I found [X] of 4 AI platforms installed. Now I'm going to install the core infrastructure components automatically. This may take a few minutes."

**Execute**:
```bash
cd install-scripts
./install-all.sh standard
```

This automatically installs:
- **Ollama** (if missing) - Local LLM server
- **Qdrant** - Vector database for semantic memory
- **Temporal** - Workflow engine for autonomous operations
- **AutoKitteh** - Event-driven workflow orchestration

**Say**: "Installation complete! I've set up Ollama for local AI, Qdrant for memory, Temporal for workflows, and AutoKitteh for events."

#### Manual Platform Installation (if needed)

Some platforms require manual installation by the human:

##### Claude Code Missing
**Say**: "Claude Code must be installed manually. Please visit https://code.claude.com and install it first, then rerun the onboarding."

**STOP**: Claude Code cannot orchestrate its own installation

##### OpenAI Codex Missing (Optional)
**Say**: "OpenAI Codex is optional but recommended. You can install it later by following OpenAI's guide, or we can skip it for now."

**Wait for**: User decision to install or skip

##### Gemini CLI Missing (Can Auto-Install)
**Check**: `command -v npm`

**If npm exists**:
```bash
npm install -g @google/generative-ai-cli
```
**Say**: "I've installed Gemini CLI for you."

**If npm missing**:
**Say**: "Gemini CLI requires Node.js. You can install Node.js from https://nodejs.org and I'll install Gemini CLI afterward, or we can skip it for now."

### 3. Authentication Setup (Human-in-the-Loop)

Once all platforms are installed, Claude Code guides authentication:

#### GitHub Authentication
**Say**: "Now I need your GitHub Personal Access Token to enable cluster communication. Please create one at https://github.com/settings/tokens/new with these scopes: repo, read:org, and workflow. Paste it when ready."

**Wait for**: Human provides token

**Execute**: Store in environment

**Verify**: Test GitHub API access

#### Ollama Setup
**Say**: "Ollama is running locally and doesn't require authentication. I've configured it to use the default port 11434."

**Execute**: Configure `OLLAMA_HOST` environment variable

#### OpenAI Codex Authentication
**Say**: "For OpenAI Codex, you have two options: OAuth with your ChatGPT account (recommended) or an API key. Which would you prefer?"

**If OAuth**:
**Say**: "I'll open a browser window for you to authenticate with ChatGPT. Please complete the OAuth flow and let me know when done."
**Execute**: `codex login`
**Wait for**: Human confirmation
**Verify**: `codex login status`

**If API Key**:
**Say**: "Please get your OpenAI API key from https://platform.openai.com/api-keys and paste it when ready."
**Wait for**: Human provides key
**Execute**: `codex login --api-key <key>`
**Verify**: `codex login status`

#### Gemini CLI Authentication
**Say**: "For Gemini, I can set up Google Cloud authentication or use a direct API key. If you're using Google Cloud, choose ADC. Otherwise, choose API key. Which would you like?"

**If ADC**:
**Say**: "I'll initiate the Google Cloud authentication flow. A browser window will open - please sign in and authorize access."
**Execute**: `gcloud auth application-default login`
**Wait for**: Human completes auth
**Ask**: "What's your Google Cloud Project ID?"
**Wait for**: Human provides project ID
**Execute**: Set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`

**If API Key**:
**Say**: "Please get your Gemini API key from https://aistudio.google.com/app/apikey and paste it when ready."
**Wait for**: Human provides key
**Execute**: Store in `~/.gemini/.env` and environment

### 4. MCP Configuration (Automated by Claude Code)

**Say**: "Perfect! All platforms are authenticated. Now I'll configure MCP servers across all platforms. This will take a moment..."

**Execute**:
```bash
./configure-all-mcps.sh
```

This script (to be created) will:
- Create `~/.claude.json` with MCP server configurations
- Create `~/.codex/mcp.json` (if Codex supports MCP)
- Create Gemini MCP configuration
- Configure cluster daemon as MCP server

**Verify**: Check that all config files were created

**Say**: "MCP servers configured! All your AI platforms can now access shared memory and cluster communication."

### 5. Cluster Daemon Setup (Automated by Claude Code)

**Say**: "Now I'll set up the cluster daemon so you can communicate with other nodes."

**Execute**:
```bash
cd cluster-deployment
./start_daemon.sh
```

**Verify**: Check daemon is running

**Say**: "The cluster daemon is now running. Your node ID is [NODE_ID]."

### 6. Final Verification (Automated)

**Say**: "Let me run a final verification to make sure everything is working..."

**Execute**:
```bash
./verify-onboarding.sh
```

**Checks**:
- All platforms installed: ✓
- All platforms authenticated: ✓
- MCP servers configured: ✓
- Cluster daemon running: ✓
- Can reach GitHub: ✓

**Say**: "Congratulations! Your node is fully onboarded and ready to join the cluster. Here's what you can do next..."

## Claude Code Communication Patterns

### Using Voice Mode
```python
mcp__voice-mode__converse(
    "I've checked your system. You have 2 of 4 required platforms...",
    wait_for_response=True
)
```

### Waiting for Confirmation
```python
response = mcp__voice-mode__converse(
    "Please install Ollama and let me know when you're done.",
    wait_for_response=True
)

# Parse response for confirmation
if "done" in response.lower() or "installed" in response.lower():
    # Proceed to verification
```

### Executing Commands
```bash
# Claude Code can run commands directly
result = Bash("ollama --version")
# Check result.stdout for version
```

### Updating Progress
```python
# Update onboarding status file
status = {
    "status": "in_progress",
    "steps": {
        "platform_check": "completed",
        "ollama_setup": "in_progress",
        # ...
    }
}

Write(
    file_path="~/.agentic-system-onboarding-status.json",
    content=json.dumps(status, indent=2)
)
```

## Error Handling

If something fails, Claude Code should:

1. **Identify the issue**
   ```bash
   # Run diagnostic commands
   ./diagnose-issue.sh
   ```

2. **Explain to human**
   ```python
   mcp__voice-mode__converse(
       "I encountered an issue with [X]. The error message is: [ERROR]. "
       "This usually means [EXPLANATION]. Would you like me to try again "
       "or would you prefer to fix this manually?"
   )
   ```

3. **Offer solutions**
   - Automatic retry
   - Manual intervention
   - Skip this platform and continue

4. **Document the issue**
   - Save error to log file
   - Update status JSON with error details

## Success Criteria

Onboarding is complete when:
- ✅ All 4 platforms installed
- ✅ All platforms authenticated
- ✅ MCP configured in Claude Code (minimum requirement)
- ✅ MCP optionally configured in Codex and Gemini
- ✅ Cluster daemon running
- ✅ Node can reach GitHub
- ✅ Test health check succeeds

Claude Code should congratulate the human and provide next steps!
