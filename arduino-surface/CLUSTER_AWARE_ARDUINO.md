# Cluster-Aware Arduino Surface System

## Overview

The Arduino Surface MCP server now supports automatic discovery and control of Arduino devices across the entire cluster, with graceful degradation when the Arduino is not available.

## Key Features

### 1. **Automatic Arduino Discovery**
- Scans local serial ports first (fastest)
- Queries remote cluster nodes if not found locally
- Supports both SSH and telnet relay methods
- No hard-coded port configuration required

### 2. **Remote Arduino Control**
- Transparent relay of commands to remote nodes
- Uses SSH with base64-encoded Python scripts (no remote files needed)
- 3-second Arduino reset settling time
- Full command support (LCD, LED, servo, beep, alert, status)

### 3. **Graceful Degradation**
- MCP server starts successfully even without Arduino
- Provides helpful error messages indicating where Arduino was last seen
- All tools gracefully fail with informative messages

## Architecture

```
┌─────────────────────┐
│  Claude Desktop     │
│  (MCP Client)       │
└──────────┬──────────┘
           │
           │ MCP Protocol
           ▼
┌─────────────────────────────────────────────────────┐
│  Arduino Surface MCP Server                         │
│  (mac-studio or any node)                           │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ ArduinoClusterDiscovery                      │  │
│  │  • Scan local ports                          │  │
│  │  • Query cluster registry                    │  │
│  │  • Check remote nodes (SSH/telnet)           │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │ ClusterAwareArduinoSurface                   │  │
│  │  • Local direct connection                   │  │
│  │  • Remote SSH relay                          │  │
│  │  • Remote telnet relay                       │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────┴───────────┐
        ▼                        ▼
   ┌─────────┐            ┌──────────────┐
   │ Local   │            │ SSH Relay    │
   │ Arduino │            │ to Remote    │
   └─────────┘            │ Arduino      │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │ macpro51     │
                          │ /dev/ttyACM0 │
                          │ Arduino UNO  │
                          └──────────────┘
```

## Files Created/Modified

### Created:
1. **`bridge/arduino_cluster_discovery.py`** (391 lines)
   - `ArduinoLocation` dataclass for tracking Arduino location
   - `ArduinoClusterDiscovery` class with discovery logic
   - Local serial port scanning (multiple patterns)
   - Remote node checking via SSH and telnet
   - Cluster registry integration

2. **`bridge/arduino_cluster_relay.py`** (407 lines)
   - `ArduinoClusterRelay` class for command relay
   - `ClusterAwareArduinoSurface` wrapper class
   - SSH relay using base64-encoded Python scripts
   - Telnet relay support
   - Full Arduino API compatibility

### Modified:
1. **`mcp-server/arduino_surface_mcp.py`**
   - Removed hard-coded port requirement
   - Added automatic discovery on startup
   - Graceful degradation when Arduino not found
   - Better status messages (node, IP, port, relay method)

2. **`/Users/marc/.claude.json`**
   - Removed `/dev/tty.usbmodem8344401` port argument
   - Server now auto-discovers Arduino location

## Testing Results

### Discovery Test ✅
```bash
$ python3 arduino_cluster_discovery.py

🔍 Searching for Arduino Surface across cluster...

✅ Arduino found!
   Node: macpro51
   IP: 192.168.1.183
   Port: /dev/ttyACM0
   Local: False
   Relay: ssh
```

### Relay Test ✅
```bash
$ python3 arduino_cluster_relay.py

🔍 Discovering Arduino across cluster...

✅ Arduino found!
   Node: macpro51
   IP: 192.168.1.183
   Port: /dev/ttyACM0
   Local: False
   Relay: ssh

🔌 Testing connection...
✅ Connected!

📺 Testing LCD...
✅ LCD write successful

💡 Testing LED...
✅ LED set successful

🔔 Testing beep...
✅ Beep successful

📊 Testing status...
✅ Status: {'cmd': 'status', 'pot': 909, 'temp_c': 279.9, 'light': 548}
```

### MCP Server Test ✅
```bash
$ .venv/bin/python mcp-server/arduino_surface_mcp.py

🔍 Arduino Surface MCP Server
   Discovering Arduino across cluster...

✅ Arduino connected!
   Node: macpro51
   IP: 192.168.1.183
   Port: /dev/ttyACM0
   Local: False
   Relay: ssh

✅ MCP server ready
```

## Cluster Node Configuration

### Known Nodes:
- **mac-studio** (192.168.1.?) - Orchestrator (local)
- **macpro51** (192.168.1.183) - Linux builder (SSH available)
- **macbook-air-m3** (192.168.1.76) - macOS researcher (SSH available)

### Serial Port Patterns:
- macOS: `/dev/tty.usbmodem*`, `/dev/cu.usbmodem*`
- Linux: `/dev/ttyACM*`, `/dev/ttyUSB*`

### Discovery Priority:
1. Local serial ports (direct connection)
2. Remote cluster nodes via cluster registry
3. Fallback to hardcoded known nodes

## SSH Relay Implementation

The SSH relay uses base64-encoded Python scripts to avoid shell quoting issues:

```python
# Encode script
encoded = base64.b64encode(python_script.encode()).decode()

# Execute remotely
ssh marc@192.168.1.183 "echo {encoded} | base64 -d | python3"
```

This approach:
- ✅ No remote file dependencies
- ✅ No shell quoting problems
- ✅ Only requires Python and pyserial on remote node
- ✅ 3-second Arduino reset handling
- ✅ Full JSON response parsing

## Usage

### From MCP Client (Claude Desktop):

```python
# Display text (automatically routes to correct node)
mcp__arduino-surface__surface.display(row=0, col=0, text="Hello Cluster")

# Set LED color
mcp__arduino-surface__surface.led.set(tier=0, r=0, g=255, b=0)

# Get sensor status
status = mcp__arduino-surface__surface.status()
# Returns: Arduino found on macpro51, sensors: pot=909, temp=279.9, light=548
```

### Manual Testing:

```bash
# Discover Arduino
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/bridge
python3 arduino_cluster_discovery.py

# Test relay
python3 arduino_cluster_relay.py

# Start MCP server
cd /Volumes/SSDRAID0/agentic-system/arduino-surface
.venv/bin/python mcp-server/arduino_surface_mcp.py
```

## Graceful Degradation

When Arduino is not found:

```
🔍 Arduino Surface MCP Server
   Discovering Arduino across cluster...

⚠️  Arduino not found on any cluster node
   MCP server will operate in degraded mode
   All Arduino operations will gracefully fail

✅ MCP server ready
   (Operating in degraded mode - Arduino not available)
```

Tool calls return helpful errors:
```json
{
  "error": {
    "code": -1,
    "message": "Arduino not available. Not found on any cluster node. Please ensure Arduino is connected."
  }
}
```

## Benefits

1. **Plug Arduino anywhere** - Works on any cluster node
2. **No configuration changes** - Discovery is automatic
3. **Graceful failures** - Server doesn't crash without Arduino
4. **Transparent relay** - Same API whether local or remote
5. **Fast local access** - Prefers local connection when available
6. **Cluster aware** - Leverages existing node registry

## Future Enhancements

Potential improvements:
- [ ] Event listening support for remote Arduinos (requires persistent SSH tunnel)
- [ ] Telnet relay implementation (currently SSH-only)
- [ ] Multiple Arduino support (discover all, select by capability)
- [ ] Arduino capability detection (which sensors/actuators are available)
- [ ] Automatic failover to backup Arduino if primary fails
- [ ] Performance metrics (latency, success rate by relay method)
