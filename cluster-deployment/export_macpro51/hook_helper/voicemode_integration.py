#!/usr/bin/env python3
"""
VoiceMode Integration for Claude Code Hooks
Provides voice synthesis using free Silero TTS at important work points
"""

import os
import subprocess
import datetime
import json
import sys
from typing import Optional, Dict, Any

class VoiceModeIntegration:
    """VoiceMode integration for hook system"""
    
    def __init__(self):
        """Initialize VoiceMode with Chatterbox TTS"""
        self.env = os.environ.copy()
        self.env.update({
            'TTS_PROVIDER': 'openai',
            'TTS_BASE_URL': 'http://127.0.0.1:8880/v1',
            'TTS_API_KEY': 'chatterbox-local',
            'TTS_MODEL': 'tts-1',
            'TTS_VOICE': 'af_sky',  # Using Chatterbox voice
            'STT_PROVIDER': 'openai',
            'OPENAI_API_KEY': self._get_api_key(),
            'VOICEMODE_DEBUG': 'false',
            'VOICEMODE_PREFER_LOCAL': 'true'
        })
        self.python_path = '/opt/homebrew/bin/python3.10'
        self.log_file = '/home/marc/.claude/voicemode_hook.log'
        
    def _get_api_key(self) -> str:
        """Get OpenAI API key from file"""
        try:
            with open('/home/marc/.openai_api_key', 'r') as f:
                return f.read().strip()
        except:
            return os.environ.get('OPENAI_API_KEY', '')
    
    def _log(self, message: str):
        """Log messages with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass
    
    def speak(self, message: str, wait_for_response: bool = False) -> bool:
        """
        Speak a message using VoiceMode with free Silero TTS
        
        Args:
            message: Text to speak
            wait_for_response: Whether to wait for user response
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Keep messages concise (under 20 words for quick feedback)
            words = message.split()
            if len(words) > 20 and not wait_for_response:
                # Truncate long messages for quick notifications
                message = ' '.join(words[:18]) + '...'
            
            cmd = [
                self.python_path, '-m', 'voice_mode', 'converse',
                '-m', message
            ]
            
            if not wait_for_response:
                cmd.append('--no-wait')
            
            # Run VoiceMode command
            result = subprocess.run(
                cmd,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            success = result.returncode == 0
            
            if success:
                self._log(f"Spoke: {message}")
            else:
                self._log(f"Failed to speak: {result.stderr}")
            
            return success
            
        except subprocess.TimeoutExpired:
            self._log(f"Timeout speaking: {message}")
            return False
        except Exception as e:
            self._log(f"Error speaking: {e}")
            return False
    
    def get_time_based_greeting(self) -> str:
        """Generate context-aware greeting"""
        now = datetime.datetime.now()
        hour = now.hour
        day_name = now.strftime('%A')
        
        # Time-based greeting
        if 5 <= hour < 12:
            greeting = "Good morning Marc!"
            suffix = "Ready to build?"
        elif 12 <= hour < 17:
            greeting = "Good afternoon Marc!"
            suffix = "Let's get productive!"
        elif 17 <= hour < 22:
            greeting = "Good evening Marc!"
            suffix = "Working late today?"
        else:
            greeting = "Hello Marc!"
            suffix = "Burning midnight oil?"
        
        # Special day additions
        if day_name == 'Friday':
            suffix = "Happy Friday!"
        elif day_name in ['Saturday', 'Sunday']:
            suffix = "Weekend productivity!"
        elif day_name == 'Monday':
            suffix = "Fresh week ahead!"
        
        return f"{greeting} {suffix}"
    
    def get_tool_announcement(self, tool_name: str, description: str = "") -> Optional[str]:
        """
        Generate appropriate voice announcement for tool usage
        
        Returns None for routine operations, message for important ones
        """
        # Important tools that deserve announcement
        important_tools = {
            'Write': "Creating new file",
            'MultiEdit': "Making multiple changes",
            'Bash': "Running command",
            'Task': "Spawning agent",
            'TodoWrite': "Updating tasks",
            'WebSearch': "Searching the web",
            'WebFetch': "Fetching content"
        }
        
        # Skip routine operations
        skip_tools = {'Read', 'LS', 'Grep', 'Glob'}
        
        if tool_name in skip_tools:
            return None
        
        if tool_name in important_tools:
            if description:
                # Use the provided description if it's short
                if len(description.split()) <= 5:
                    return description
            return important_tools[tool_name]
        
        # For unknown tools, only announce if significant
        if tool_name.startswith('mcp__'):
            return f"Using {tool_name.split('__')[1].split('_')[0]}"
        
        return None
    
    def get_completion_message(self, tool_name: str, success: bool) -> Optional[str]:
        """
        Generate completion message for important operations
        
        Returns None for routine completions
        """
        # Only announce completions for significant operations
        significant_completions = {
            'Write': ("File created", "File creation failed"),
            'MultiEdit': ("Changes complete", "Changes failed"),
            'Bash': ("Command finished", "Command failed"),
            'Task': ("Agent completed", "Agent failed"),
            'WebFetch': ("Content fetched", "Fetch failed")
        }
        
        if tool_name in significant_completions:
            messages = significant_completions[tool_name]
            return messages[0] if success else messages[1]
        
        return None
    
    def announce_milestone(self, milestone_type: str, details: str = "") -> bool:
        """
        Announce important milestones during work
        
        Types: 'error', 'success', 'task_complete', 'found', 'starting'
        """
        messages = {
            'error': f"Encountered an issue. {details}" if details else "Hit a snag here.",
            'success': f"Success! {details}" if details else "That worked!",
            'task_complete': f"Finished {details}" if details else "Task complete!",
            'found': f"Found {details}" if details else "Got it!",
            'starting': f"Starting {details}" if details else "Let's begin!"
        }
        
        message = messages.get(milestone_type, details)
        if message:
            return self.speak(message, wait_for_response=False)
        return False

# Global instance for hooks to use
voice = VoiceModeIntegration()

def session_start_greeting():
    """Called on session start"""
    greeting = voice.get_time_based_greeting()
    voice.speak(greeting, wait_for_response=False)
    return True

def pre_tool_announcement(tool_name: str, description: str = ""):
    """Called before tool execution"""
    message = voice.get_tool_announcement(tool_name, description)
    if message:
        voice.speak(message, wait_for_response=False)
    return True

def post_tool_notification(tool_name: str, success: bool):
    """Called after tool execution"""
    message = voice.get_completion_message(tool_name, success)
    if message:
        voice.speak(message, wait_for_response=False)
    return True

def error_notification(error_message: str):
    """Called on errors"""
    # Keep error messages short
    if len(error_message) > 50:
        error_message = "Error occurred. Check output."
    voice.announce_milestone('error', error_message)
    return True

if __name__ == "__main__":
    # Test the voice integration
    print("Testing VoiceMode Integration...")
    
    # Test greeting
    print("1. Testing greeting...")
    session_start_greeting()
    
    # Test tool announcement
    print("2. Testing tool announcement...")
    pre_tool_announcement("Write", "Creating config file")
    
    # Test milestone
    print("3. Testing milestone...")
    voice.announce_milestone('success', 'Configuration complete')
    
    print("\nVoiceMode integration test complete!")
    print("Check log at: /home/marc/.claude/voicemode_hook.log")