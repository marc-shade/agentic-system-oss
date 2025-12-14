# Mac-Studio Quick Reconnection Guide

After macOS reinstall, run these steps to reconnect mac-studio to the agentic cluster.

## Prerequisites

- Fresh macOS installed on system drive
- External drives mounted:
  - **SSDRAID0** at `/Volumes/SSDRAID0/` (hot tier - active agentic system)
  - **FILES** at `/Volumes/FILES/` (cold tier - backups only)

## Quick Reconnection (5 minutes)

### Step 1: Install Essential Tools

```bash
# Install Xcode command line tools
xcode-select --install

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH (Apple Silicon)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Install packages
brew install python3 node git sqlite jq
```

### Step 2: Restore SSH Keys (from another node or backup)

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Option A: Copy from surviving node
scp marc@macpro51.local:~/.ssh/id_ed25519* ~/.ssh/
scp marc@macpro51.local:~/.ssh/authorized_keys ~/.ssh/

# Option B: Copy from backup on FILES drive
cp /Volumes/FILES/backups/ssh/* ~/.ssh/

chmod 600 ~/.ssh/id_ed25519
```

### Step 3: Setup Claude Code Config

```bash
mkdir -p ~/.claude

# Restore from external drive
cp /Volumes/SSDRAID0/agentic-system/.claude.json.backup ~/.claude.json 2>/dev/null || \
cat > ~/.claude.json << 'EOF'
{
  "version": "1.0",
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp/server.py"],
      "env": {},
      "disabled": false
    },
    "agent-runtime": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/agent-runtime-mcp/server.py"],
      "env": {},
      "disabled": false
    },
    "voice-mode": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/voice-mode/server.py"],
      "env": {},
      "disabled": false
    }
  }
}
EOF

# Copy local settings if they exist
cp /Volumes/SSDRAID0/agentic-system/.claude/settings.local.json ~/.claude/ 2>/dev/null || true
```

### Step 4: Setup Python Environment

```bash
cd /Volumes/SSDRAID0/agentic-system

# Create/activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r mcp-servers/enhanced-memory-mcp/requirements.txt
pip install -r mcp-servers/agent-runtime-mcp/requirements.txt
```

### Step 5: Verify External Drives

```bash
# Check SSDRAID0 (hot tier)
ls -la /Volumes/SSDRAID0/agentic-system/
# Should see: CLAUDE.md, cluster-deployment/, mcp-servers/, etc.

# Check databases
ls -la /Volumes/SSDRAID0/agentic-system/databases/
# Should see: cluster/, mcp/, temporal/, qdrant/
```

### Step 6: Test Cluster Connectivity

```bash
cd /Volumes/SSDRAID0/agentic-system

# Check other nodes are reachable
ping -c 1 macpro51.local
ping -c 1 completeu-server.local
ping -c 1 Marcs-MacBook-Air.local

# Run health check
python3 system_health_check.py
```

### Step 7: Rejoin Cluster

```bash
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment

# Check cluster status
python3 resilient_cluster.py --check-health

# Reclaim orchestrator role (if desired)
python3 resilient_cluster.py --status
```

## Optional: Restore Services

### Temporal (if used)

```bash
cd /Volumes/SSDRAID0/agentic-system/scripts
./start-temporal.sh
```

### Monitoring Stack

```bash
cd /Volumes/SSDRAID0/agentic-system/monitoring
./start-all.sh
```

### Arduino Surface (if connected)

```bash
# Find Arduino port
ls /dev/tty.usbmodem*

# Test connection
cd /Volumes/SSDRAID0/agentic-system/arduino-surface
python3 test_hardware.py /dev/tty.usbmodem<PORT>
```

## Verification Checklist

- [ ] Homebrew installed
- [ ] Python 3 working
- [ ] SSH keys restored
- [ ] ~/.claude.json configured
- [ ] External drives mounted (SSDRAID0, FILES)
- [ ] Virtual environment activated
- [ ] MCP servers can start
- [ ] Can ping other cluster nodes
- [ ] system_health_check.py passes

## Troubleshooting

### External drives not mounting

```bash
# List all disks
diskutil list

# Mount manually
diskutil mount /dev/diskXsY
```

### Python packages missing

```bash
cd /Volumes/SSDRAID0/agentic-system
source .venv/bin/activate
pip install -r requirements.txt  # If exists
pip install anthropic mcp sqlite-utils qdrant-client
```

### MCP server won't start

```bash
# Test manually
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp
python3 server.py --help

# Check for missing deps
pip install -r requirements.txt
```

### Cluster nodes not visible

```bash
# Check mDNS
dns-sd -B _ssh._tcp local.

# Check firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

## Recovery Time

| Step | Time |
|------|------|
| Install tools | ~3 min |
| Restore SSH | ~1 min |
| Setup Claude | ~1 min |
| Python env | ~2 min |
| Verify | ~1 min |
| **Total** | **~8 min** |

## Notes

- All agentic system data is on SSDRAID0 - the system drive only needs base OS + tools
- No startup scripts needed initially - start services manually as needed
- The cluster can operate without mac-studio (other nodes take over orchestration)
- Once mac-studio is back, it can reclaim orchestrator role via leader election
