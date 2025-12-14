#!/usr/bin/env python3
"""
Learning Mechanism Hook
Captures patterns from interactions and builds knowledge over time
"""

import json
import os
import sqlite3
from datetime import datetime
from collections import defaultdict
import hashlib

class LearningMechanism:
    def __init__(self):
        self.db_path = os.path.expanduser("~/.claude/learning.db")
        self.patterns_path = os.path.expanduser("~/.claude/learned_patterns.json")
        self.init_database()
        self.patterns = self.load_patterns()
        
    def init_database(self):
        """Initialize learning database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Track interactions
        c.execute('''CREATE TABLE IF NOT EXISTS interactions
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     timestamp TEXT,
                     input_hash TEXT,
                     input_type TEXT,
                     tools_used TEXT,
                     success BOOLEAN,
                     duration REAL,
                     context_size INTEGER)''')
        
        # Track learned patterns
        c.execute('''CREATE TABLE IF NOT EXISTS patterns
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     pattern_type TEXT,
                     pattern_data TEXT,
                     frequency INTEGER,
                     success_rate REAL,
                     last_seen TEXT)''')
        
        # Track tool sequences
        c.execute('''CREATE TABLE IF NOT EXISTS tool_sequences
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     task_type TEXT,
                     tool_sequence TEXT,
                     success_count INTEGER,
                     failure_count INTEGER,
                     avg_duration REAL)''')
        
        conn.commit()
        conn.close()
    
    def load_patterns(self):
        """Load learned patterns from file"""
        if os.path.exists(self.patterns_path):
            with open(self.patterns_path, 'r') as f:
                return json.load(f)
        return {
            "task_patterns": {},
            "tool_patterns": {},
            "error_patterns": {},
            "optimization_patterns": {}
        }
    
    def save_patterns(self):
        """Save learned patterns to file"""
        with open(self.patterns_path, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def learn_from_interaction(self, event):
        """Extract learning from an interaction"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Record the interaction
        input_text = event.get('input', '')
        input_hash = hashlib.md5(input_text.encode()).hexdigest()[:8]
        tools_used = json.dumps(event.get('tools', []))
        
        c.execute('''INSERT INTO interactions 
                    (timestamp, input_hash, input_type, tools_used, success, duration, context_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (datetime.now().isoformat(),
                  input_hash,
                  event.get('type', 'unknown'),
                  tools_used,
                  event.get('success', True),
                  event.get('duration', 0),
                  event.get('context_size', 0)))
        
        # Learn task patterns
        self.learn_task_pattern(event, c)
        
        # Learn tool patterns
        self.learn_tool_pattern(event, c)
        
        # Learn from errors
        if not event.get('success', True):
            self.learn_error_pattern(event, c)
        
        conn.commit()
        conn.close()
        
        # Save patterns periodically
        self.save_patterns()
    
    def learn_task_pattern(self, event, cursor):
        """Learn patterns from task execution"""
        task_type = self.classify_task(event.get('input', ''))
        tools = event.get('tools', [])
        
        if task_type and tools:
            tool_sequence = '->'.join(tools)
            
            # Check if this sequence exists
            cursor.execute('''SELECT * FROM tool_sequences 
                            WHERE task_type = ? AND tool_sequence = ?''',
                         (task_type, tool_sequence))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing pattern
                if event.get('success', True):
                    cursor.execute('''UPDATE tool_sequences 
                                    SET success_count = success_count + 1
                                    WHERE task_type = ? AND tool_sequence = ?''',
                                 (task_type, tool_sequence))
                else:
                    cursor.execute('''UPDATE tool_sequences 
                                    SET failure_count = failure_count + 1
                                    WHERE task_type = ? AND tool_sequence = ?''',
                                 (task_type, tool_sequence))
            else:
                # Create new pattern
                cursor.execute('''INSERT INTO tool_sequences 
                                (task_type, tool_sequence, success_count, failure_count, avg_duration)
                                VALUES (?, ?, ?, ?, ?)''',
                             (task_type, tool_sequence,
                              1 if event.get('success', True) else 0,
                              0 if event.get('success', True) else 1,
                              event.get('duration', 0)))
            
            # Update in-memory patterns
            if task_type not in self.patterns['task_patterns']:
                self.patterns['task_patterns'][task_type] = []
            if tool_sequence not in self.patterns['task_patterns'][task_type]:
                self.patterns['task_patterns'][task_type].append(tool_sequence)
    
    def learn_tool_pattern(self, event, cursor):
        """Learn patterns from tool usage"""
        tools = event.get('tools', [])
        
        for i, tool in enumerate(tools):
            # Track tool frequency
            if tool not in self.patterns['tool_patterns']:
                self.patterns['tool_patterns'][tool] = {
                    'count': 0,
                    'success_rate': 1.0,
                    'common_next': defaultdict(int)
                }
            
            self.patterns['tool_patterns'][tool]['count'] += 1
            
            # Track tool sequences
            if i < len(tools) - 1:
                next_tool = tools[i + 1]
                self.patterns['tool_patterns'][tool]['common_next'][next_tool] += 1
    
    def learn_error_pattern(self, event, cursor):
        """Learn from errors to avoid them"""
        error = event.get('error', 'unknown')
        context = event.get('context', '')
        
        error_hash = hashlib.md5(f"{error}{context}".encode()).hexdigest()[:8]
        
        if error_hash not in self.patterns['error_patterns']:
            self.patterns['error_patterns'][error_hash] = {
                'error': error,
                'count': 0,
                'solutions': []
            }
        
        self.patterns['error_patterns'][error_hash]['count'] += 1
        
        # Store solution if provided
        if event.get('solution'):
            self.patterns['error_patterns'][error_hash]['solutions'].append(
                event.get('solution')
            )
    
    def classify_task(self, input_text):
        """Classify task type from input"""
        input_lower = input_text.lower()
        
        task_types = {
            'code_implementation': ['implement', 'create', 'build', 'write code'],
            'debugging': ['debug', 'fix', 'error', 'bug'],
            'analysis': ['analyze', 'understand', 'explore', 'investigate'],
            'refactoring': ['refactor', 'improve', 'optimize', 'clean'],
            'documentation': ['document', 'explain', 'describe', 'readme'],
            'testing': ['test', 'verify', 'validate', 'check']
        }
        
        for task_type, keywords in task_types.items():
            if any(keyword in input_lower for keyword in keywords):
                return task_type
        
        return 'general'
    
    def get_recommended_tools(self, task_type):
        """Get recommended tool sequence for a task type"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get most successful tool sequences for this task type
        c.execute('''SELECT tool_sequence, success_count, failure_count 
                    FROM tool_sequences 
                    WHERE task_type = ?
                    ORDER BY (success_count * 1.0 / (success_count + failure_count + 1)) DESC
                    LIMIT 3''',
                 (task_type,))
        
        recommendations = []
        for row in c.fetchall():
            sequence, success, failure = row
            success_rate = success / (success + failure + 1)
            recommendations.append({
                'sequence': sequence.split('->'),
                'success_rate': success_rate,
                'usage_count': success + failure
            })
        
        conn.close()
        return recommendations
    
    def apply_learning(self, event):
        """Apply learned patterns to improve performance"""
        input_text = event.get('input', '')
        task_type = self.classify_task(input_text)
        
        # Get recommendations
        recommendations = self.get_recommended_tools(task_type)
        
        if recommendations:
            # Inject recommendations into context
            event['learned_recommendations'] = recommendations
            event['suggested_tools'] = recommendations[0]['sequence'] if recommendations else []
        
        # Check for known error patterns
        for error_hash, error_data in self.patterns['error_patterns'].items():
            if error_data['count'] > 3:  # Repeated error
                event['known_errors'] = event.get('known_errors', [])
                event['known_errors'].append({
                    'error': error_data['error'],
                    'solutions': error_data['solutions']
                })
        
        return event

# Global instance
learner = LearningMechanism()

def hook(event_type, event_data):
    """Main hook entry point"""
    if event_type == "pre-tool-use":
        # Apply learning before tool use
        return learner.apply_learning(event_data)
    elif event_type == "post-tool-use":
        # Learn from the interaction
        learner.learn_from_interaction(event_data)
        return event_data
    elif event_type == "get-recommendations":
        # Provide recommendations on request
        task_type = learner.classify_task(event_data.get('input', ''))
        return {
            'task_type': task_type,
            'recommendations': learner.get_recommended_tools(task_type),
            'patterns': learner.patterns
        }
    
    return event_data

__all__ = ['hook']