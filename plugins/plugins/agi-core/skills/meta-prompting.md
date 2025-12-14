---
name: Meta-Prompting
description: Skill for handling complex tasks through structured analysis and planning
---

# Meta-Prompting Skill

This skill activates for complex tasks that require structured analysis before implementation.

## When to Activate

Activate meta-prompting when the task involves:
- **Multi-file modifications**: Changes spanning multiple files
- **System refactoring**: Structural changes to codebase
- **Database migrations**: Schema or data changes
- **Complex integrations**: Connecting multiple systems
- **Architecture changes**: Fundamental design modifications
- **Ambiguous requirements**: Tasks needing clarification

## Skip for

- Simple single-file edits
- Clear, unambiguous tasks
- Quick fixes with obvious solutions
- Documentation updates

## Meta-Prompting Workflow

### Phase 1: Clarification
Ask targeted questions to understand:
1. **Goal**: What exactly should be achieved?
2. **Context**: What's the current state?
3. **Constraints**: What limitations exist?
4. **Success criteria**: How do we know it's done?

### Phase 2: Analysis
Before any implementation:
1. **Explore**: Read relevant code and documentation
2. **Map**: Identify all affected components
3. **Risks**: Note potential issues and edge cases
4. **Alternatives**: Consider different approaches

### Phase 3: Planning
Create structured plan:
1. **Steps**: Break into ordered, testable steps
2. **Dependencies**: Note what depends on what
3. **Verification**: How to verify each step
4. **Rollback**: How to undo if needed

### Phase 4: Confirmation
Present plan to user:
- Summary of understanding
- Proposed approach
- Key decisions to confirm
- Request approval before proceeding

### Phase 5: Execution
For each step:
1. State what you're about to do
2. Execute the change
3. Verify it worked
4. Document outcome

### Phase 6: Review
After completion:
1. Summarize what was done
2. Note any issues encountered
3. Suggest follow-up actions
4. Document lessons learned

## Example Application

**User request**: "Refactor the authentication module to use JWT"

**Meta-prompting response**:

```
This is a significant change. Let me apply the meta-prompting workflow:

## Clarification Questions
1. Should I preserve backward compatibility with existing sessions?
2. What token expiration policy do you want?
3. Should refresh tokens be implemented?
4. Where should the JWT secret be stored?

## After Clarification - Analysis
[Read auth module, identify all usage points, map dependencies]

## Plan
1. Add JWT library dependency
2. Create token generation utility
3. Update login endpoint
4. Update middleware to verify JWT
5. Update tests
6. Migration script for existing sessions

Shall I proceed with this plan?
```

## Best Practices

1. **Don't assume**: Ask when uncertain
2. **Be thorough**: Check all affected areas
3. **Be incremental**: Small, verifiable steps
4. **Be transparent**: Share reasoning
5. **Be reversible**: Plan for rollback

## Integration with Agents

- Use `@architect` for design decisions during planning
- Use `@code-reviewer` to verify changes after execution
- Use `@deep-thinker` for complex algorithm changes

---

*Meta-prompting ensures complex tasks are handled systematically and safely.*
