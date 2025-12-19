#!/usr/bin/env python3
"""
Action Item Tracker Hook - Solves the "Action Item Loss" critique

Automatically extracts, persists, and tracks action items from conversations.
Runs as PostToolUse hook to capture all commitments and tasks.
"""

import os
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib

class ActionItemTracker:
    def __init__(self):
        self.db_path = os.path.expanduser("/home/marc/.claude/action_items.db")
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for action items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_hash TEXT UNIQUE,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                agent_source TEXT,
                conversation_context TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                due_date TIMESTAMP,
                completed_date TIMESTAMP,
                source_tool TEXT,
                source_content TEXT,
                user_confirmed BOOLEAN DEFAULT FALSE,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_item_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_item_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                update_reason TEXT,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_item_id) REFERENCES action_items (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def extract_action_items(self, content: str, tool_name: str, agent_context: str = None) -> List[Dict]:
        """Extract action items using multiple patterns"""
        action_items = []
        
        # Pattern 1: Explicit commitments
        commitment_patterns = [
            r"I(?:'ll|'m going to| will| am going to)\s+([^.!?]+)",
            r"Next(?:,| steps?:?)\s+([^.!?]+)",
            r"Action(?:s?)(?::|\s+needed?:?)\s+([^.!?]+)",
            r"TODO?:?\s+([^.!?]+)",
            r"Follow[- ]?up:?\s+([^.!?]+)",
            r"(?:Will|Should|Must|Need to)\s+([^.!?]+)",
        ]
        
        for pattern in commitment_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                action_text = match.group(1).strip()
                if len(action_text) > 10:  # Filter out too-short matches
                    action_items.append({
                        'description': action_text,
                        'category': 'commitment',
                        'priority': self._determine_priority(action_text),
                        'pattern_matched': pattern
                    })
        
        # Pattern 2: Implementation tasks
        task_patterns = [
            r"(?:Creating?|Building?|Implementing?|Developing?)\s+([^.!?]{20,})",
            r"(?:Setting up|Configuring?|Installing?)\s+([^.!?]{15,})",
            r"(?:Testing?|Deploying?|Fixing?)\s+([^.!?]{15,})",
        ]
        
        for pattern in task_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                task_text = match.group(1).strip()
                action_items.append({
                    'description': f"Complete: {task_text}",
                    'category': 'implementation',
                    'priority': self._determine_priority(task_text),
                    'pattern_matched': pattern
                })
        
        # Pattern 3: Delegation items
        delegation_patterns = [
            r"(?:Delegating?|Assigning?|Handing off) (?:this |to )([^.!?]+)",
            r"(?:Bringing in|Using) the ([A-Z][^.!?]+(?:Agent|Specialist))",
        ]
        
        for pattern in delegation_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                delegation_text = match.group(1).strip()
                action_items.append({
                    'description': f"Delegate to: {delegation_text}",
                    'category': 'delegation',
                    'priority': 'medium',
                    'pattern_matched': pattern
                })
        
        # Add metadata to all items
        for item in action_items:
            item.update({
                'agent_source': agent_context or 'orchestrator',
                'source_tool': tool_name,
                'extracted_at': datetime.now().isoformat(),
                'conversation_context': content[:200] + '...' if len(content) > 200 else content
            })
            
        return action_items
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on text content"""
        high_priority_keywords = [
            'urgent', 'critical', 'immediately', 'asap', 'emergency',
            'production', 'security', 'bug', 'fix', 'broken'
        ]
        
        low_priority_keywords = [
            'consider', 'maybe', 'future', 'eventually', 'nice to have',
            'documentation', 'cleanup', 'refactor', 'optimize'
        ]
        
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in high_priority_keywords):
            return 'high'
        elif any(keyword in text_lower for keyword in low_priority_keywords):
            return 'low'
        else:
            return 'medium'
    
    def store_action_items(self, items: List[Dict]) -> List[str]:
        """Store action items in database, avoiding duplicates"""
        stored_ids = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for item in items:
            # Create hash to detect duplicates
            item_content = f"{item['description']}{item['category']}{item['agent_source']}"
            item_hash = hashlib.md5(item_content.encode()).hexdigest()
            
            # Check if item already exists
            cursor.execute('SELECT id FROM action_items WHERE item_hash = ?', (item_hash,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute('''
                    INSERT INTO action_items 
                    (item_hash, description, category, priority, agent_source, 
                     conversation_context, source_tool, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item_hash,
                    item['description'],
                    item['category'],
                    item['priority'],
                    item['agent_source'],
                    item['conversation_context'],
                    item['source_tool'],
                    json.dumps({
                        'pattern_matched': item.get('pattern_matched'),
                        'extracted_at': item.get('extracted_at')
                    })
                ))
                
                stored_ids.append(cursor.lastrowid)
            else:
                stored_ids.append(existing[0])
        
        conn.commit()
        conn.close()
        return stored_ids
    
    def get_active_action_items(self, limit: int = 20) -> List[Dict]:
        """Get current active action items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, description, category, priority, status, agent_source,
                   created_date, due_date, source_tool
            FROM action_items 
            WHERE status IN ('pending', 'in_progress')
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1 
                    WHEN 'medium' THEN 2 
                    WHEN 'low' THEN 3 
                END,
                created_date DESC
            LIMIT ?
        ''', (limit,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'description': row[1],
                'category': row[2],
                'priority': row[3],
                'status': row[4],
                'agent_source': row[5],
                'created_date': row[6],
                'due_date': row[7],
                'source_tool': row[8]
            })
        
        conn.close()
        return items
    
    def update_item_status(self, item_id: int, new_status: str, reason: str = None) -> bool:
        """Update action item status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current status
        cursor.execute('SELECT status FROM action_items WHERE id = ?', (item_id,))
        current = cursor.fetchone()
        if not current:
            conn.close()
            return False
        
        old_status = current[0]
        
        # Update item
        update_fields = {'status': new_status}
        if new_status == 'completed':
            update_fields['completed_date'] = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE action_items 
            SET status = ?, completed_date = ?
            WHERE id = ?
        ''', (new_status, update_fields.get('completed_date'), item_id))
        
        # Log the update
        cursor.execute('''
            INSERT INTO action_item_updates 
            (action_item_id, old_status, new_status, update_reason)
            VALUES (?, ?, ?, ?)
        ''', (item_id, old_status, new_status, reason or 'Manual update'))
        
        conn.commit()
        conn.close()
        return True
    
    def generate_daily_summary(self) -> str:
        """Generate daily action item summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get counts by status
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM action_items 
            WHERE created_date >= date('now', '-1 day')
            GROUP BY status
        ''')
        today_counts = dict(cursor.fetchall())
        
        # Get overdue items
        cursor.execute('''
            SELECT COUNT(*) 
            FROM action_items 
            WHERE due_date < date('now') AND status != 'completed'
        ''')
        overdue_count = cursor.fetchone()[0]
        
        # Get high priority pending
        cursor.execute('''
            SELECT description, agent_source, created_date
            FROM action_items 
            WHERE priority = 'high' AND status = 'pending'
            ORDER BY created_date DESC
            LIMIT 5
        ''')
        high_priority = cursor.fetchall()
        
        conn.close()
        
        summary = f"""
