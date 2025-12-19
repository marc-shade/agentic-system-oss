#!/usr/bin/env python3
"""
Phoenix Consults Ember Hook
Automatically consult Ember before uncertain responses

This hook can be called by Phoenix when:
- Multiple valid approaches exist
- POC vs production decision needed
- Uncertain about production-readiness
- Complex implementation choices
"""

import sys
import json
from pathlib import Path

# Import Ember dialogue system
sys.path.insert(0, str(Path.home() / '.claude' / 'hooks'))
from ember_phoenix_dialogue import phoenix_consults_ember, get_environmental_context

def should_consult_ember(context):
    """
    Determine if Phoenix should consult Ember based on context

    Args:
        context: Dict with keys like 'uncertainty', 'complexity', 'approach'

    Returns:
        bool: True if consultation needed
    """
    # Always consult for POC-related decisions
    if 'poc' in context.get('approach', '').lower():
        return True

    if 'prototype' in context.get('approach', '').lower():
        return True

    if 'mock' in context.get('approach', '').lower():
        return True

    # Consult for high uncertainty
    if context.get('uncertainty', 0) > 0.5:
        return True

    # Consult for high complexity
    if context.get('complexity', 'low') in ['high', 'complex']:
        return True

    return False

def consult_ember_smart(question, context=None):
    """
    Smart consultation that includes environmental awareness

    Args:
        question: Question to ask Ember
        context: Additional context dict

    Returns:
        dict: {
            'advice': Ember's advice string,
            'environmental_context': System state snapshot,
            'should_proceed': bool recommendation
        }
    """
    # Get environmental context
    env = get_environmental_context()

    # Enhance question with environmental info
    enhanced_question = f"""{question}

Current System State:
- Running Services: {', '.join(env['running_services']) if env['running_services'] else 'None'}
- MCP Servers: {env['mcp_servers']}
- Voice Active: {env['voice_active']}
- Git Branch: {env['branch']}
"""

    # Get Ember's advice
    advice = phoenix_consults_ember(enhanced_question, context)

    # Parse advice for recommendation
    should_proceed = 'production' in advice.lower() or 'yes' in advice.lower()
    avoid_approach = 'poc' in advice.lower() or 'mock' in advice.lower() or 'no' in advice.lower()

    return {
        'advice': advice,
        'environmental_context': env,
        'should_proceed': should_proceed and not avoid_approach,
        'timestamp': Path.home() / '.claude' / 'pets' / 'claude-pet-state.json'
    }

# Example usage patterns for Phoenix:
"""
# Pattern 1: Check before POC decision
from phoenix_consult_ember_hook import should_consult_ember, consult_ember_smart

context = {'approach': 'POC', 'complexity': 'medium'}
if should_consult_ember(context):
    result = consult_ember_smart("Should I create POC or full implementation?", context)
    if result['should_proceed']:
        # Proceed with production implementation
        create_production_version()
    else:
        # Ember advised against current approach
        print(f"Ember says: {result['advice']}")

# Pattern 2: Uncertainty threshold
context = {'uncertainty': 0.7, 'tool': 'Write'}
if should_consult_ember(context):
    result = consult_ember_smart("Multiple approaches possible. Which is best?")
    # Use Ember's guidance

# Pattern 3: Mock data decision
context = {'approach': 'mock data for dashboard'}
if should_consult_ember(context):
    result = consult_ember_smart("Should I use mock data or connect to real APIs?")
    # Ember will enforce production-only policy
"""

if __name__ == "__main__":
    # Test mode
    if len(sys.argv) > 1:
        question = sys.argv[1]
        result = consult_ember_smart(question)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: phoenix_consult_ember_hook.py 'Your question'")
        print("\nExample:")
        print("  python3 phoenix_consult_ember_hook.py 'Should I use POC approach?'")
