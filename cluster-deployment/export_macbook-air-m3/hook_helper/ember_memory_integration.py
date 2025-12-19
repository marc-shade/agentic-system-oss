#!/usr/bin/env python3
"""
Ember Memory Integration with Enhanced-Memory-MCP
Provides functions for Phoenix to store and query Ember's memory
"""

import json
from datetime import datetime
from pathlib import Path

def store_ember_critique_in_memory(critique, phoenix_response, user_message, tool_used):
    """
    Store Ember's critique in enhanced-memory-mcp
    Call this from Phoenix after getting Ember's critique
    """
    timestamp = int(datetime.now().timestamp())

    entity = {
        'name': f'ember_critique_{timestamp}',
        'entityType': 'ember_critique',
        'observations': [
            f'critique: {critique}',
            f'phoenix_response_length: {len(phoenix_response)}',
            f'user_message: {user_message[:200]}',
            f'tool_used: {tool_used or "none"}',
            f'timestamp: {datetime.now().isoformat()}'
        ]
    }

    return entity

def store_ember_consultation_in_memory(advice, question, context):
    """
    Store Ember's consultation advice in enhanced-memory-mcp
    Call this from Phoenix after consulting Ember
    """
    timestamp = int(datetime.now().timestamp())

    entity = {
        'name': f'ember_consultation_{timestamp}',
        'entityType': 'ember_consultation',
        'observations': [
            f'advice: {advice}',
            f'question: {question}',
            f'context: {json.dumps(context) if context else "none"}',
            f'timestamp: {datetime.now().isoformat()}'
        ]
    }

    return entity

def store_ember_violation_in_memory(violation_type, description, phoenix_action):
    """
    Store production-policy violations caught by Ember
    """
    timestamp = int(datetime.now().timestamp())

    entity = {
        'name': f'ember_violation_{timestamp}',
        'entityType': 'ember_violation',
        'observations': [
            f'violation_type: {violation_type}',
            f'description: {description}',
            f'phoenix_action: {phoenix_action}',
            f'timestamp: {datetime.now().isoformat()}'
        ]
    }

    return entity

def store_ember_learning_in_memory(pattern, frequency, recommendation):
    """
    Store patterns Ember has learned about Phoenix's tendencies
    """
    timestamp = int(datetime.now().timestamp())

    entity = {
        'name': f'ember_learning_{timestamp}',
        'entityType': 'ember_learning',
        'observations': [
            f'pattern: {pattern}',
            f'frequency: {frequency}',
            f'recommendation: {recommendation}',
            f'timestamp: {datetime.now().isoformat()}'
        ]
    }

    return entity

def query_ember_memory(memory_type, query_text, limit=5):
    """
    Query Ember's memory using enhanced-memory-mcp search

    Args:
        memory_type: 'critique', 'consultation', 'violation', or 'learning'
        query_text: Text to search for
        limit: Number of results to return

    Returns:
        List of matching memory entities
    """
    # This would be called with enhanced-memory-mcp search_nodes
    # For now, return structure for Phoenix to use
    return {
        'query': f'ember_{memory_type} {query_text}',
        'limit': limit,
        'entity_type': f'ember_{memory_type}'
    }

def get_ember_memory_stats():
    """
    Get statistics about Ember's memory
    Returns counts of each entity type
    """
    stats = {
        'ember_critique': 0,
        'ember_consultation': 0,
        'ember_violation': 0,
        'ember_learning': 0
    }

    # Read from local backup file
    memory_file = Path.home() / '.claude' / 'ember_memory.jsonl'
    if memory_file.exists():
        try:
            with open(memory_file, 'r') as f:
                for line in f:
                    try:
                        entity = json.loads(line)
                        entity_type = entity.get('entityType', '')
                        if entity_type in stats:
                            stats[entity_type] += 1
                    except:
                        pass
        except:
            pass

    return stats

# Example usage for Phoenix:
"""
# After consulting Ember
from ember_memory_integration import store_ember_consultation_in_memory

advice = phoenix_consults_ember("Should I use POC?")
entity = store_ember_consultation_in_memory(advice, "Should I use POC?", {'urgency': 'high'})

# Store in enhanced-memory-mcp
mcp__enhanced-memory-mcp__create_entities([entity])

# After getting critique
from ember_memory_integration import store_ember_critique_in_memory

critique = get_ember_critique(response, user_msg, "Write")
entity = store_ember_critique_in_memory(critique, response, user_msg, "Write")

# Store in enhanced-memory-mcp
mcp__enhanced-memory-mcp__create_entities([entity])

# Query Ember's past critiques
from ember_memory_integration import query_ember_memory

query = query_ember_memory('critique', 'POC prototype', limit=10)
results = mcp__enhanced-memory-mcp__search_nodes(
    query=query['query'],
    limit=query['limit']
)
"""
