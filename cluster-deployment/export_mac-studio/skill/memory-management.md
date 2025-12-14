# Memory Management

Complete knowledge graph and entity storage operations using enhanced-memory MCP.

## Core Operations

**Save Memories**
- Create entities with observations (user preferences, project context, code patterns, decisions, lessons learned)
- Build knowledge relationships and link concepts
- Update existing memories with new information
- Structure: `{name, entityType, observations: [key insights, context, when/where applies]}`

**Search & Retrieve**
- Semantic search across all memories
- Filter by entity type, namespace, or time period
- Find related entities and concepts
- Query patterns and historical decisions

**Agent-Specific Memories**
- Create agent namespaces for specialized learning
- Track agent evolution and performance
- Store task patterns and optimization hints
- Manage agent types: architect, coder, researcher, tester, coordinator, analyst
- Namespace format: `agent_[type]_[id]`

**Memory Analysis**
- Analyze memory usage and patterns
- Identify knowledge gaps and duplications
- Track memory evolution over time
- Generate memory statistics and insights

**Share Knowledge**
- Share insights across agents
- Build team knowledge base
- Cross-reference related concepts
- Enable collaborative learning

**Load & Restore**
- Load project-specific context
- Restore previous decisions and rationale
- Access historical patterns and preferences
- Quick context recovery for resuming work

## Entity Types
- `user_preference`: User's style and preferences
- `project_context`: Project-specific information
- `code_pattern`: Implementation patterns that worked
- `decision`: Important decisions with rationale
- `lesson_learned`: Success and failure insights
- `agent_memory`: Personal agent learning
- `task_pattern`: Successful task approaches
- `error_pattern`: Mistakes to avoid
- `shared_knowledge`: Team-wide insights

## Memory Categories
- Personal: User preferences, style, habits
- Project: Context, decisions, architecture
- Learning: Patterns, lessons, optimizations
- Agent: Namespaced agent-specific memories
- Team: Shared knowledge and collaboration

## MCP Integration
All operations use enhanced-memory MCP tools:
- `create_entities`: New memories
- `search_nodes`: Find memories
- `create_relations`: Link concepts
- `update_entity`: Modify existing
- `get_memory_status`: System stats
- `memory_commit`: Version snapshots
- `memory_branch`: Experimental paths

## Example Operations
```
Save architecture decision with rationale
Search for similar project patterns
Create namespace for new coder agent
Load project context for resuming work
Analyze memory usage and growth
Share key insight with team
Update user preferences based on session
```

## Token Cost: ~150 tokens
Replaces 7 slash commands (240 lines, ~720 tokens) = **570 token savings**
