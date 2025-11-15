# Quick Start - New Node Onboarding

**For humans setting up a new node to join the agentic cluster**

## Prerequisites

You need:
- Python 3.10+ ([Download](https://www.python.org/))
- Git ([Download](https://git-scm.com/))
- GitHub account with Personal Access Token ([Create](https://github.com/settings/tokens/new))

## Three Ways to Get Started

### Option 1: Over the Network (Recommended for Local Clusters)

If you have an existing node on your network:

```bash
# Get the bootstrap script from existing node
scp user@existing-node:/path/to/agentic-system/bootstrap-local.sh ~/

# Run it
bash ~/bootstrap-local.sh
```

The script will guide you through:
1. Choosing how to get the code (GitHub, local node, or zip)
2. Running environmental awareness
3. Intelligent integration

### Option 2: Direct from GitHub

If you have internet and GitHub access:

```bash
# Clone the repository
git clone https://github.com/marc-shade/agentic-system.git
cd agentic-system

# STOP! Read this first (shows up first alphabetically)
cat 00-START-HERE.md
```

### Option 3: Via USB/Transfer

If you need to transfer the entire repository:

```bash
# On source node: Create archive
cd /path/to/agentic-system
tar czf ~/agentic-system.tar.gz .

# Transfer via USB or network
# On new node: Extract
tar xzf agentic-system.tar.gz
cd agentic-system

# Read the start guide
cat 00-START-HERE.md
```

## The Onboarding Flow

Once you have the code, here's what happens:

### 1. Environmental Awareness (REQUIRED)

**For Claude Code agents**: When you first see this repository, **READ `00-START-HERE.md` FIRST**. It will guide you through creating and running the environmental awareness script.

**For humans**: Help your Claude Code agent set this up:

```bash
# Create the awareness script
mkdir -p ~/.claude/hooks
cp scripts/environmental-awareness.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/environmental-awareness.py

# Install required Python packages
pip3 install psutil

# Run environmental awareness
python3 ~/.claude/hooks/environmental-awareness.py
```

This creates `~/.claude/environmental-awareness.json` which catalogs:
- What services you're already running
- What databases you have
- What's configured
- What needs to be installed

### 2. Review What You Have

```bash
# View the awareness data
cat ~/.claude/environmental-awareness.json | jq .

# Or without jq
cat ~/.claude/environmental-awareness.json
```

This tells you what's already on your system that will be preserved.

### 3. Run Intelligent Onboarding

Now the onboarding script knows what you have and won't break it:

```bash
./onboard-with-claude.sh
```

The script will:
- ✅ Check you have environmental awareness (required)
- ✅ Create backups of all existing configurations
- ✅ Show you what services you already have running
- ✅ Only install missing components
- ✅ Merge MCP configurations (not replace)
- ✅ Guide authentication setup
- ✅ Configure cluster daemon
- ✅ Verify everything works

### 4. Verify Success

```bash
./verify-onboarding.sh
```

This checks:
- All your original services still running
- All your original data intact
- New components integrated successfully
- No conflicts

## What Gets Installed

Based on what you already have, the system may install:

**Core Infrastructure**:
- Ollama (local LLM server) - if not running
- Qdrant (vector database) - if not running
- Temporal (workflow engine) - if not running
- AutoKitteh (event orchestration) - if not running

**Claude Code Configuration** (merged with existing):
- Intelligent statusline (real-time system status)
- MCP servers:
  - enhanced-memory-mcp (4-tier memory)
  - agent-runtime-mcp (persistent tasks)
  - ember-mcp (quality enforcement)
- Hooks, skills, and agents

**Monitoring** (optional):
- Prometheus, Loki, Grafana

## Safety Features

The onboarding is designed to be **non-destructive**:

1. **Environmental Awareness First** - Must understand what exists before acting
2. **Automatic Backups** - All configs backed up with timestamps
3. **Intelligent Detection** - Skips services already running
4. **Configuration Merging** - Adds to existing MCP servers, doesn't replace
5. **Database Preservation** - Never modifies existing databases
6. **Rollback Available** - All backups in `~/.claude/backups/`

## Common Scenarios

### Fresh System (Nothing Installed)

The onboarding will install everything you need.

### Existing Services Running

The onboarding will:
- Detect what's running
- Skip those installations
- Configure new components to work with existing ones
- Preserve all your data

### Existing Claude Configuration

The onboarding will:
- Backup your current `~/.claude.json`
- Merge new MCP servers with yours
- Keep all your existing servers
- Add cluster capabilities

## Troubleshooting

### Environmental Awareness Missing

```bash
Error: ⚠️  ENVIRONMENTAL AWARENESS REQUIRED
```

Solution: Run the environmental awareness script first (see step 1 above)

### Python Package Missing

```bash
Error: ModuleNotFoundError: No module named 'psutil'
```

Solution:
```bash
pip3 install psutil
```

### Permission Denied

```bash
Error: Permission denied accessing ~/.claude/
```

Solution: Make sure you own the .claude directory:
```bash
sudo chown -R $USER:$USER ~/.claude
```

## What Happens Next

After onboarding completes:

1. **Join the Cluster** - Your node can communicate with other nodes via GitHub
2. **Share Memory** - Access cluster-wide shared memory
3. **Run Autonomous Workflows** - Temporal and AutoKitteh are configured
4. **Use MCP** - All AI platforms can access cluster capabilities

## Need Help?

- Read `00-START-HERE.md` for detailed explanation
- Read `INTELLIGENT-INTEGRATION-GUIDE.md` for technical details
- Read `SYSTEM_REQUIREMENTS.md` for complete component list
- Check the verification output for specific issues

## Emergency Rollback

If something goes wrong:

```bash
# Find your backup
ls -la ~/.claude/backups/

# Restore from most recent backup
LATEST=$(ls -td ~/.claude/backups/* | head -1)
echo "Restoring from: $LATEST"

cp "$LATEST/claude.json.backup" ~/.claude.json
cp "$LATEST/mcp.json.backup" ~/.mcp.json
cp -r "$LATEST/hooks.backup/"* ~/.claude/hooks/

# Restart Claude Code
pkill -f claude-code
```

Your original configuration will be restored.

---

**Remember**: The key principle is **self-awareness before action**. The system must understand what you have before it can intelligently integrate with it.
