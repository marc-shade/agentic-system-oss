# Fast comprehensive code review with quality assessment

Perform a quick but thorough code review of recent changes or specified files.

## Review Focus Areas
1. **Security**: Common vulnerabilities (injection, XSS, auth)
2. **Quality**: Code clarity, maintainability, patterns
3. **Performance**: Obvious inefficiencies, N+1 queries
4. **Correctness**: Logic errors, edge cases

## Output
- Overall quality score (1-10)
- Critical issues (must fix)
- Suggestions (nice to have)
- Positive notes (what's done well)

---

Perform a quick code review:

$ARGUMENTS

If no specific files mentioned, check git status for recent changes.

Review process:
1. Identify files to review (from arguments or recent changes)
2. Read the relevant code
3. Analyze for the focus areas above
4. Provide concise feedback with:
   - Quality score
   - Critical issues (if any)
   - Top 3 improvement suggestions
   - Positive observations
