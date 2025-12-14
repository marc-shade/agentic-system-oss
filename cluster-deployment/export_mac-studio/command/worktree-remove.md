# Remove Git Worktree

Remove an existing git worktree and clean up the associated directory.

## Task

When the user requests to remove a git worktree:

1. Identify the worktree name from user input
2. Verify the worktree exists
3. Remove the worktree using git worktree remove
4. Clean up any associated configuration files

## Safety Checks

Before removing:
- Verify there are no uncommitted changes
- Check if the worktree branch has been merged
- Warn the user if unmerged changes exist

## Usage Examples

```
/worktree-remove purple
```

This removes the worktree named "purple".

## Implementation

```bash
# Check for uncommitted changes
git -C ../project-{name} status --porcelain

# If clean, remove worktree
git worktree remove ../project-{name}

# Clean up any environment files
rm -rf ../project-{name}
```

Return confirmation of removal and any warnings about unmerged changes.
