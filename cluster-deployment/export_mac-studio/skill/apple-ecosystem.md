# Apple Ecosystem Integration

Complete Apple ecosystem management using apple-mcp: Calendar, Mail, Messages, Notes, and Reminders.

## Calendar Operations
- **create**: Create new events with time, duration, location, notes
- **search**: Find events by keyword or date range
- **list**: Show upcoming events (today, week, month)
- **open**: Open specific event for editing
- Supports: All-day events, recurring patterns, multiple calendars

## Mail Operations
- **send**: Compose and send emails with attachments
- **unread**: Get unread messages filtered by date/sender
- **search**: Find emails by subject, sender, or content
- **mailboxes**: List all mail folders and categories
- **accounts**: Show configured email accounts
- Smart filters: Today's unread, specific sender, keywords

## Messages (iMessage/SMS)
- **send**: Send messages to contacts or phone numbers
- **recent**: View recent conversations
- **search**: Find messages by contact or keyword
- **chats**: List all active conversations
- Group messaging and attachments supported

## Notes Operations
- **create**: Create new notes with rich content
- **search**: Find notes by title or content
- **list**: Show all notes or by folder
- **update**: Modify existing notes
- **folders**: Manage note organization
- Markdown support and attachments

## Reminders Operations
- **create**: Create tasks with due dates and priorities
- **complete**: Mark reminders as done
- **list**: Show upcoming or overdue tasks
- **search**: Find reminders by keyword
- **lists**: Manage reminder lists (work, personal, shopping)
- Priority levels and due date notifications

## Example Usage
```
Create calendar event for team standup tomorrow 9am 30min
Send email to john@example.com about project update
Search messages from Sarah about meeting
Create note "API Design Ideas" with bullet points
Add reminder "Buy groceries" tomorrow 5pm high priority
```

## MCP Integration
All operations route through apple-mcp server:
- `mcp__apple-mcp__calendar` for calendar ops
- `mcp__apple-mcp__mail` for email
- `mcp__apple-mcp__messages` for iMessage
- `mcp__apple-mcp__notes` for Notes
- `mcp__apple-mcp__reminders` for tasks

## Token Cost: ~100 tokens
Replaces 5 slash commands (95 lines, ~380 tokens) = **280 token savings**
