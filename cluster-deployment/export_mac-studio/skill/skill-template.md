# [Skill Name]

[CONCISE DESCRIPTION - Max 50 tokens - This is ALWAYS loaded]
[One sentence describing what this skill does and when to use it]

## When to Use This Skill

[Clear trigger conditions - these should be obvious context patterns]

**Trigger Patterns**:
- Specific keywords in user request
- File paths being accessed
- MCP servers needed
- Agent types required
- Domain expertise needed

**Examples**:
- "Create a blog post about..." → business/blog-generator
- "Review this API code..." → development/code-review
- "Research market trends for..." → research/market-analysis

## Core Capabilities

[Brief bullet list - what does this skill provide?]

- Capability 1: [specific skill or process]
- Capability 2: [specific tool or technique]
- Capability 3: [specific output or deliverable]

## Workflow

[DETAILED INSTRUCTIONS - Lazy-loaded only when skill is invoked]

### Phase 1: [Phase Name] (Time estimate)
1. **Step 1**: [Specific action]
   - Sub-action or detail
   - Expected outcome

2. **Step 2**: [Specific action]
   - Sub-action or detail
   - Expected outcome

### Phase 2: [Phase Name] (Time estimate)
1. **Step 1**: [Specific action]
2. **Step 2**: [Specific action]

### Phase 3: [Phase Name] (Time estimate)
1. **Step 1**: [Specific action]
2. **Step 2**: [Specific action]

## Integration Points

### MCP Server Integration
```python
# Which MCP servers does this skill use?
required_servers = [
    "enhanced-memory",    # For: [specific purpose]
    "voice-mode",         # For: [specific purpose]
    "sequential-thinking" # For: [specific purpose]
]

optional_servers = [
    "image-gen",          # For: [specific purpose]
    "youtube-transcript"  # For: [specific purpose]
]
```

### Agent Orchestration
```python
# Which agents does this skill spawn?
agents = {
    "primary": "agent-type-name",  # Main agent for this skill
    "supporting": [
        "agent-type-1",  # For: [specific task]
        "agent-type-2"   # For: [specific task]
    ]
}
```

### Hook Integration
```python
# How does this skill integrate with hooks?
hook_triggers = {
    "pre-tool-use": [
        "Detect skill invocation context",
        "Load required MCP servers",
        "Initialize voice narration"
    ],
    "post-tool-use": [
        "Store skill learnings in memory",
        "Capture execution patterns",
        "Update skill effectiveness metrics"
    ]
}
```

### Memory Integration
```python
# How does this skill use enhanced-memory?
memory_usage = {
    "store": [
        "Skill execution outcomes",
        "Successful patterns",
        "User preferences",
        "Domain-specific learnings"
    ],
    "retrieve": [
        "Similar past executions",
        "Best practices",
        "Common pitfalls",
        "User customizations"
    ]
}
```

## Voice Milestones

[Key progress points to announce via voice-mode]

```python
# Start
mcp__voice-mode__converse(
    "Starting [skill name]. I'll [brief description of what's happening]...",
    wait_for_response=False
)

# Progress checkpoints
mcp__voice-mode__converse(
    "Completed [phase 1]. Now moving to [phase 2]...",
    wait_for_response=False
)

# Completion
mcp__voice-mode__converse(
    "Skill execution complete. Generated [deliverables]. Ready for your review.",
    wait_for_response=False
)
```

## Input Parameters

[What inputs does this skill accept?]

**Required**:
- `parameter_name` (type): Description of what this parameter controls

**Optional**:
- `parameter_name` (type, default: value): Description and when to use
- `--flag-name`: Description of flag behavior

**Examples**:
```bash
# Example 1: Basic usage
skill skill-name "simple input"

# Example 2: With optional parameters
skill skill-name "input" --flag --param=value

# Example 3: Complex usage
skill skill-name "detailed input" --all-options --verbose
```

## Output Standards

[Expected deliverables and quality requirements]

### Primary Deliverables
1. **Deliverable 1**: [Description and file format]
   - Location: `/path/to/output/`
   - Format: [file format]
   - Quality Requirements: [specific standards]

2. **Deliverable 2**: [Description and file format]
   - Location: `/path/to/output/`
   - Format: [file format]
   - Quality Requirements: [specific standards]

### Quality Checklist
- [ ] Production-ready (no POCs or demos)
- [ ] Real data (no mock/placeholder content)
- [ ] Proper error handling
- [ ] Complete documentation
- [ ] Tested and validated
- [ ] Voice milestones completed
- [ ] Memory integration working

### Success Criteria
- Metric 1: [measurable outcome]
- Metric 2: [measurable outcome]
- Metric 3: [measurable outcome]

## Examples

### Example 1: [Simple Use Case]

**Context**: [When would you use this example?]

**Input**:
```bash
skill skill-name "example input"
```

**Process**:
1. Skill detects [context]
2. Activates [MCP servers]
3. Spawns [agents]
4. Executes [workflow]

**Output**:
```
[Expected output with realistic content]
```

**Files Generated**:
- `/path/to/file1.ext` - [Description]
- `/path/to/file2.ext` - [Description]

### Example 2: [Complex Use Case]

**Context**: [When would you use this example?]

