# Cluster Network Map
**Updated**: 2025-11-23 22:45

## Cluster Nodes (Verified Active)

### mac-studio (Orchestrator)
- **IP**: 192.168.1.16
- **MAC**: a4:fc:14:00:99:9c
- **Hostname**: Marc's Mac Studio
- **Role**: Orchestrator
- **Status**: ✅ **Online** (current node)
- **Services**:
  - Temporal Server (port 7233, UI 8233)
  - Temporal Workers (attempting to fix)
  - Orchestrator workflows

### macbook-air (Researcher)
- **IP**: 192.168.1.76
- **MAC**: 2a:44:f1:78:d4:33
- **Hostname**: Marcs-MacBook-Air
- **Role**: Researcher
- **Status**: ✅ **Online** (reachable)
- **Services**: Analysis and documentation workflows
- **Note**: Previously showed unreachable, now confirmed online

### macpro51 (Builder - Linux)
- **IP (Primary)**: 192.168.1.183
- **IP (Secondary)**: 192.168.1.87
- **MAC (Primary)**: e8:06:88:ca:da:a5
- **MAC (Secondary)**: 3a:cc:2e:d0:79:5a
- **Hostname**: macpro51
- **Role**: Builder (Linux - Fedora 43)
- **Status**: ✅ **Online** (both IPs respond)
- **Services**:
  - Builder API (port 9000) - ✅ Healthy
  - Redis (port 6379) - ✅ Running
  - Artifact Storage - ✅ Ready
  - Hardware Broadcast (port 8888)
- **Note**: Dual NICs or virtual interface, both operational
- **No Temporal**: Linux node - uses Builder API instead

### macbook-pro (Developer)
- **IP**: Unknown
- **MAC**: Unknown
- **Hostname**: Not found in network scan
- **Role**: Developer (if available)
- **Status**: ❓ **Not Found**
- **Possible Explanations**:
  - Offline/powered off
  - Different hostname
  - Not yet configured as cluster node
  - Could be one of the unidentified Mac devices

## Other Mac Devices on Network

### Potential macbook-pro Candidates
1. **192.168.1.36** - macmini (14:98:77:3d:54:56)
   - NetBIOS: MACMINI
   - Could be repurposed as cluster node

2. **192.168.1.168** - ftp-mini (a8:60:b6:20:64:f3)
   - Apple, Inc.
   - Running FTP service
   - Could be storage node

3. **192.168.1.233** - Mac-Mini-File-Server (68:5b:35:8f:49:f9)
   - Apple, Inc.
   - Likely dedicated file server
   - Not cluster node

4. **192.168.1.186** - completeu-server (1c:1d:d3:eb:a8:08)
   - NetBIOS: MAC-EBA808
   - Different project

## Network Topology

```
Router: 192.168.1.1 (Verizon)
├─ mac-studio (192.168.1.16) [Orchestrator] ✅
├─ macbook-air (192.168.1.76) [Researcher] ✅
├─ macpro51 (192.168.1.183/.87) [Builder] ✅
├─ macbook-pro (???) [Developer] ❓
└─ Other devices (printers, servers, etc.)
```

## Service Discovery

### Avahi/mDNS Services
- `macpro51.local` → 192.168.1.183 (primary)
- `_agentic-builder._tcp` → macpro51 (port 9000)
- Mac devices discoverable via .local domain

### Port Assignments by Node

**mac-studio (Orchestrator)**:
- 7233: Temporal gRPC
- 8233: Temporal UI
- 9500: Grafana
- 9700: Prometheus
- 9900: Loki

**macpro51 (Builder)**:
- 9000: Builder API
- 8888: Hardware Broadcast
- 6379: Redis
- 6333: Qdrant REST
- 11434: Ollama

**macbook-air (Researcher)**:
- TBD: Research workflows
- TBD: Analysis services

## Cluster Health Summary

| Node | IP | Status | Services | Temporal |
|------|-------|--------|----------|----------|
| mac-studio | 192.168.1.16 | ✅ Online | Orchestrator | ✅ Server running |
| macbook-air | 192.168.1.76 | ✅ Online | Research | ❓ Not checked |
| macpro51 | 192.168.1.183 | ✅ Online | Builder API | N/A (Linux) |
| macbook-pro | Unknown | ❓ Unknown | Developer | ❓ Unknown |

## Next Steps

1. **Identify macbook-pro**:
   - Check if any Mac Mini is actually the developer node
   - Search for SSH access to unidentified devices
   - Review cluster deployment logs for last known IP

2. **Configure macbook-air**:
   - SSH into 192.168.1.76
   - Verify node-config.json
   - Check if Temporal is installed
   - Start researcher workflows

3. **Update DNS/mDNS**:
   - Ensure all nodes advertise via Avahi
   - Create /etc/hosts entries for static mapping
   - Configure proper hostnames

4. **Test Cross-Node Communication**:
   - Verify all nodes can reach each other
   - Test Builder API from all nodes
   - Validate Temporal connectivity

## Firewall Configuration

**macpro51 (Linux) Required Ports**:
```bash
firewall-cmd --permanent --add-port=9000/tcp  # Builder API
firewall-cmd --permanent --add-port=8888/tcp  # Hardware Broadcast
firewall-cmd --permanent --add-port=6379/tcp  # Redis (internal)
firewall-cmd --reload
```

**macOS Nodes**:
- Firewall: Allow incoming for Temporal (7233)
- Allow cluster communication (all nodes)