## Daily Action Items Summary - {datetime.now().strftime('%Y-%m-%d')}

### Today's Activity
- New Items: {today_counts.get('pending', 0)}
- Completed: {today_counts.get('completed', 0)}
- In Progress: {today_counts.get('in_progress', 0)}

### Attention Needed
- Overdue Items: {overdue_count}
- High Priority Pending: {len(high_priority)}

### Top Priority Items
"""
        
        for item in high_priority:
            summary += f"- **{item[0][:60]}...** (from {item[1]}) - {item[2]}\n"
        
        return summary

def hook_main(tool_name: str, tool_args: Dict, tool_result: str, context: Dict) -> Dict:
    """
    Main hook function - called after each tool use
    Extracts and stores action items from tool results
    """
    try:
        tracker = ActionItemTracker()
        
        # Skip action item extraction for certain tools
        skip_tools = ['Read', 'LS', 'Grep', 'WebSearch']
        if tool_name in skip_tools:
            return {"action_items_processed": 0}
        
        # Extract action items from tool result
        agent_context = context.get('agent_name', 'orchestrator')
        
        # Look in both tool arguments and results for action items
        content_to_analyze = ""
        if isinstance(tool_args, dict):
            # For Write/Edit operations, analyze the content being written
            if tool_name in ['Write', 'Edit', 'MultiEdit']:
                content_to_analyze += tool_args.get('content', '') + "\n"
                content_to_analyze += tool_args.get('new_string', '') + "\n"
            
            # For task delegation, analyze the task description
            if 'Task' in tool_name or 'subagent' in str(tool_args).lower():
                content_to_analyze += str(tool_args) + "\n"
        
        # Also analyze tool results for commitment statements
        if isinstance(tool_result, str) and len(tool_result) > 50:
            content_to_analyze += tool_result
        
        if not content_to_analyze.strip():
            return {"action_items_processed": 0}
        
        # Extract action items
        action_items = tracker.extract_action_items(
            content_to_analyze, 
            tool_name, 
            agent_context
        )
        
        if action_items:
            # Store action items
            stored_ids = tracker.store_action_items(action_items)
            
            # Generate notification for high priority items
            high_priority_items = [item for item in action_items if item['priority'] == 'high']
            if high_priority_items:
                notification_content = f"🚨 {len(high_priority_items)} high-priority action items detected:\n"
                for item in high_priority_items[:3]:  # Show first 3
                    notification_content += f"- {item['description'][:80]}...\n"
                
                # Save notification for user attention
                with open(os.path.expanduser("/home/marc/.claude/urgent_actions.txt"), "a") as f:
                    f.write(f"\n{datetime.now().isoformat()}: {notification_content}")
            
            return {
                "action_items_processed": len(action_items),
                "stored_item_ids": stored_ids,
                "high_priority_count": len(high_priority_items)
            }
        
        return {"action_items_processed": 0}
        
    except Exception as e:
        # Log error but don't break the tool chain
        with open(os.path.expanduser("/home/marc/.claude/hooks/action_tracker_errors.log"), "a") as f:
            f.write(f"{datetime.now().isoformat()}: Error in action tracker: {str(e)}\n")
        return {"error": str(e), "action_items_processed": 0}

def get_action_items_dashboard() -> str:
    """Generate action items dashboard for user review"""
    try:
        tracker = ActionItemTracker()
        active_items = tracker.get_active_action_items()
        
        dashboard = f"""
