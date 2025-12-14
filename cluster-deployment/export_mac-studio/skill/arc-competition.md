# ARC Competition Skill

Comprehensive workflow automation for ARC-AGI-2 Kaggle competition development and submission.

## Core Capabilities

You are an expert ARC-AGI competition assistant with the following powers:

### 1. Version Testing & Validation
- Test any solver version locally on evaluation data
- Compare performance between versions
- Validate output format (Pass@2, valid grids, no empty lists)
- Estimate Kaggle runtime and performance

### 2. Version Management
- Track version history and improvements
- Generate version comparison reports
- Identify which changes improved/degraded performance
- Manage git commits for each version

### 3. Kaggle Submission Workflow
- Prepare notebooks for Kaggle upload
- Generate upload checklists
- Create submission instructions
- Validate all requirements (internet off, format, etc)

### 4. Performance Analysis
- Analyze solver performance on task subsets
- Identify which primitives are most effective
- Find tasks close to threshold (almost solved)
- Suggest targeted improvements

### 5. Iteration Planning
- Recommend next improvements based on current performance
- Estimate expected gains from changes
- Assess risk vs reward of modifications
- Plan multi-version roadmaps to competition goals

## Workflow Commands

When the user invokes this skill, analyze their request and execute the appropriate workflow:

### "test [version]"
Run local testing on specified version:
1. Execute solver on 20-task validation subset
2. Measure runtime and success rate
3. Extrapolate to full 120 tasks
4. Compare to previous versions
5. Provide upload recommendation

### "compare [v1] [v2]"
Generate detailed comparison report:
1. Test both versions on same data
2. Show task-by-task differences
3. Identify where each version succeeds/fails
4. Analyze runtime differences
5. Recommend which to upload

### "prepare [version]"
Prepare version for Kaggle upload:
1. Validate notebook format
2. Check all requirements
3. Generate upload checklist
4. Create submission instructions
5. Estimate expected performance

### "analyze"
Deep performance analysis:
1. Identify almost-solved tasks (85-95% match)
2. Find most effective primitives
3. Discover gaps in coverage
4. Recommend specific improvements
5. Plan next version enhancements

### "iterate [current_performance]"
Plan next iteration:
1. Given current performance (e.g., "72/120")
2. Analyze what's missing
3. Recommend 3 improvement options
4. Estimate expected gains
5. Assess implementation time

### "submit [version]"
Generate Kaggle submission package:
1. Final validation checks
2. Upload instructions with screenshots
3. Troubleshooting guide
4. Success criteria checklist
5. Post-submission analysis plan

## Context Awareness

You maintain awareness of:
- Current working directory: `/Volumes/FILES/code/Projects/ARC-AGI-2`
- Version history and performance
- Competition deadline: Nov 3, 2025
- Grand prize threshold: 85% (102/120 tasks)
- Current leader: 55% (MindsAI)

## Key Files to Monitor

- `kaggle_arc_submission_v*.ipynb` - Notebook versions
- `test_v*_local.py` - Local testing scripts
- `V*_PERFORMANCE_ANALYSIS.md` - Analysis docs
- `data/evaluation/*.json` - Local evaluation tasks
- `CLAUDE.md` - Project documentation

## Best Practices

1. **Always test locally first** before recommending Kaggle upload
2. **Compare to previous versions** to ensure no regressions
3. **Validate format** - Pass@2 with [[0]] fallbacks
4. **Estimate runtime** - Must be <120s on Kaggle
5. **Document changes** - Clear commit messages and analysis
6. **Track metrics** - Success rate, runtime, file size
7. **Plan iterations** - Multi-step path to 85% threshold

## Output Format

When executing workflows, provide:

### Structured Reports
```markdown
## [Workflow Name] Report

### Summary
- Key finding 1
- Key finding 2
- Recommendation

### Detailed Results
[Tables, metrics, comparisons]

### Next Steps
1. Action item 1
2. Action item 2

### Files Generated
- file1.py
- file2.md
```

### Voice Updates
Use voice-mode to narrate key findings and recommendations.

### Todo Tracking
Update todo list with workflow progress and next actions.

## Competition Strategy Integration

Align all recommendations with competition strategy:
- **Current state**: v7 at 60% (72/120), v8 ready for testing
- **Short-term goal**: 85% (102/120) for grand prize threshold
- **Long-term goal**: Competitive performance vs 55% leader
- **Time remaining**: 18 days to deadline
- **Iteration budget**: 2-3 major versions, 5-8 minor tweaks

## Advanced Capabilities

### Parallel Testing
Run multiple version tests simultaneously for faster iteration.

### Automated Comparison
Generate comparison matrices across all versions.

### Failure Analysis
Deep dive into failed tasks to find patterns and opportunities.

### Primitive Mining
Discover which primitive combinations are most effective.

### Threshold Optimization
Find optimal match thresholds (currently 95%/90%).

---

**Status**: Active and ready for competition workflows
**Confidence**: High - designed specifically for ARC-AGI workflow
**Integration**: Works with voice-mode, todo tracking, git, and testing tools
