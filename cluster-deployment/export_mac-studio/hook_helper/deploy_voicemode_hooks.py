#!/usr/bin/env python3
"""
Deploy VoiceMode Hooks and Clean Up Old Voice Systems
"""

import os
import shutil
import json
import subprocess
from datetime import datetime

def backup_file(filepath):
    """Create backup of file before modifying"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(filepath, backup_path)
        print(f"✓ Backed up {os.path.basename(filepath)}")
        return backup_path
    return None

def clean_old_voice_references():
    """Remove or update files with old voice system references"""
    hooks_dir = "/Users/marc/.claude/hooks"
    old_systems = ["unified-voice-mcp", "unified_voice", "siobhan_voice", "universal_voice"]
    
    print("\n🧹 Cleaning old voice system references...")
    
    # Files to update
    files_to_check = [
        "ux/voice_greeting_hook.py",
        "ux/voice_notifier_hook.py", 
        "ux/voice_summary_hook.py",
        "ux/voice_notification.py",
        "notification/voice_notification.py",
        "voice_usage_checker.py"
    ]
    
    for file_path in files_to_check:
        full_path = os.path.join(hooks_dir, file_path)
        if os.path.exists(full_path):
            # Backup and disable old voice hooks
            backup_file(full_path)
            
            # Rename to .disabled to prevent execution
            disabled_path = f"{full_path}.disabled"
            os.rename(full_path, disabled_path)
            print(f"✓ Disabled old hook: {file_path}")

def deploy_voicemode_hooks():
    """Deploy the new VoiceMode hooks"""
    hooks_dir = "/Users/marc/.claude/hooks"
    
    print("\n🚀 Deploying VoiceMode hooks...")
    
    # 1. Check if voicemode_integration.py exists
    integration_path = os.path.join(hooks_dir, "voicemode_integration.py")
    if not os.path.exists(integration_path):
        print("❌ voicemode_integration.py not found!")
        return False
    
    # 2. Update pre-tool-use hook
    pre_tool_path = os.path.join(hooks_dir, "pre-tool-use.py")
    pre_tool_vm_path = os.path.join(hooks_dir, "pre-tool-use-voicemode.py")
    
    if os.path.exists(pre_tool_vm_path):
        backup_file(pre_tool_path)
        shutil.copy2(pre_tool_vm_path, pre_tool_path)
        print("✓ Updated pre-tool-use.py with VoiceMode")
    
    # 3. Deploy post-tool-use hook
    post_tool_path = os.path.join(hooks_dir, "post-tool-use")
    post_tool_vm_path = os.path.join(hooks_dir, "post-tool-use-voicemode.py")
    
    if os.path.exists(post_tool_vm_path):
        backup_file(post_tool_path)
        shutil.copy2(post_tool_vm_path, post_tool_path)
        # Make executable
        os.chmod(post_tool_path, 0o755)
        print("✓ Deployed post-tool-use with VoiceMode")
    
    # 4. Verify session-start.py has VoiceMode
    session_start_path = os.path.join(hooks_dir, "session-start.py")
    if os.path.exists(session_start_path):
        with open(session_start_path, 'r') as f:
            content = f.read()
            if "voicemode_integration" in content:
                print("✓ session-start.py already has VoiceMode")
            else:
                print("⚠️  session-start.py needs VoiceMode integration")
    
    return True

def test_voicemode():
    """Test VoiceMode functionality"""
    print("\n🧪 Testing VoiceMode...")
    
    try:
        # Test the integration module
        import sys
        sys.path.append('/Users/marc/.claude/hooks')
        from voicemode_integration import voice
        
        # Test speaking
        success = voice.speak("VoiceMode hooks deployed successfully!", wait_for_response=False)
        
        if success:
            print("✓ VoiceMode test successful!")
            return True
        else:
            print("⚠️  VoiceMode test failed - check configuration")
            return False
            
    except Exception as e:
        print(f"❌ VoiceMode test error: {e}")
        return False

def update_claude_md():
    """Update CLAUDE.md to reflect VoiceMode hooks"""
    claude_md_path = "/Users/marc/.claude/CLAUDE.md"
    
    print("\n📝 Updating CLAUDE.md...")
    
    if os.path.exists(claude_md_path):
        with open(claude_md_path, 'r') as f:
            content = f.read()
        
        # Check if already updated
        if "VoiceMode hooks provide automatic voice feedback" not in content:
            # Find hooks section and add VoiceMode info
            hooks_section = """
## VOICEMODE HOOKS (ACTIVE)
**Automatic voice feedback during work sessions:**

- **SessionStart**: Greets you with time-aware message using free Silero TTS
- **PreToolUse**: Announces important operations (file creation, agent spawning, etc.)
- **PostToolUse**: Notifies completion of significant tasks
- **Milestones**: Speaks at key points (errors, successes, task completion)

**Voice Configuration:**
- TTS: Silero (FREE - no API costs)
- STT: OpenAI Whisper (minimal cost)
- Hooks Path: `/Users/marc/.claude/hooks/voicemode_integration.py`
"""
            
            # Insert after HOOKS SYSTEM ACTIVE section
            if "## HOOKS SYSTEM ACTIVE" in content:
                content = content.replace("## HOOKS SYSTEM ACTIVE", 
                                         "## HOOKS SYSTEM ACTIVE" + hooks_section)
                
                backup_file(claude_md_path)
                with open(claude_md_path, 'w') as f:
                    f.write(content)
                print("✓ Updated CLAUDE.md with VoiceMode hooks info")
            else:
                print("⚠️  Could not find HOOKS section in CLAUDE.md")
    else:
        print("⚠️  CLAUDE.md not found")

def main():
    print("=" * 50)
    print("VoiceMode Hooks Deployment")
    print("=" * 50)
    
    # 1. Clean old voice systems
    clean_old_voice_references()
    
    # 2. Deploy new VoiceMode hooks
    if deploy_voicemode_hooks():
        # 3. Test VoiceMode
        test_voicemode()
        
        # 4. Update documentation
        update_claude_md()
        
        print("\n" + "=" * 50)
        print("✅ VoiceMode hooks deployment complete!")
        print("\nVoiceMode will now:")
        print("  • Greet you when sessions start")
        print("  • Announce important operations")
        print("  • Notify task completions")
        print("  • Speak at key milestones")
        print("\nUsing FREE Silero TTS - no API costs!")
        print("=" * 50)
    else:
        print("\n❌ Deployment failed - check errors above")

if __name__ == "__main__":
    main()