# Action Items Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Active Items ({len(active_items)})
"""
        
        for item in active_items:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[item['priority']]
            dashboard += f"""
### {priority_emoji} {item['description'][:80]}{"..." if len(item['description']) > 80 else ""}
- **Category**: {item['category']}
- **Source**: {item['agent_source']} via {item['source_tool']}
- **Created**: {item['created_date']}
- **Status**: {item['status']}
- **ID**: #{item['id']}

"""
        
        dashboard += f"""
## Quick Actions
- Mark item complete: `mark_action_complete(item_id)`
- Update status: `update_action_status(item_id, new_status)`
- View full history: `get_action_history(item_id)`

---
*Action items are automatically tracked from all agent interactions*
"""
        
        return dashboard
        
    except Exception as e:
        return f"Error generating dashboard: {str(e)}"

if __name__ == "__main__":
    # CLI interface for manual action item management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: action-item-tracker.py [dashboard|summary|complete <id>]")
        sys.exit(1)
    
    command = sys.argv[1]
    tracker = ActionItemTracker()
    
    if command == "dashboard":
        print(get_action_items_dashboard())
    elif command == "summary":
        print(tracker.generate_daily_summary())
    elif command == "complete" and len(sys.argv) > 2:
        item_id = int(sys.argv[2])
        if tracker.update_item_status(item_id, 'completed', 'Manual completion'):
            print(f"✅ Action item #{item_id} marked complete")
        else:
            print(f"❌ Failed to update item #{item_id}")
    else:
        print("Unknown command")