**Input**:
```bash
skill skill-name "complex input" --options --flags
```

**Process**:
1. [Detailed step]
2. [Detailed step]
3. [Detailed step]

**Output**:
```
[Expected output with realistic content]
```

**Voice Narration**:
```
"Starting complex workflow. This will take approximately [time]..."
"Phase 1 complete. Discovered [findings]..."
"All phases complete. Generated [deliverables]."
```

### Example 3: [Edge Case]

**Context**: [Unusual but important scenario]

**Input**:
```bash
skill skill-name "edge case input"
```

**Handling**:
- Detects [unusual condition]
- Applies [special logic]
- Generates [appropriate output]

**Output**:
```
[Expected output showing edge case handling]
```

## Error Handling

### Common Errors

**Error 1: [Error type]**
- **Cause**: [What triggers this error]
- **Detection**: [How to identify it]
- **Resolution**: [How to fix it]
- **Prevention**: [How to avoid it]

**Error 2: [Error type]**
- **Cause**: [What triggers this error]
- **Detection**: [How to identify it]
- **Resolution**: [How to fix it]
- **Prevention**: [How to avoid it]

### Recovery Strategies

1. **Graceful Degradation**: If [condition], fall back to [alternative]
2. **Retry Logic**: Retry [operation] up to [n] times with [backoff strategy]
3. **User Notification**: Alert user via voice-mode about [issue] and [action taken]

## Performance Optimization

### Token Efficiency
- **Baseline Cost**: ~50 tokens (short description)
- **Full Load Cost**: ~[number] tokens (complete skill)
- **Average Execution**: ~[number] tokens per invocation
- **Optimization**: [Specific techniques used]

### Execution Speed
- **Target**: Complete in <[time]
- **Actual**: Average [time] per execution
- **Bottlenecks**: [Known slow points]
- **Optimizations**: [Performance improvements]

### Context Management
- **Context Load**: [Amount] at skill start
- **Peak Usage**: [Amount] during execution
- **Context Release**: [Amount] freed after completion
- **Caching**: [What gets cached and for how long]

## Best Practices

### Do's
1. **Always**: [Best practice with explanation]
2. **Always**: [Best practice with explanation]
3. **Always**: [Best practice with explanation]

### Don'ts
1. **Never**: [Anti-pattern with explanation]
2. **Never**: [Anti-pattern with explanation]
3. **Never**: [Anti-pattern with explanation]

### Recommendations
1. **Prefer**: [Recommended approach] over [alternative] because [reason]
2. **Consider**: [Option] when [condition] for [benefit]
3. **Optimize**: [Area] by [technique] to achieve [outcome]

## Skill Learning and Evolution

### Learning Capture
```python
# After successful execution, store learnings
mcp__enhanced-memory-mcp__create_entities([{
    "name": f"skill-{skill_name}-learning-{timestamp}",
    "entityType": "skill_learning",
    "observations": [
        "execution_pattern: [pattern discovered]",
        "success_factor: [what made it work]",
        "user_preference: [customization used]",
        "improvement_opportunity: [potential enhancement]"
    ]
}])
```

### Evolution Strategy
1. **Monitor**: Track skill usage and success rates
2. **Analyze**: Identify patterns in successful executions
3. **Adapt**: Update workflow based on learnings
4. **Test**: Validate improvements with real scenarios
5. **Deploy**: Roll out enhanced version

### Version History
- **v1.0**: Initial implementation - [date]
- **v1.1**: [Enhancement] - [date]
- **v1.2**: [Enhancement] - [date]

## Troubleshooting

### Issue 1: [Common problem]
**Symptoms**: [How to recognize this issue]
**Diagnosis**: [How to confirm it's this issue]
**Solution**: [Step-by-step fix]
**Prevention**: [How to avoid in future]

### Issue 2: [Common problem]
**Symptoms**: [How to recognize this issue]
**Diagnosis**: [How to confirm it's this issue]
**Solution**: [Step-by-step fix]
**Prevention**: [How to avoid in future]

## Related Skills

### Complementary Skills
- `category/skill-name`: [When to use together]
- `category/skill-name`: [When to use together]

### Alternative Skills
- `category/skill-name`: [When to use instead]
- `category/skill-name`: [When to use instead]

### Prerequisite Skills
- `category/skill-name`: [Required before this skill]
- `category/skill-name`: [Recommended before this skill]

## Resources

### Documentation
- [Link to relevant docs]
- [Link to API reference]
- [Link to examples]

### Tools
- [Required tool name]: [Purpose]
- [Optional tool name]: [Purpose]

### External References
- [Useful article/guide]
- [Framework documentation]
- [Best practices guide]

## Metadata

```yaml
skill_name: skill-name
category: category-name
version: 1.0.0
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
author: Marc Shade / 2 Acre Studios
status: production|beta|experimental
complexity: simple|moderate|complex
estimated_time: [time range]
token_cost: [baseline|full]
dependencies:
  mcp_servers: [list]
  agents: [list]
  hooks: [list]
tags:
  - tag1
  - tag2
  - tag3
```

---

**Note**: This template provides a comprehensive structure. Not all sections are required for every skill. Use judgment to include what's relevant for your specific skill. The short description and "When to Use This Skill" sections are mandatory for skill detection.
