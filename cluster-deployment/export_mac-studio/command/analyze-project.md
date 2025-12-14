---
name: analyze-project
description: Quick project analysis with intelligent planning for pre-implementation
---

Analyze the project at {{args}} and generate a complete pre-implementation analysis.

**Tasks:**

1. **Context Analysis** - Use `pre-implementation-analyzer-mcp` to analyze:
   - Project structure and language detection
   - Tech stack and dependencies
   - Architectural patterns
   - Key directories and their purposes
   - Risk identification

2. **Implementation Planning** - Generate:
   - Phased implementation plan
   - Agent assignments for each phase
   - Quality gates and success criteria
   - Timeline with milestones
   - Risk mitigation strategies

3. **Output Formatting** - Provide formatted output for:
   - **Executive**: Business impact, timeline, decision points
   - **Developer**: Technical details, implementation steps
   - **Default**: Balanced view with all key information

4. **Artifact Generation** - Auto-generate:
   - `00-context.md` - Project context analysis
   - `01-plan.md` - Implementation plan

**Example Usage:**
```
/analyze-project /path/to/project "Add user authentication with JWT"
```

**Output:**
- Complete analysis result
- Formatted summaries for different audiences
- Generated artifacts with tracking IDs
- Recommended next steps

**Integration:**
- Uses `pre-implementation-analyzer-mcp` MCP tool
- Integrates with `artifact-generator-mcp` for document creation
- Stores patterns in memory for cross-session learning
