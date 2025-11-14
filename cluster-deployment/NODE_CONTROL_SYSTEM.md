# Node-to-Node Control System

**Status:** ✅ Deployed and Ready
**Date:** 2025-11-13
**Type:** Telnet-style Command Execution
**Protocol:** Text-based TCP socket communication

## Overview

This system enables **orchestrator-to-node remote command execution** without SSH authentication. Perfect for trusted local networks where you need quick node control.

### Architecture

```
Orchestrator (mac-studio)
    ↓ TCP socket (port 9999)
    ↓ sends: "exec <command>"
Node (macpro51)
    ↓ executes command
    ↓ returns JSON response
    ↓ {status, stdout, stderr, returncode}
Orchestrator (mac-studio)
    ↓ receives result
    ↓ continues workflow
```

## Quick Start - macpro51

### Option 1: One-Liner (Fastest)

On macpro51, run:
```bash
cd /mnt/ssdraid0/agentic-system/cluster-deployment && python3 ./node_command_listener.py macpro51 9999
```

Or if mounted at different path:
```bash
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment && python3 ./node_command_listener.py macpro51 9999
```

### Option 2: Bootstrap Script

```bash
cd /mnt/ssdraid0/agentic-system/cluster-deployment
./bootstrap_node_control.sh macpro51 9999
```

This will:
- Make scripts executable
- Check Python availability
- Verify port is available
- Create systemd service (optional)
- Start listener in foreground

### Option 3: Background Mode

```bash
cd /mnt/ssdraid0/agentic-system/cluster-deployment
nohup python3 ./node_command_listener.py macpro51 9999 > /tmp/node_listener.log 2>&1 &
echo $! > /tmp/node_listener.pid
```

Check it's running:
```bash
ps aux | grep node_command_listener
tail -f /tmp/node_listener.log
```

## Using from Orchestrator (mac-studio)

### Test Connection

```bash
cd /Volumes/SSDRAID0/agentic-system/cluster-deployment

# Get node status
python3 orchestrator_remote_exec.py 192.168.1.183 status

# Simple command
python3 orchestrator_remote_exec.py 192.168.1.183 "exec hostname"

# Check if node can see the build script
python3 orchestrator_remote_exec.py 192.168.1.183 "exec ls -l /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51/build_toon.sh"
```

### Execute TOON Build

```bash
# Start the build (will take 30-45 minutes)
python3 orchestrator_remote_exec.py 192.168.1.183 "exec cd /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51 && nohup ./build_toon.sh > /tmp/toon-build.log 2>&1 &"

# Monitor progress
python3 orchestrator_remote_exec.py 192.168.1.183 "exec tail -20 /tmp/toon-build.log"

# Check if build is complete
python3 orchestrator_remote_exec.py 192.168.1.183 "exec ls -l /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51/toon-results/BUILD_SUMMARY.md"
```

### Interactive Mode (telnet/netcat)

```bash
# Using telnet
telnet 192.168.1.183 9999

# Using netcat
nc 192.168.1.183 9999

# Then type commands:
status
exec hostname
exec pwd
quit
```

## Protocol Reference

### Commands

**status**
- Get node status, uptime, timestamp
- Returns JSON

**exec \<command\>**
- Execute shell command
- Returns JSON with stdout, stderr, returncode
- 5-minute timeout

**quit**
- Disconnect from node

### Response Format

All responses are JSON:

```json
{
  "status": "success|error|timeout",
  "returncode": 0,
  "stdout": "command output",
  "stderr": "error output",
  "command": "original command",
  "node": "macpro51",
  "timestamp": "2025-11-13T20:00:00"
}
```

## Security Considerations

⚠️ **This is for trusted local networks only!**

- No authentication (anyone who can reach the port can execute commands)
- No encryption (commands and responses in plain text)
- Execute with user permissions of the listener process

**For production:**
- Add authentication (API key, token)
- Use TLS/SSL encryption
- Implement command whitelist
- Rate limiting
- Audit logging

**Current use case:** Local trusted network for development cluster

## Troubleshooting

### Listener won't start

```bash
# Check if port is in use
lsof -i :9999
ss -tuln | grep 9999

# Kill existing process
kill $(lsof -t -i:9999)

# Try different port
python3 node_command_listener.py macpro51 9998
```

### Can't connect from orchestrator

```bash
# Check firewall
sudo firewall-cmd --list-all  # Fedora
sudo ufw status               # Ubuntu

# Open port
sudo firewall-cmd --permanent --add-port=9999/tcp
sudo firewall-cmd --reload

# Test connectivity
nc -zv 192.168.1.183 9999
telnet 192.168.1.183 9999
```

### Commands timeout

- Default timeout: 5 minutes (300 seconds)
- For long-running commands, use `nohup` and background:
  ```bash
  exec nohup ./long_script.sh > /tmp/out.log 2>&1 &
  ```
- Then poll for results:
  ```bash
  exec tail /tmp/out.log
  exec ls -l /path/to/results/
  ```

### Mount path issues

macpro51 might mount SSDRAID0 at different path:
- macOS: `/Volumes/SSDRAID0`
- Linux: `/mnt/ssdraid0` or `/media/SSDRAID0`

Check with:
```bash
exec mount | grep -i ssdraid
exec df -h | grep -i ssdraid
```

## Systemd Service (Auto-start on boot)

On macpro51:

```bash
# Create and enable service
sudo systemctl daemon-reload
sudo systemctl enable node-command-listener
sudo systemctl start node-command-listener

# Check status
sudo systemctl status node-command-listener

# View logs
sudo journalctl -u node-command-listener -f

# Stop/restart
sudo systemctl stop node-command-listener
sudo systemctl restart node-command-listener
```

## Integration with Agent Runtime

Future enhancement: Instead of manual orchestrator commands, integrate with agent-runtime-mcp:

```python
# Create task for remote execution
task = mcp__agent-runtime-mcp__create_task({
    "title": "Build TOON on macpro51",
    "description": "Remote execution via node control",
    "metadata": {
        "node": "macpro51",
        "command": "./build_toon.sh",
        "protocol": "node_control"
    }
})

# Task consumer automatically routes to node control system
# Executes on macpro51, monitors, reports results
```

## Files

```
cluster-deployment/
├── node_command_listener.py      - Daemon for nodes
├── orchestrator_remote_exec.py   - Client for orchestrator
├── bootstrap_node_control.sh     - Setup script
└── NODE_CONTROL_SYSTEM.md        - This file
```

## Logs

**Node (macpro51):**
- `/tmp/node_command_listener_macpro51.log`
- stdout if running in foreground

**Orchestrator (mac-studio):**
- stdout from orchestrator_remote_exec.py

## Next Steps

1. **Immediate:** Start listener on macpro51
   ```bash
   python3 node_command_listener.py macpro51 9999
   ```

2. **Test:** From orchestrator, send test command
   ```bash
   python3 orchestrator_remote_exec.py 192.168.1.183 status
   ```

3. **Execute:** Run TOON build
   ```bash
   python3 orchestrator_remote_exec.py 192.168.1.183 "exec cd /mnt/ssdraid0/agentic-system/databases/cluster/nodes/macpro51 && ./build_toon.sh"
   ```

4. **Monitor:** Check build progress
   ```bash
   python3 orchestrator_remote_exec.py 192.168.1.183 "exec tail -20 /tmp/toon-build.log"
   ```

5. **Results:** Read BUILD_SUMMARY.md when complete

---

**Status:** ✅ Ready for deployment
**Next:** Bootstrap on macpro51
**Protocol:** Simple, debuggable, effective
**Perfect for:** Trusted local development cluster
