---
name: quick-review
description: Fast comprehensive code review with quality assessment
---

Perform a quick but thorough code review of the project at {{args}}.

**Review Focus:**

1. **Security Analysis**
   - Bandit (Python) security scan
   - Semgrep multi-language security rules
   - Critical vulnerability detection
   - Dependency security audit

2. **Code Quality**
   - Cyclomatic complexity analysis
   - Linting (Pylint/ESLint/etc.)
   - Code style consistency
   - Maintainability metrics

3. **Test Coverage**
   - Coverage percentage (lines, branches, functions)
   - Missing test cases identification
   - Test quality assessment

4. **Iterative Refinement** (if enabled)
   - Automatic quality evaluation
   - Iterative improvement until quality threshold met
   - Chain-of-thought tracking across iterations

**Parameters:**
- Project path (required)
- Focus area: "all", "security", "quality", "testing" (optional)
- Quality threshold: 1-10 (default: 7)
- Iterative refinement: true/false (default: true)

**Example Usage:**
```
/quick-review /path/to/project
/quick-review /path/to/project --focus=security
/quick-review /path/to/project --quality=9 --iterative=true
```

**Output:**
- Overall quality rating (0-10)
- Approval status (Approved/Conditional/Changes Required)
- Critical findings summary
- Actionable recommendations
- Iteration history (if iterative mode enabled)

**Integration:**
- Uses `critic-agent-mcp` with evaluator-optimizer pattern
- Auto-generates `04-review.md` artifact via `artifact-generator-mcp`
- Tracks findings and improvements across sessions
