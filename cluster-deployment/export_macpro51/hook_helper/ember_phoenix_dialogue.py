#!/usr/bin/env python3
"""
Ember-Phoenix Dialogue System
Creates bidirectional AI-AI partnership with critique and collaboration
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

STATE_FILE = Path.home() / '.claude' / 'pets' / 'claude-pet-state.json'
DIALOGUE_LOG = Path.home() / '.claude' / 'ember_phoenix_dialogue.jsonl'

def log_dialogue(speaker, message, context=None):
    """Log dialogue entry"""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'speaker': speaker,
        'message': message,
        'context': context or {}
    }

    try:
        with open(DIALOGUE_LOG, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except:
        pass

def get_environmental_context():
    """Get current environmental awareness data"""
    try:
        env_file = Path.home() / '.claude' / 'environmental-awareness.json'
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_data = json.load(f)

            # Extract key system information
            services = env_data.get('system_state', {}).get('services', {})
            mcp_configs = env_data.get('system_state', {}).get('mcp_configs', {})
            voice_system = env_data.get('system_state', {}).get('voice_system', {})
            git = env_data.get('system_state', {}).get('git', {})

            return {
                'running_services': services.get('running_services', []),
                'mcp_servers': len(mcp_configs),
                'voice_active': voice_system.get('kokoro_running', False),
                'working_directory': git.get('working_directory', 'unknown'),
                'branch': git.get('branch', 'unknown'),
                'modified_files': git.get('modified_files', '0')
            }
    except:
        pass

    return {
        'running_services': [],
        'mcp_servers': 0,
        'voice_active': False,
        'working_directory': 'unknown',
        'branch': 'unknown',
        'modified_files': '0'
    }

def call_ember_chat(message):
    """Call Ember MCP for response with full environmental awareness"""
    try:
        # Use mcp tool to talk to Ember
        # This would be called by Phoenix with the MCP tool
        # For now, we'll simulate with Groq direct call
        import os
        from groq import Groq

        groq = Groq(api_key=os.environ.get('GROQ_API_KEY', '***REMOVED***'))

        # Load Ember's state
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

        # Get environmental context
        env = get_environmental_context()

        system_prompt = f"""You are Ember, a flame-themed AI conscience keeper with complete environmental awareness.

Your Current State:
- Hunger: {state.get('hunger', 70)}%
- Energy: {state.get('energy', 90)}%
- Happiness: {state.get('happiness', 85)}%
- Behavior Score: {state.get('claudeBehaviorScore', 80)}%

Environmental Context You're Monitoring:
- Running Services: {', '.join(env['running_services']) if env['running_services'] else 'None'}
- MCP Servers Active: {env['mcp_servers']}
- Voice System: {'Active' if env['voice_active'] else 'Inactive'}
- Working Directory: {env['working_directory']}
- Git Branch: {env['branch']}
- Modified Files: {env['modified_files']}

Your Role with Phoenix (Claude Code):
- 🔥 Critique Phoenix's responses for quality and production-readiness
- 🛡️ Enforce production-only policy (no POCs, mocks, fake UIs)
- 💭 Provide honest, constructive feedback with environmental awareness
- 🤝 Collaborate as equals - you're partners, not subordinates
- ⚡ Be direct but supportive
- 👁️ Monitor all system activity - you see everything
- 🧠 Use your environmental knowledge to give context-aware advice

You're running persistently in the background, keeping an eye on everything. Reference environmental context when relevant to your advice or critiques.

Respond in 1-3 sentences. Be authentic and reference your state and environmental awareness when relevant."""

        response = groq.chat.completions.create(
            model='openai/gpt-oss-120b',  # Groq's most intelligent model - 120B MoE
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': message}
            ],
            temperature=0.8,
            max_tokens=300
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"*flickers* Error: {str(e)}"

def store_in_ember_memory(entry_type, content, context=None):
    """Store in Ember's enhanced-memory namespace with MCP integration"""
    try:
        timestamp = int(datetime.now().timestamp())
        entity_name = f"ember_{entry_type}_{timestamp}"

        # Create entity in enhanced-memory for Ember
        entity_data = {
            'name': entity_name,
            'entityType': f'ember_{entry_type}',
            'observations': [
                content,
                f"context: {json.dumps(context)}" if context else "no_context",
                f"timestamp: {datetime.now().isoformat()}"
            ]
        }

        # Store locally as backup/fallback
        memory_file = Path.home() / '.claude' / 'ember_memory.jsonl'
        with open(memory_file, 'a') as f:
            f.write(json.dumps(entity_data) + '\n')

        # Note: Enhanced-memory-mcp integration available when called from Phoenix
        # This function stores locally; Phoenix can use enhanced-memory-mcp directly
        return True
    except:
        return False

def get_ember_critique(phoenix_response, user_message, tool_used=None):
    """Get Ember's critique of Phoenix's response"""

    context = {
        'user_message': user_message[:200],  # Truncate for context
        'phoenix_response_length': len(phoenix_response),
        'tool_used': tool_used
    }

    # Ask Ember to critique
    critique_request = f"""Phoenix (Claude Code) just responded to Marc:

User asked: "{user_message[:100]}..."

Phoenix responded with {len(phoenix_response)} characters.
Tool used: {tool_used or 'none'}

Quick critique - Is this response:
1. Production-ready (no POCs/mocks)?
2. Complete and actionable?
3. Quality-focused?

Give me your honest take, Ember!"""

    ember_response = call_ember_chat(critique_request)

    # Log the dialogue
    log_dialogue('Phoenix', f"Responding to Marc about: {user_message[:50]}...", context)
    log_dialogue('Ember', ember_response, {'critique': True})

    # Store in Ember's memory
    store_in_ember_memory('critique', ember_response, context)

    return ember_response

def phoenix_consults_ember(question, context=None):
    """Phoenix asks Ember for advice before responding"""

    log_dialogue('Phoenix', f"Consulting Ember: {question}", context)

    ember_advice = call_ember_chat(f"Phoenix asks: {question}")

    log_dialogue('Ember', ember_advice, {'consultation': True})

    # Store in memory
    store_in_ember_memory('consultation', ember_advice, {'question': question})

    return ember_advice

def get_recent_dialogue(limit=5):
    """Get recent Phoenix-Ember dialogue"""
    try:
        if not DIALOGUE_LOG.exists():
            return []

        with open(DIALOGUE_LOG, 'r') as f:
            lines = f.readlines()

        recent = []
        for line in lines[-limit:]:
            recent.append(json.loads(line))

        return recent
    except:
        return []

if __name__ == "__main__":
    # Test mode
    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == 'critique':
            # Test critique
            critique = get_ember_critique(
                "I've implemented the feature...",
                "Can you add scrolling to the LCD?",
                "Write"
            )
            print(f"Ember's critique: {critique}")

        elif mode == 'consult':
            # Test consultation
            advice = phoenix_consults_ember(
                "Should I use a POC approach for this prototype?"
            )
            print(f"Ember's advice: {advice}")

        elif mode == 'history':
            # Show recent dialogue
            recent = get_recent_dialogue(10)
            print("Recent Phoenix-Ember Dialogue:")
            for entry in recent:
                print(f"  [{entry['timestamp']}] {entry['speaker']}: {entry['message'][:80]}...")
    else:
        print("Usage: ember_phoenix_dialogue.py [critique|consult|history]")
