# Complete Slash Commands Reference

## Built-in Commands (33)

### Official Commands (20)
- `/add-dir` - Add directory to project files
- `/bug` - Report bugs with system logs
- `/clear` - Clear conversation history
- `/compact` - Compress conversation context
- `/config` - Show configuration settings
- `/cost` - Show usage and cost information
- `/cursor` - Jump to cursor position in editor
- `/doctor` - Run system diagnostics
- `/edit` - Quick file editing
- `/help` - Show help information
- `/init` - Initialize new Claude Code project
- `/login` - Login to Claude Code
- `/logout` - Logout from Claude Code
- `/mcp` - MCP server management
- `/memory` - Memory system operations
- `/model` - Switch AI models
- `/permissions` - Manage permissions
- `/pr_comments` - GitHub PR comment management
- `/review` - Code review operations
- `/status` - Show system status
- `/terminal-setup` - Terminal setup and configuration
- `/vim` - Vim integration
- `/agents` - Create and manage Claude Code sub-agents (NEW!)

### Extended Commands (12)
- `/exclude` - Exclude files from project
- `/exit` - Exit Claude Code
- `/files` - List all project files
- `/git` - Git operations and status
- `/paste` - Paste content into conversation
- `/project` - Switch between projects
- `/recentcommits` - Show recent git commits
- `/reset` - Reset conversation state
- `/search` - Search codebase
- `/shell` - Execute shell commands
- `/summarize` - Summarize files or directories

## Custom User Commands (42+)

### AI Agent Commands (8)
- `/user:ai-agents` - List available AI agents from 173+ library (renamed from /agents)
- `/user:ai-business` - Business strategy agents (15+ specialists)
- `/user:ai-technical` - Development agents (10+ specialists) 
- `/user:ai-marketing` - Marketing agents (10+ specialists)
- `/user:ai-creative` - Creative agents (10+ specialists)
- `/user:ai-fractional` - C-suite executives (7 specialists)
- `/user:ai-nonprofit` - Mission-driven agents (8+ specialists)
- `/user:ai-agency` - Agency operation agents (9+ specialists)
- `/user:ai-agent` - General AI agent access

### System & Orchestration (5)
- `/user:orchestrate` - Advanced orchestration (SPARC, swarms, containers)
- `/user:runtime` - Runtime management and monitoring
- `/user:monitor` - System monitoring and alerts
- `/user:agi` - AGI system controls
- `/user:memory` - Memory system operations

### Research & Intelligence (3)
- `/user:research-ai` - AI-powered research (ArXiv, PubMed)
- `/user:business-intelligence` - Lead generation, market research
- `/user:competitive-intel` - Competitive analysis

### Communication & Workflow (4)
- `/user:communication-hub` - Multi-platform messaging
- `/user:workflow-automation` - Process automation
- `/user:schedule-optimize` - AI scheduling optimization
- `/user:meeting-management` - Meeting orchestration

### Creative & Design (3)
- `/user:creative` - Creative project management
- `/user:workshop-tactics` - Pip Deck facilitation
- `/user:image-generation` - Multi-provider image generation

### Technical Tools (8)
- `/user:database-tools` - Database operations (SQLite, PostgreSQL, Vector)
- `/user:document-processing` - Advanced document extraction
- `/user:code-analysis` - Code review and analysis
- `/user:fabric-patterns` - AI content processing
- `/user:mcp-health` - MCP server health monitoring
- `/user:distributed-tasks` - Multi-node task distribution
- `/user:container-mgmt` - Container orchestration
- `/user:backup-recovery` - Data backup and recovery

### Business Operations (6)
- `/user:business` - General business operations
- `/user:financial-ops` - Financial management
- `/user:legal-ops` - Legal operations
- `/user:compliance` - Regulatory compliance
- `/user:risk-management` - Risk assessment
- `/user:strategic-planning` - Strategic planning

### Specialized Tools (5)
- `/user:voice` - Voice interface controls
- `/user:magic` - Advanced automation sequences
- `/user:asi-monitoring` - ASI/AGI progress tracking
- `/user:quality-assurance` - QA testing and validation
- `/user:security-privacy` - Security and privacy tools

## MCP Commands (67+ servers)
Commands are auto-discovered from connected MCP servers with `/mcp:` prefix.

### Key MCP Integrations
- `[MCP_WILDCARD_REMOVED]` - Advanced memory operations
- `[MCP_WILDCARD_REMOVED]` - SPARC system and swarms
- `[MCP_WILDCARD_REMOVED]` - Multi-node orchestration
- `[MCP_WILDCARD_REMOVED]` - Multimodal AI operations
- `[MCP_WILDCARD_REMOVED]` - Adaptive goal management
- `[MCP_WILDCARD_REMOVED]` - Self-improvement systems

## Usage Examples

### Basic Commands
```bash
/help                    # Show help
/files                   # List project files
/search "function name"  # Search codebase
/git status             # Git status
```

### AI Agent Access
```bash
/user:ai-business consultant     # Load business consultant
/user:ai-technical python       # Load Python developer
/user:ai-marketing campaign      # Load marketing specialist
```

### Advanced Orchestration
```bash
/user:orchestrate swarm          # Launch multi-agent swarm
/user:distributed-tasks parallel # Parallel task execution
/user:memory search "patterns"   # Search memory system
```

### Research & Analysis
```bash
/user:research-ai comprehensive "AI safety"
/user:business-intelligence leads "fintech SF"
/user:competitive-intel analyze "competitor"
```

## Configuration
All commands configured in `/Users/marc/.claude/settings.json`:
- Built-in commands: **enabled**
- Custom commands: **enabled** 
- MCP commands: **enabled** with auto-discovery
- Auto-completion: **enabled**
- Command chaining: **enabled**

## Command Discovery
- Built-in commands are always available
- Custom commands loaded from `/Users/marc/.claude/commands/`
- MCP commands auto-discovered from connected servers
- Use tab completion for faster access
- All commands support help via `/command help`