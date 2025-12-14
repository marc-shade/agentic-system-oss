# MCP Service Management

Comprehensive MCP server monitoring, diagnostics, testing, and automated recovery using mcp-controller.

## Health Monitoring

**System-Wide Health Checks:**
- Check all 43+ MCP servers in ecosystem
- Verify API connections and credentials
- Identify healthy/degraded/down services
- Generate comprehensive health reports
- Provide specific recommendations for issues

**Usage:**
```
Check health of all MCP services
Show comprehensive MCP status report
Verify all MCP API connections
```

**MCP Tool:** `mcp__mcp-controller__check_all_mcp_services`

**Report Includes:**
- Summary: healthy/degraded/down counts
- Detailed status per service
- Recent errors for problematic services
- Fix recommendations

## Service Status

**Individual Service Status:**
- Current health state
- Connection verification
- API key validation
- Recent error logs
- Service history
- Uptime metrics

**Usage:**
```
Check status of [service_name] MCP
Get detailed status for specific service
Verify connection to MCP server
```

**MCP Tool:** `mcp__mcp-controller__check_mcp_service`

## Service Testing

**Comprehensive Service Tests:**
- Connection and startup verification
- Tool functionality testing
- API key validation
- Performance benchmarking
- Error handling verification
- Response time analysis

**Usage:**
```
Test [service_name] MCP functionality
Run comprehensive tests on specific server
Benchmark performance of MCP service
```

**Test Coverage:**
- ✅ Startup and initialization
- ✅ All exposed tools
- ✅ API authentication
- ✅ Error scenarios
- ✅ Performance under load

**Deliverables:**
- Detailed test results
- Performance metrics
- Issue diagnosis
- Fix recommendations

## Service Repair

**Automated Diagnosis & Fix:**

**Steps:**
1. Check service health status
2. Get restart information and history
3. Analyze service logs
4. Provide clear diagnosis
5. Generate fix recommendations
6. Offer watchdog creation if needed

**Usage:**
```
Fix [service_name] MCP service
Diagnose and repair MCP issues
Restart failed MCP server
```

**MCP Tools:**
- `mcp__mcp-controller__check_mcp_service`
- `mcp__mcp-controller__get_mcp_restart_info`
- `mcp__mcp-controller__get_mcp_service_history`
- `mcp__mcp-controller__create_mcp_watchdog_script`

**Fix Process:**
- Identify root cause
- Check restart history
- Review error patterns
- Apply appropriate fix
- Verify resolution

## Watchdog Automation

**Auto-Monitor & Restart:**
- Create watchdog scripts for any MCP service
- Configurable check intervals (default: 300s)
- Automatic restart on failure
- Detailed logging
- Background execution

**Usage:**
```
Create watchdog for [service_name]
Setup auto-restart for MCP service
Monitor [service_name] with 60-second checks
```

**MCP Tool:** `mcp__mcp-controller__create_mcp_watchdog_script`

**Watchdog Features:**
- Continuous health monitoring
- Automatic service restart on failure
- Detailed event logging
- Background daemon mode
- Easy start/stop controls

**Setup Instructions Provided:**
- Path to generated script
- Foreground/background execution commands
- How to stop watchdog
- How to check logs
- Optional auto-start in background

## Service History

**Track Service Behavior:**
- Service uptime/downtime events
- Restart history
- Error patterns over time
- Performance trends
- Configuration changes

**Usage:**
```
Show history for [service_name]
Get service restart log
Analyze uptime patterns
```

**MCP Tool:** `mcp__mcp-controller__get_mcp_service_history`

## Common Workflows

**Daily Health Check:**
```
1. Check all MCP services
2. Review any degraded services
3. Run tests on problematic services
4. Apply fixes as needed
5. Create watchdogs for unstable services
```

**New Service Validation:**
```
1. Test service functionality
2. Verify API connections
3. Benchmark performance
4. Setup watchdog
5. Monitor for 24 hours
```

**Troubleshooting:**
```
1. Check service status
2. Review error logs and history
3. Get restart information
4. Apply diagnosis recommendations
5. Create watchdog to prevent recurrence
```

## Integration with MCP Ecosystem

**Manages 43+ Servers Including:**
- Essential MCPs (enhanced-memory, voice-mode, agent-runtime)
- On-Demand MCPs via enhanced-router (23 servers)
- Development MCPs (github-mcp, shadcn-ui, checkov-mcp)
- AI/ML MCPs (ai-persona-lab, consciousness-agent-runtime)
- Visualization MCPs (imagemagick-local, genui-mcp)
- Security MCPs (kismet-mcp, surveillance-detection)
- Integration MCPs (telegram-mcp, kutiraai-mcp)

## Token Cost: ~100 tokens
Replaces 5 MCP management commands (42 lines, ~168 tokens) = **68 token savings**
