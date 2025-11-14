#!/bin/bash
# Deploy MCP servers configuration to macpro51 Builder node

BUILDER_IP="192.168.1.183"
BUILDER_USER="marc"
BUILDER_AGENTIC="/mnt/agentic-system"

echo "🚀 Deploying MCP Configuration to Builder Node (macpro51)"

# Create MCP configuration for Builder node
cat > /tmp/builder_claude.json << 'EOF'
{
  "mcpServers": {
    "enhanced-memory": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/server.py"],
      "env": {
        "MEMORY_DB_PATH": "/mnt/agentic-system/agent-memory/enhanced_memories/memory.db",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_COLLECTION": "enhanced_memory_v2",
        "NODE_ID": "macpro51"
      },
      "disabled": false
    },
    "agent-runtime-mcp": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/agent-runtime-mcp/server.py"],
      "env": {
        "DATABASE_PATH": "/mnt/agentic-system/databases/agent_runtime.db",
        "NODE_ID": "macpro51"
      },
      "disabled": false
    },
    "safla-enhanced": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/SAFLA/server.py"],
      "env": {
        "SAFLA_DB_PATH": "/mnt/agentic-system/databases/safla_memory.db",
        "NODE_ID": "macpro51"
      },
      "disabled": false
    },
    "ember-mcp": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/ember-mcp/server.py"],
      "env": {
        "NODE_ID": "macpro51",
        "PRODUCTION_ONLY": "true"
      },
      "disabled": false
    },
    "video-transcript-mcp": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/video-transcript-mcp/server.py"],
      "disabled": false
    },
    "research-paper-mcp": {
      "command": "python3",
      "args": ["/mnt/agentic-system/mcp-servers/research-paper-mcp/server.py"],
      "disabled": false
    }
  }
}
EOF

# Copy MCP configuration to Builder
echo "📦 Copying MCP configuration..."
scp /tmp/builder_claude.json ${BUILDER_USER}@${BUILDER_IP}:~/.claude.json

# Create node-specific configuration
cat > /tmp/builder_node_config.json << 'EOF'
{
  "node_id": "macpro51",
  "node_role": "builder",
  "orchestrator_ip": "192.168.1.161",
  "capabilities": [
    "build",
    "compile",
    "test",
    "package"
  ],
  "storage": {
    "agentic_base": "/mnt/agentic-system",
    "databases": "/mnt/agentic-system/databases",
    "logs": "/mnt/agentic-system/logs"
  }
}
EOF

ssh ${BUILDER_USER}@${BUILDER_IP} "mkdir -p ~/.claude"
scp /tmp/builder_node_config.json ${BUILDER_USER}@${BUILDER_IP}:~/.claude/node-config.json

echo "✅ MCP Configuration deployed to Builder node"
echo "📊 Verify with: ssh marc@192.168.1.183 'cat ~/.claude.json'"
