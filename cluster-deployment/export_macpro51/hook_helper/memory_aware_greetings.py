#!/usr/bin/env python3
"""
Memory-Aware Greeting System
Provides organic, context-aware greetings based on previous session memory
"""

import os
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

class MemoryAwareGreetings:
    """Organic greeting system that remembers context"""
    
    def __init__(self):
        self.memory_db = Path("/home/marc/.claude/agentic-evolution/events.db")
        self.session_db = Path("/home/marc/.claude/session_memory.db")
        self.log_file = Path("/home/marc/.claude/memory_greetings.log")
        self.init_session_memory()
    
    def init_session_memory(self):
        """Initialize session memory database"""
        self.session_db.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(self.session_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                session_type TEXT,  -- 'start' or 'end'
                work_summary TEXT,
                tasks_completed TEXT,
                current_focus TEXT,
                next_steps TEXT,
                mood TEXT,
                metadata TEXT
            )
        """)
        conn.close()
    
    def get_last_session(self) -> Optional[Dict[str, Any]]:
        """Get the last session's information"""
        try:
            conn = sqlite3.connect(self.session_db)
            cursor = conn.execute("""
                SELECT timestamp, work_summary, tasks_completed, current_focus, next_steps, mood
                FROM session_memory 
                WHERE session_type = 'end'
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'timestamp': datetime.fromisoformat(row[0]),
                    'work_summary': row[1],
                    'tasks_completed': json.loads(row[2]) if row[2] else [],
                    'current_focus': row[3],
                    'next_steps': row[4],
                    'mood': row[5]
                }
        except Exception as e:
            self._log(f"Error getting last session: {e}")
        return None
    
    def save_session_start(self, greeting: str, context: Dict[str, Any]):
        """Save session start information"""
        try:
            conn = sqlite3.connect(self.session_db)
            conn.execute("""
                INSERT INTO session_memory 
                (timestamp, session_type, work_summary, current_focus, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'start',
                greeting,
                context.get('focus', ''),
                json.dumps(context)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self._log(f"Error saving session start: {e}")
    
    def save_session_end(self, summary: Dict[str, Any]):
        """Save session end information"""
        try:
            conn = sqlite3.connect(self.session_db)
            conn.execute("""
                INSERT INTO session_memory 
                (timestamp, session_type, work_summary, tasks_completed, current_focus, next_steps, mood)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                'end',
                summary.get('work_summary', ''),
                json.dumps(summary.get('tasks_completed', [])),
                summary.get('current_focus', ''),
                summary.get('next_steps', ''),
                summary.get('mood', 'productive')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self._log(f"Error saving session end: {e}")
    
    def generate_organic_greeting(self) -> str:
        """Generate an organic, memory-aware greeting"""
        now = datetime.now()
        hour = now.hour
        day_name = now.strftime('%A')
        
        # Get base time-of-day greeting
        if 5 <= hour < 12:
            base = "Good morning Marc"
        elif 12 <= hour < 17:
            base = "Good afternoon Marc"
        elif 17 <= hour < 22:
            base = "Good evening Marc"
        else:
            base = "Hey Marc"
        
        # Check last session
        last_session = self.get_last_session()
        
        if not last_session:
            # First time or no memory
            return f"{base}! Ready to build something amazing today?"
        
        # Calculate time since last session
        time_since = now - last_session['timestamp']
        
        # Generate context-aware continuation
        if time_since < timedelta(hours=4):
            # Same day, continuing work
            if last_session.get('current_focus'):
                return f"{base}! Welcome back. Ready to continue with {last_session['current_focus']}?"
            else:
                return f"{base}! Let's pick up where we left off."
        
        elif time_since < timedelta(days=1):
            # Next day
            if last_session.get('tasks_completed'):
                task_count = len(last_session['tasks_completed'])
                return f"{base}! Yesterday we knocked out {task_count} tasks. What's on the agenda today?"
            else:
                return f"{base}! Fresh day, fresh start. What should we tackle first?"
        
        elif time_since < timedelta(days=3):
            # Few days ago
            if last_session.get('next_steps'):
                return f"{base}! Last time we talked about {last_session['next_steps']}. Want to dive into that?"
            else:
                return f"{base}! It's been a couple days. What would you like to work on?"
        
        elif time_since < timedelta(weeks=1):
            # Within a week
            return f"{base}! Good to see you again. What can I help you build today?"
        
        else:
            # Long absence
            return f"{base}! It's been a while! What exciting project brings you back?"
    
    def generate_organic_goodbye(self, session_summary: Dict[str, Any]) -> str:
        """Generate an organic goodbye based on session accomplishments"""
        tasks = session_summary.get('tasks_completed', [])
        duration = session_summary.get('duration_hours', 0)
        next_steps = session_summary.get('next_steps', '')
        
        # Build accomplishment summary
        if tasks:
            task_count = len(tasks)
            if task_count == 1:
                accomplishment = f"Got {tasks[0]} done"
            elif task_count <= 3:
                accomplishment = f"Completed {', '.join(tasks[:2])}"
                if task_count == 3:
                    accomplishment += f" and {tasks[2]}"
            else:
                accomplishment = f"Knocked out {task_count} tasks"
        else:
            accomplishment = "Made good progress"
        
        # Time-based farewell
        hour = datetime.now().hour
        if hour < 17:
            farewell = "Have a great rest of your day"
        elif hour < 21:
            farewell = "Enjoy your evening"
        else:
            farewell = "Get some good rest"
        
        # Build complete goodbye
        if duration > 2:
            goodbye = f"Great session Marc! {accomplishment} in {duration:.1f} hours. {farewell}!"
        else:
            goodbye = f"{accomplishment} today. {farewell} Marc!"
        
        # Add next steps if relevant
        if next_steps:
            goodbye += f" Next time we can tackle {next_steps}."
        
        return goodbye
    
    def _log(self, message: str):
        """Log messages"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def speak(self, message: str):
        """Speak using VoiceMode"""
        try:
            # Use VoiceMode MCP for natural voice
            from voicemode_integration import voice
            voice.speak(message, wait_for_response=False)
            self._log(f"Spoke: {message}")
            return True
        except Exception as e:
            self._log(f"Speech failed: {e}")
            # Fallback to macOS say
            try:
                subprocess.run(['say', '-v', 'Samantha', message], check=True)
                return True
            except:
                return False

# Global instance
memory_greetings = MemoryAwareGreetings()

def organic_session_start():
    """Generate and speak organic greeting"""
    greeting = memory_greetings.generate_organic_greeting()
    memory_greetings.speak(greeting)
    memory_greetings.save_session_start(greeting, {'focus': 'general'})
    return greeting

def organic_session_end(summary: Dict[str, Any] = None):
    """Generate and speak organic goodbye"""
    if not summary:
        summary = {'tasks_completed': [], 'duration_hours': 1}
    
    goodbye = memory_greetings.generate_organic_goodbye(summary)
    memory_greetings.speak(goodbye)
    memory_greetings.save_session_end(summary)
    return goodbye

if __name__ == "__main__":
    # Test the organic greetings
    print("Testing Organic Greetings...")
    
    # Test greeting
    greeting = organic_session_start()
    print(f"Greeting: {greeting}")
    
    # Test goodbye
    test_summary = {
        'tasks_completed': ['voice system update', 'memory integration'],
        'duration_hours': 2.5,
        'next_steps': 'dashboard implementation'
    }
    goodbye = organic_session_end(test_summary)
    print(f"Goodbye: {goodbye}")