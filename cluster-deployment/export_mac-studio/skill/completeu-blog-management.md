# CompleteU Blog Management

Complete blog automation system for CompleteU marketing operations.

## Core Functions

**Create Blog Task**
- Syntax: Create blog task: "Title" "Topic" [agent] [priority] [when]
- Auto-assigns appropriate CompleteU agent based on topic keywords
- Supports scheduling (immediate or future date/time)

**Generate Complete Blog**
- Full workflow: research → content (800-1200 words) → 3 FLUX images → SEO → save
- FERPA compliance checks and brand alignment
- Agents: john-meyer (CEO), jessica-haberley (VP Client Success), michael-conley (VP Marketing), ryan-tracy (VP Partnerships), marc-shade (CISO)

**Task Management**
- List tasks: Filter by status (all, pending, running, completed, failed) and limit
- Run task: Execute immediately by task_id or run next pending
- Status: System metrics, success rate, next scheduled, failed tasks
- Cleanup: Remove old completed tasks (default: 30 days)

**Scheduler Operations**
- Start daemon: Background scheduler for automated posting
- Schedule weekly: Auto-create weekly posts (Tuesdays 9AM, Thursdays 2PM)
- Dashboard: Real-time monitoring interface

## Workflow Location
Base path: `/Volumes/orange/projects/CompleteU/marketing`
Scripts: `automated_blog_scheduler.py`, `run_blog_automation.py`

## Quality Gates
- FERPA compliance validation
- Brand voice alignment
- Technical accuracy checks
- SEO optimization
- Image generation (FLUX)

## Example Operations
```
Create blog task: "Future of Enrollment" "AI in Higher Ed" "john-meyer" "high"
Generate blog: "Student Success" "Retention Programs"
List tasks: pending 5
Run next pending task
Show system status
Start scheduler daemon
Schedule weekly posts for 4 weeks
Clean up tasks older than 60 days
```

## Token Cost: ~150 tokens
Replaces 9 slash commands (245 lines, ~900 tokens) = **750 token savings**
