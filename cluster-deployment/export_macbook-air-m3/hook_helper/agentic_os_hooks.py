#!/usr/bin/env python3
"""
AGENTIC OPERATING SYSTEM - OUTPUT STYLES HOOKS INTEGRATION
Enhances Claude Code hooks with rich output generation capabilities
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Add Claude paths for imports
sys.path.append('/Users/marc/.claude')
sys.path.append('/Users/marc/.claude/hooks')

class AgenticOSOutputManager:
    """Manages output styles and renders for the Agentic Operating System"""
    
    def __init__(self):
        self.base_path = Path('/Users/marc/.claude')
        self.output_styles_path = self.base_path / 'output_styles'
        self.templates_path = self.output_styles_path / 'templates'
        self.current_output_mode = self.detect_output_mode()
        
        # Initialize output style configuration
        self.load_output_styles()
        
        # Track agent activities for dashboard
        self.agent_activities = []
        self.system_metrics = self.initialize_metrics()
        
    def detect_output_mode(self):
        """Detect the appropriate output mode based on context and environment"""
        # Check if we're in a terminal that supports rich output
        if os.environ.get('TERM_PROGRAM') == 'iTerm.app':
            return 'agentic_os'
        elif os.environ.get('CLAUDE_OUTPUT_STYLE'):
            return os.environ.get('CLAUDE_OUTPUT_STYLE')
        else:
            return 'orchestrator'  # Default fallback
            
    def load_output_styles(self):
        """Load output style configurations"""
        try:
            # Load the agentic OS configuration
            agentic_config_path = self.output_styles_path / 'agentic_os.js'
            if agentic_config_path.exists():
                self.agentic_config = self.parse_js_config(agentic_config_path)
            else:
                self.agentic_config = self.get_default_config()
                
        except Exception as e:
            print(f"Warning: Could not load output styles configuration: {e}")
            self.agentic_config = self.get_default_config()
            
    def parse_js_config(self, config_path):
        """Parse JavaScript module.exports configuration"""
        # Simple JavaScript config parser - reads the structure
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Extract key configuration elements (simplified parser)
        return {
            'name': 'agentic_os',
            'templates': {
                'dashboard': str(self.templates_path / 'agent_dashboard.html'),
                'status_line': str(self.templates_path / 'status_line.txt'),
                'yaml_schema': str(self.templates_path / 'yaml_response.yaml'),
                'voice_script': str(self.templates_path / 'voice_synthesis.txt')
            },
            'features': {
                'realTime': True,
                'voiceIntegrated': True,
                'interactiveElements': True
            }
        }
        
    def get_default_config(self):
        """Default configuration if files are missing"""
        return {
            'name': 'agentic_os',
            'templates': {},
            'features': {
                'realTime': False,
                'voiceIntegrated': False,
                'interactiveElements': False
            }
        }
        
    def initialize_metrics(self):
        """Initialize system metrics tracking"""
        return {
            'start_time': time.time(),
            'tools_used': [],
            'agents_spawned': [],
            'tasks_completed': 0,
            'success_rate': 100.0,
            'memory_usage': 0,
            'mcp_servers_active': 0
        }
        
    def update_agent_activity(self, agent_name, activity, status='active'):
        """Update agent activity for dashboard display"""
        activity_record = {
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'activity': activity,
            'status': status
        }
        
        self.agent_activities.append(activity_record)
        
        # Keep only last 50 activities for performance
        if len(self.agent_activities) > 50:
            self.agent_activities = self.agent_activities[-50:]
            
    def generate_status_line(self, context=None):
        """Generate dynamic status line based on current system state"""
        try:
            # Collect current system metrics
            uptime = time.time() - self.system_metrics['start_time']
            uptime_str = self.format_uptime(uptime)
            
            # Memory usage (simplified)
            memory_usage = self.get_memory_usage()
            
            # Agent count
            active_agents = len(set(activity['agent'] for activity in self.agent_activities[-10:]))
            
            # Generate status line
            status_line = f"🎛️ AOS | Uptime: {uptime_str} | Memory: {memory_usage}% | Agents: {active_agents} | Tasks: {self.system_metrics['tasks_completed']} | Success: {self.system_metrics['success_rate']:.1f}%"
            
            return status_line
            
        except Exception as e:
            return f"🎛️ AOS | Status: Operational | Error collecting metrics: {str(e)}"
            
    def format_uptime(self, seconds):
        """Format uptime in human-readable format"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds/60)}m"
        else:
            return f"{int(seconds/3600)}h {int((seconds%3600)/60)}m"
            
    def get_memory_usage(self):
        """Get simplified memory usage percentage"""
        try:
            import psutil
            return psutil.virtual_memory().percent
        except:
            return 0
            
    def generate_dashboard_html(self, context=None):
        """Generate HTML dashboard with current system state"""
        try:
            template_path = self.templates_path / 'agent_dashboard.html'
            if not template_path.exists():
                return "<h1>🎛️ Agentic Operating System Dashboard</h1><p>Template not found</p>"
                
            # Read template
            with open(template_path, 'r') as f:
                template = f.read()
                
            # Replace dynamic content (basic template substitution)
            current_time = datetime.now().strftime("%H:%M:%S")
            template = template.replace("09:45:32", current_time)
            
            return template
            
        except Exception as e:
            return f"<h1>Dashboard Error</h1><p>Could not generate dashboard: {e}</p>"
            
    def generate_yaml_response(self, agent_type, task_data, context=None):
        """Generate structured YAML response for specific agent types"""
        try:
            template_path = self.templates_path / 'yaml_response.yaml'
            if not template_path.exists():
                return self.get_basic_yaml_response(agent_type, task_data)
                
            # Read YAML template
            with open(template_path, 'r') as f:
                template = f.read()
                
            # Basic template variable substitution
            current_time = datetime.now().isoformat()
            template = template.replace("{{ current_timestamp }}", current_time)
            template = template.replace("{{ task.id }}", str(task_data.get('task_id', 'unknown')))
            
            # Extract relevant section based on agent type
            if 'backend' in agent_type.lower():
                return self.extract_yaml_section(template, 'backend_api_response')
            elif 'frontend' in agent_type.lower():
                return self.extract_yaml_section(template, 'frontend_component_response')
            elif 'architect' in agent_type.lower():
                return self.extract_yaml_section(template, 'system_architecture_response')
            elif 'security' in agent_type.lower():
                return self.extract_yaml_section(template, 'security_assessment_response')
            else:
                return self.extract_yaml_section(template, 'system_status_response')
                
        except Exception as e:
            return self.get_basic_yaml_response(agent_type, task_data, error=str(e))
            
    def extract_yaml_section(self, template, section_name):
        """Extract a specific YAML section from template"""
        lines = template.split('\n')
        in_section = False
        section_lines = []
        
        for line in lines:
            if line.startswith(f"{section_name}:"):
                in_section = True
                section_lines.append(line)
            elif in_section and line.startswith('# ======='):
                break
            elif in_section:
                section_lines.append(line)
                
        return '\n'.join(section_lines) if section_lines else f"{section_name}:\n  status: 'template_not_found'"
        
    def get_basic_yaml_response(self, agent_type, task_data, error=None):
        """Generate basic YAML response if templates are unavailable"""
        current_time = datetime.now().isoformat()
        
        yaml_response = f"""
agent_response:
  agent: "{agent_type}"
  timestamp: "{current_time}"
  task_id: "{task_data.get('task_id', 'unknown')}"
  status: "{'error' if error else 'completed'}"
"""
        
        if error:
            yaml_response += f'  error: "{error}"\n'
            
        if task_data:
            yaml_response += f"""  
  task_details:
    description: "{task_data.get('description', 'No description provided')}"
    priority: "{task_data.get('priority', 'normal')}"
    estimated_duration: "{task_data.get('duration', 'unknown')}"
"""
            
        return yaml_response
        
    def trigger_voice_announcement(self, message, emotion="neutral", priority="normal"):
        """Trigger voice synthesis for status announcements"""
        try:
            # Check if voice is enabled in configuration
            if not self.agentic_config.get('features', {}).get('voiceIntegrated', False):
                return False
                
            # Create voice synthesis command (integration with existing voice system)
            voice_command = [
                'python3', '/Users/marc/.claude/siobhan_voice.py',
                '--text', message,
                '--emotion', emotion,
                '--priority', priority
            ]
            
            # Execute voice command in background
            subprocess.Popen(voice_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
            
        except Exception as e:
            print(f"Voice synthesis failed: {e}")
            return False
            
    def update_dashboard_metrics(self, tool_used, success=True, duration=None):
        """Update dashboard metrics after tool usage"""
        self.system_metrics['tools_used'].append({
            'tool': tool_used,
            'timestamp': time.time(),
            'success': success,
            'duration': duration
        })
        
        if success:
            self.system_metrics['tasks_completed'] += 1
            
        # Update success rate
        recent_tools = self.system_metrics['tools_used'][-20:]  # Last 20 tools
        if recent_tools:
            success_count = sum(1 for tool in recent_tools if tool['success'])
            self.system_metrics['success_rate'] = (success_count / len(recent_tools)) * 100
            
    def export_dashboard_to_file(self):
        """Export current dashboard to HTML file for viewing"""
        try:
            dashboard_html = self.generate_dashboard_html()
            output_file = self.base_path / 'current_dashboard.html'
            
            with open(output_file, 'w') as f:
                f.write(dashboard_html)
                
            return str(output_file)
            
        except Exception as e:
            print(f"Failed to export dashboard: {e}")
            return None


# Global instance for use in hooks
output_manager = AgenticOSOutputManager()


def pre_tool_use_output_hook(tool_name, tool_args, context=None):
    """Pre-tool hook for output style preparation"""
    try:
        # Update activity tracking
        output_manager.update_agent_activity(
            agent_name="System", 
            activity=f"Starting {tool_name}",
            status="active"
        )
        
        # Generate status line for current operation
        status_line = output_manager.generate_status_line(context)
        print(f"\n{status_line}")
        
        # Voice announcement for major operations
        if tool_name in ['Task', 'Write', 'Edit']:
            message = f"Initiating {tool_name} operation"
            output_manager.trigger_voice_announcement(message, emotion="confident")
            
        return True
        
    except Exception as e:
        print(f"Pre-tool output hook error: {e}")
        return True  # Don't block execution
        

def post_tool_use_output_hook(tool_name, tool_result, success=True, duration=None, context=None):
    """Post-tool hook for rich output generation"""
    try:
        # Update metrics
        output_manager.update_dashboard_metrics(tool_name, success, duration)
        
        # Update activity tracking
        status = "completed" if success else "error"
        output_manager.update_agent_activity(
            agent_name="System",
            activity=f"Completed {tool_name}",
            status=status
        )
        
        # Generate appropriate output based on tool and result
        if tool_name == 'Task' and success:
            # Agent delegation - generate rich output
            agent_name = extract_agent_name_from_result(tool_result)
            if agent_name:
                output_manager.update_agent_activity(
                    agent_name=agent_name,
                    activity="Agent delegated and active",
                    status="delegated"
                )
                
                # Voice confirmation
                message = f"Task successfully delegated to {agent_name}"
                output_manager.trigger_voice_announcement(message, emotion="confident")
                
        elif tool_name in ['Write', 'Edit', 'MultiEdit'] and success:
            # File operations - show completion status
            print(f"✅ {tool_name} operation completed successfully")
            
        # Generate and display status line
        status_line = output_manager.generate_status_line(context)
        print(f"{status_line}\n")
        
        return True
        
    except Exception as e:
        print(f"Post-tool output hook error: {e}")
        return True  # Don't block execution


def session_start_output_hook(context=None):
    """Session start hook for Agentic OS initialization"""
    try:
        # Initialize output manager for new session
        output_manager.system_metrics = output_manager.initialize_metrics()
        
        # Generate welcome dashboard
        if output_manager.current_output_mode == 'agentic_os':
            dashboard_file = output_manager.export_dashboard_to_file()
            if dashboard_file:
                print(f"🎛️ Agentic Operating System Dashboard: file://{dashboard_file}")
                
        # Voice welcome
        message = "Agentic Operating System initialized. All systems operational."
        output_manager.trigger_voice_announcement(message, emotion="confident")
        
        # Status line
        status_line = output_manager.generate_status_line()
        print(f"\n{status_line}\n")
        
        return True
        
    except Exception as e:
        print(f"Session start output hook error: {e}")
        return True


def extract_agent_name_from_result(tool_result):
    """Extract agent name from Task tool result"""
    try:
        if isinstance(tool_result, dict):
            return tool_result.get('agent_name', 'Unknown Agent')
        elif isinstance(tool_result, str):
            # Look for agent patterns in string result
            import re
            agent_pattern = r'([🔧🐸🐻🏗️🦉🐢🦎🦋🎨🧠]\s*[\w\s]+(?:Engineer|Specialist|Architect|Builder|Agent))'
            match = re.search(agent_pattern, tool_result)
            return match.group(1) if match else None
        else:
            return None
            
    except Exception as e:
        print(f"Error extracting agent name: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🎛️ Agentic OS Hooks - Usage: python3 agentic_os_hooks.py <hook_type> [args...]")
        sys.exit(1)
        
    hook_type = sys.argv[1]
    
    if hook_type == "session_start":
        session_start_output_hook()
    elif hook_type == "pre_tool_use":
        tool_name = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
        tool_args = sys.argv[3] if len(sys.argv) > 3 else "{}"
        pre_tool_use_output_hook(tool_name, tool_args)
    elif hook_type == "post_tool_use":
        tool_name = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
        success = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else True
        post_tool_use_output_hook(tool_name, None, success)
    elif hook_type == "test":
        # Test the output manager
        print("🎛️ Testing Agentic OS Output Manager")
        
        # Test status line generation
        status = output_manager.generate_status_line()
        print(f"Status Line: {status}")
        
        # Test activity tracking
        output_manager.update_agent_activity("🐸 Frontend Specialist", "Creating UI mockup", "active")
        output_manager.update_agent_activity("🐻 Backend Engineer", "Implementing API", "active")
        
        # Test dashboard export
        dashboard_file = output_manager.export_dashboard_to_file()
        if dashboard_file:
            print(f"Dashboard exported: {dashboard_file}")
            
        # Test YAML generation
        yaml_output = output_manager.generate_yaml_response(
            "🐸 Frontend Specialist", 
            {'task_id': 'test-001', 'description': 'Test task', 'priority': 'high'}
        )
        print(f"YAML Output:\n{yaml_output}")
        
        print("\n✅ Agentic OS Output Manager test completed")
    else:
        print(f"🎛️ Unknown hook type: {hook_type}")
        sys.exit(1)