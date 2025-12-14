# List Git Worktrees

Display all active git worktrees with their status and configuration.

## Task

When the user requests to list git worktrees:

1. Use git worktree list to get all worktrees
2. For each worktree, show:
   - Name/branch
   - Path
   - Current commit
   - Port configuration (if applicable)

## Output Format

Present the information in a readable table format:

```
Worktree    Branch      Path                    Ports
main        main        /path/to/main          4000, 5153
purple      purple      /path/to/purple        4040, 5193
green       green       /path/to/green         4080, 5233
```

## Usage Examples

```
/worktree-list
```

This lists all active worktrees.

## Implementation

```bash
# Get worktree list
git worktree list

# For each worktree, check for .env files
for worktree in $(git worktree list --porcelain | grep worktree | cut -d' ' -f2); do
    if [ -f "$worktree/.env" ]; then
        # Extract port configuration
        grep PORT $worktree/.env
    fi
done
```

Return formatted table with worktree information.
