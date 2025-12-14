# Create Git Worktree

Create a new git worktree with automatic port offset configuration.

## Task

When the user requests to create a git worktree:

1. Determine the worktree name from user input
2. Calculate port offsets if working with a web project
3. Create the worktree using git worktree add
4. Configure environment variables for the new worktree if needed

## Port Offset Strategy

For web projects with multiple services:
- Frontend: Base port + offset
- Backend API: Base API port + offset
- Database: Base DB port + offset

Example: For offset 4:
- Frontend: 4040 (4000 + 40)
- Backend: 5193 (5153 + 40)

## Usage Examples

```
/worktree-create purple 4
```

This creates a worktree named "purple" with port offset 4.

## Implementation

```bash
# Create worktree
git worktree add ../project-{name} -b {name}

# If ports are specified, create .env file
cd ../project-{name}
echo "PORT={calculated_port}" > .env
echo "API_PORT={calculated_api_port}" >> .env
```

Return confirmation with the worktree path and configured ports.
