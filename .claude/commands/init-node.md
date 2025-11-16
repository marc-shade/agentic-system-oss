# Initialize Node

You are initializing a node in the agentic network cluster. This command sets up the node's environment, configuration, and verifies cluster connectivity.

## Steps to Execute

1. **Detect Current Node**
   - Run `hostname` to identify the current node
   - Map hostname to node identity:
     - `Marcs-Mac-Studio.local` → mac-studio (Orchestrator, Priority 1)
     - `Marcs-MacBook-Air.local` → macbook-air (Researcher, Priority 2)
     - `completeu-server.local` → completeu-server (Server, Priority 3)
     - `macmini.fios-router.home` → macmini (Worker, Priority 4)

2. **Determine Storage Path**
   - Mac Studio: `/Volumes/SSDRAID0/agentic-system/` (orchestrator/hot tier)
   - All other nodes: `/Volumes/FILES/agentic-system/` (distributed/cold tier)

3. **Create Directory Structure**
   ```bash
   mkdir -p $STORAGE_BASE/databases/cluster/nodes/$NODE_ID
   mkdir -p $STORAGE_BASE/databases/cluster
   mkdir -p $STORAGE_BASE/logs
   mkdir -p $STORAGE_BASE/mcp-servers
   mkdir -p $STORAGE_BASE/intelligent-agents
   mkdir -p $STORAGE_BASE/cluster-deployment
   mkdir -p $STORAGE_BASE/workflows
   mkdir -p $STORAGE_BASE/scripts
   mkdir -p ~/.claude
   ```

4. **Create Node Configuration**
   Create `~/.claude/node-config.json` with:
   ```json
   {
     "node_id": "$NODE_ID",
     "persona": "$PERSONA",
     "priority": $PRIORITY,
     "created_at": "$TIMESTAMP",
     "storage": {
       "base": "$STORAGE_BASE",
       "databases": "$STORAGE_BASE/databases",
       "logs": "$STORAGE_BASE/logs"
     },
     "memory": {
       "local_db": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/local_memory.db",
       "personal_db": "$STORAGE_BASE/databases/cluster/nodes/$NODE_ID/personal_memories.db",
       "shared_db": "$STORAGE_BASE/databases/cluster/shared_memories.db",
       "node_registry": "$STORAGE_BASE/databases/cluster/node_registry.db"
     }
   }
   ```

5. **Verify Python Dependencies**
   Check if required packages are installed:
   ```bash
   cd $STORAGE_BASE/intelligent-agents
   pip3 install -r requirements.txt --user
   ```

6. **Test Cluster Memory**
   Run the cluster memory test suite:
   ```bash
   cd $STORAGE_BASE/cluster-deployment
   python3 test_cluster_memory.py
   ```

7. **Check MCP Configuration**
   Verify `~/.claude.json` has the required MCP servers:
   - enhanced-memory-mcp
   - agent-runtime-mcp
   - ember-mcp

8. **Report Status**
   Display initialization results:
   - Node ID and persona
   - Storage paths
   - Cluster memory test results
   - MCP server status
   - Next steps (if any manual configuration needed)

## Expected Outcomes

- ✅ Node configuration file created
- ✅ Directory structure established
- ✅ Python dependencies installed
- ✅ Cluster memory tests passing
- ✅ MCP servers verified

## Troubleshooting

If cluster memory tests fail:
- Verify storage paths exist
- Check node configuration has complete 'memory' section
- Ensure shared database is accessible

If MCP servers are missing:
- Check `~/.claude.json` configuration
- Verify MCP server paths are correct
- Restart Claude Code after updating configuration
