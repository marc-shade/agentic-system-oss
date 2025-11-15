#!/usr/bin/env python3
"""
Intelligent Adaptive StatusLine for Claude Code
Uses AI to prioritize and display what's actually important RIGHT NOW

Production-ready implementation that shows:
- Critical issues first (errors, warnings, resource constraints)
- Active work (training, processing, workflows)
- System health (memory, storage, services)
- Context-aware information based on current system state

Integrates with intelligent display agent data collection
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import anthropic

# ANSI color codes for rich terminal display
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class IntelligentStatusLine:
    """Production AI-powered adaptive statusline generator"""

    def __init__(self):
        self.max_length = 150  # Increased to fit all items including token usage
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.use_ai = self.api_key is not None

        if self.use_ai:
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.model = "claude-sonnet-4-20250514"
            except Exception as e:
                print(f"AI initialization failed: {e}", file=sys.stderr)
                self.use_ai = False

    def collect_system_data(self) -> Dict[str, Any]:
        """
        Collect comprehensive system state data
        Mirrors intelligent display agent's data collection
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'hostname': os.uname().nodename
        }

        # Count active agent processes
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=2
            )
            agent_lines = [
                l for l in result.stdout.split('\n')
                if 'python' in l.lower() and 'agent' in l.lower() and 'grep' not in l
            ]
            data['agent_count'] = len(agent_lines)
        except subprocess.TimeoutExpired:
            data['agent_count'] = 0
        except Exception as e:
            data['agent_count'] = 0

        # Claude Code session status
        try:
            sessions_dir = Path.home() / ".claude" / "sessions"
            if sessions_dir.exists():
                data['claude_sessions'] = len(list(sessions_dir.glob("*")))
            else:
                data['claude_sessions'] = 0

            # Check for Claude process using ps (more reliable than pgrep)
            result = subprocess.run(
                ['ps', '-ax'],
                capture_output=True,
                text=True,
                timeout=2
            )
            # Look for process ending with " claude" (exact match to avoid false positives)
            claude_running = any(
                line.strip().endswith(' claude')
                for line in result.stdout.split('\n')
            )
            data['claude_running'] = claude_running
        except Exception:
            data['claude_sessions'] = 0
            data['claude_running'] = False

        # Hook activity detection
        try:
            hooks_dir = Path.home() / ".claude" / "hooks"
            pre_hook = hooks_dir / "pre_tool_use.py"
            post_hook = hooks_dir / "post_tool_use.py"

            # Count active hooks
            active_hooks = 0
            if pre_hook.exists():
                active_hooks += 1
            if post_hook.exists():
                active_hooks += 1

            # Check recent hook activity (last 60 seconds)
            hook_log = Path("/tmp/phoenix_session_start.log")
            recent_hook_activity = False

            if hook_log.exists():
                mod_time = hook_log.stat().st_mtime
                age = datetime.now().timestamp() - mod_time
                if age < 60:
                    recent_hook_activity = True

            data['hook_count'] = active_hooks
            data['recent_hook_activity'] = recent_hook_activity
        except Exception:
            data['hook_count'] = 0
            data['recent_hook_activity'] = False

        # MCP server configuration
        try:
            claude_json = Path.home() / ".claude.json"
            if claude_json.exists():
                with open(claude_json, 'r') as f:
                    config = json.load(f)
                    data['mcp_count'] = len(config.get('mcpServers', {}))
            else:
                data['mcp_count'] = 0
        except json.JSONDecodeError:
            data['mcp_count'] = 0
        except Exception:
            data['mcp_count'] = 0

        # Temporal workflow engine status
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'temporal'],
                capture_output=True,
                text=True,
                timeout=1
            )
            data['temporal_running'] = bool(result.stdout.strip())
        except Exception:
            data['temporal_running'] = False

        # AutoKitteh event-driven automation status
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'autokitteh'],
                capture_output=True,
                text=True,
                timeout=1
            )
            data['autokitteh_running'] = bool(result.stdout.strip())
        except Exception:
            data['autokitteh_running'] = False

        # Recent error detection from logs
        data['recent_errors'] = self._check_recent_errors()

        # Self-healing system status
        data['self_healing'] = self._check_self_healing_status()

        # Session duration (safe file-based tracking)
        data['session_duration'] = self._get_session_duration()

        # Token usage estimation (safe metadata-based tracking)
        data['token_usage'] = self._get_token_usage()

        # MLX machine learning training detection
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=2
            )
            mlx_lines = [l for l in result.stdout.split('\n') if 'mlx' in l.lower() and 'python' in l]
            data['mlx_training'] = len(mlx_lines) > 0
        except Exception:
            data['mlx_training'] = False

        # Memory pressure (macOS vm_stat)
        data['memory_pressure'] = self._check_memory_pressure()

        # Storage usage on hot tier
        data['storage_usage'] = self._check_storage_usage()

        # Current working directory for context
        data['cwd'] = os.path.basename(os.getcwd())

        # Active Claude Code skill detection
        data['active_skill'] = self._detect_active_skill()

        # Current model detection
        data['model'] = self._detect_current_model()

        # Enhanced memory system activity
        data['memory_status'] = self._check_memory_activity()

        return data

    def _check_recent_errors(self) -> int:
        """Scan recent logs for error conditions (last 5 minutes only)"""
        error_count = 0
        from datetime import datetime, timedelta
        import re

        # Only count errors from last 5 minutes
        cutoff_time = datetime.now() - timedelta(minutes=5)

        log_paths = [
            Path("/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log"),
            Path("/tmp/phoenix_session_start.log")
        ]

        for log_path in log_paths:
            if not log_path.exists():
                continue

            try:
                with open(log_path, 'r') as f:
                    # Check last 100 lines for recent errors
                    lines = f.readlines()[-100:]

                    for line in lines:
                        if 'ERROR' not in line and 'CRITICAL' not in line and 'FATAL' not in line:
                            continue

                        # Parse timestamp (format: 2025-11-07 11:18:04,872)
                        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if not timestamp_match:
                            continue

                        try:
                            timestamp_str = timestamp_match.group(1)
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                            # Only count if within last 5 minutes
                            if log_time >= cutoff_time:
                                error_count += 1
                        except ValueError:
                            continue

            except Exception:
                continue

        return error_count

    def _check_self_healing_status(self) -> Dict[str, Any]:
        """Check autonomous self-healing system status"""
        status_file = Path('/tmp/self_healing_status.json')
        default_status = {
            'state': 'idle',
            'error_count': 0,
            'healing_count': 0,
            'fixed_count': 0,
            'message': '',
            'active': False
        }

        if not status_file.exists():
            return default_status

        try:
            with open(status_file, 'r') as f:
                status = json.load(f)

                # Check if status is stale (>10 minutes old)
                if 'last_update' in status:
                    from datetime import datetime
                    last_update = datetime.fromisoformat(status['last_update'])
                    age_seconds = (datetime.now() - last_update).total_seconds()
                    if age_seconds > 600:  # 10 minutes
                        return default_status

                # Mark as active if not idle
                status['active'] = status.get('state', 'idle') != 'idle'
                return status
        except Exception:
            return default_status

    def _get_session_duration(self) -> str:
        """Get Claude Code session duration from timestamp file (production-safe)"""
        try:
            from datetime import datetime
            session_file = Path('/tmp/claude_session_start.json')

            if not session_file.exists():
                return ''

            with open(session_file, 'r') as f:
                data = json.load(f)
                start_time_str = data.get('start_time')

                if not start_time_str:
                    return ''

                start_time = datetime.fromisoformat(start_time_str)
                elapsed = datetime.now() - start_time
                total_seconds = int(elapsed.total_seconds())

                # Format as HH:MM or MM:SS depending on duration
                if total_seconds < 3600:  # Less than 1 hour
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    return f"{minutes}:{seconds:02d}"
                else:  # 1 hour or more
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    return f"{hours}h{minutes:02d}m"

        except Exception:
            return ''

    def _get_token_usage(self) -> Dict[str, Any]:
        """Get Claude Code token usage estimation (production-safe)"""
        try:
            # Import the token estimator utility
            import sys
            sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
            from token_estimator import estimate_token_usage

            usage = estimate_token_usage()
            if usage:
                return {
                    'current': usage['current'],
                    'limit': usage['limit'],
                    'percentage': usage['percentage']
                }
            return {}
        except Exception:
            return {}

    def _check_memory_pressure(self) -> str:
        """Check system memory pressure"""
        try:
            result = subprocess.run(
                ['vm_stat'],
                capture_output=True,
                text=True,
                timeout=2
            )

            # Parse vm_stat output
            output = result.stdout
            if 'Pages free' in output:
                # Extract free pages (simplified)
                for line in output.split('\n'):
                    if 'Pages free' in line:
                        free_pages = int(line.split(':')[1].strip().rstrip('.'))
                        # macOS page size is 4096 bytes
                        free_mb = (free_pages * 4096) / (1024 * 1024)
                        if free_mb < 500:
                            return 'high'
                        elif free_mb < 2000:
                            return 'moderate'
                        else:
                            return 'normal'

            return 'normal'
        except Exception:
            return 'unknown'

    def _check_storage_usage(self) -> int:
        """Check storage usage percentage on hot tier"""
        try:
            hot_tier = Path("/Volumes/SSDRAID0/agentic-system")
            if not hot_tier.exists():
                return 0

            result = subprocess.run(
                ['df', '-h', str(hot_tier)],
                capture_output=True,
                text=True,
                timeout=2
            )

            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    usage_str = parts[4].rstrip('%')
                    return int(usage_str)

            return 0
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            return 0
        except Exception:
            return 0

    def _detect_active_skill(self) -> Optional[str]:
        """
        Detect active Claude Code skill
        Checks for .active_skill indicator file
        """
        try:
            active_skill_file = Path.home() / ".claude" / ".active_skill"
            if not active_skill_file.exists():
                return None

            mod_time = active_skill_file.stat().st_mtime
            age_seconds = datetime.now().timestamp() - mod_time

            if age_seconds > 120:  # Older than 2 minutes
                return None

            with open(active_skill_file, 'r') as f:
                skill_data = json.load(f)
                return skill_data.get('name')

        except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
            return None

    def _detect_current_model(self) -> str:
        """
        Detect current Claude model being used
        Checks environment variable, settings, or defaults to sonnet-4.5
        """
        try:
            # Check environment variable
            model_env = os.environ.get('ANTHROPIC_MODEL', '')
            if model_env:
                # Simplify model name (e.g., claude-sonnet-4-5-20250929 -> sonnet-4.5)
                if 'sonnet-4-5' in model_env or 'sonnet-4.5' in model_env:
                    return 'sonnet-4.5'
                elif 'sonnet-4' in model_env:
                    return 'sonnet-4'
                elif 'opus' in model_env:
                    return 'opus'
                elif 'haiku' in model_env:
                    return 'haiku'
                return model_env.split('-')[-1][:8]  # Last part, max 8 chars

            # Check settings file
            settings_file = Path.home() / ".claude" / "settings.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    model_setting = settings.get('model', '')
                    if model_setting:
                        if 'sonnet-4-5' in model_setting or 'sonnet-4.5' in model_setting:
                            return 'sonnet-4.5'
                        elif 'sonnet-4' in model_setting:
                            return 'sonnet-4'
                        elif 'opus' in model_setting:
                            return 'opus'
                        elif 'haiku' in model_setting:
                            return 'haiku'

            # Default to sonnet-4.5 (current default for Claude Code)
            return 'sonnet-4.5'

        except Exception:
            return 'sonnet-4.5'

    def _check_memory_activity(self) -> Dict[str, Any]:
        """Check enhanced memory system activity (4-tier memory)"""
        try:
            result = subprocess.run(
                ['/tmp/memory-status-check.sh'],
                capture_output=True,
                text=True,
                timeout=2
            )

            status_output = result.stdout.strip()

            # Parse output: 🧠💤10 -> {"icon": "💤", "count": 10, "active": False}
            if status_output.startswith('🧠'):
                icon = status_output[2:4]  # Get emoji after 🧠
                try:
                    count = int(status_output[4:])  # Get number
                except ValueError:
                    count = 0

                is_active = icon == '🔄'
                is_recent = icon == '📥'

                return {
                    "status": "ok",
                    "icon": icon,
                    "count": count,
                    "active": is_active,
                    "recent_pull": is_recent,
                    "display": status_output
                }
            else:
                return {"status": "error", "display": "🧠❌"}

        except Exception:
            return {"status": "error", "display": "🧠❌"}

    def ai_prioritize_display(self, data: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        """
        Use Claude AI to intelligently prioritize statusline content

        Returns: List of (emoji, text, priority) tuples
        Priority levels: 0=critical, 1=high, 2=normal, 3=low
        """

        if not self.use_ai:
            return self._rule_based_prioritize(data)

        context_prompt = f"""Analyze this agentic system state and create a statusline with ALL useful information.

System Data:
{json.dumps(data, indent=2)}

Prioritization Rules:
1. Errors/critical issues: Always show first (priority 0)
2. Resource warnings (memory, storage): High priority (priority 1)
3. Active work (training, workflows, active_skill): High priority (priority 1)
4. Service status changes: Important if down (priority 1)
5. Normal operations (agents, Claude with hooks, MCP): Medium priority (priority 2)
6. Background services running: Low priority (priority 3)

MANDATORY ITEMS (include ALL of these):
1. memory_status: ALWAYS show display field (e.g., "🧠🔄11" if active, "🧠💤11" if idle)
   - Priority 1 if active (🔄) or recent_pull (📥)
   - Priority 2 if idle (💤)
2. mcp_count: ALWAYS show (e.g., "🔌 7mcp") with priority 2
3. agent_count with normal priority (2) if > 0 (e.g., "🤖 18agents")
4. claude_running: show "💻 active" if true with priority 2 (NOT 🧠, that's memory!)
5. temporal_running: show "⏰" if true with priority 3
6. autokitteh_running: show "🐈" if true with priority 3
7. current model (e.g., "🧬 sonnet-4.5") with priority 3
8. current directory (e.g., "📁 agentic-system") with priority 3
9. If active_skill present, show it with priority 1 (e.g., "⚡ skill-name")
10. If memory_pressure is moderate/high, show it with priority 1 (e.g., "⚠️ high memory")

CONDITIONAL ITEMS (only show if abnormal):
- Hooks: ONLY if != 2 (e.g., "⚠️ 0hooks!" or "⚠️ 3hooks?")
- MCP: ONLY if < 6 or > 10 (e.g., "⚠️ 3mcp low!")
- Self-Healing: Show dynamic state based on self_healing.state:
  * analyzing: "🔍 Analyzing..." (priority 1)
  * healing: "🔧 Fixing N" where N is error_count (priority 1)
  * completed: "✅ N fixed!" where N is fixed_count (priority 2, celebratory)
  * idle with errors: "❌ N errors" (priority 0)
  * idle without errors: don't show
- Services down: ONLY if temporal/autokitteh down

Keep total under 120 characters. Use all available space for useful info.

Return JSON array of items:
[
  {{"emoji": "❌", "text": "3 errors", "priority": 0}},
  {{"emoji": "🔥", "text": "MLX training", "priority": 1}},
  {{"emoji": "🤖", "text": "19 agents", "priority": 2}}
]

Priority meanings:
- 0: Critical (display in red)
- 1: High importance (display in yellow)
- 2: Normal status (display in green)
- 3: Background info (display in gray)
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": context_prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text.strip()

            items = json.loads(json_str)

            # Validate and convert to tuples
            result = []
            for item in items:
                if all(key in item for key in ['emoji', 'text', 'priority']):
                    result.append((item['emoji'], item['text'], item['priority']))

            if not result:
                # AI returned invalid format - use rules
                return self._rule_based_prioritize(data)

            return result

        except (json.JSONDecodeError, anthropic.APIError, Exception) as e:
            print(f"AI prioritization failed: {e}", file=sys.stderr)
            return self._rule_based_prioritize(data)

    def _rule_based_prioritize(self, data: Dict[str, Any]) -> List[Tuple[str, str, int]]:
        """Production rule-based prioritization (fallback when AI unavailable)"""
        items = []

        # Critical: Dynamic self-healing status
        self_healing = data.get('self_healing', {})
        healing_state = self_healing.get('state', 'idle')

        if healing_state == 'analyzing':
            # Show analyzing state (high priority)
            items.append(('🔍', 'Analyzing...', 1))
        elif healing_state == 'healing':
            # Show active healing (high priority)
            healing_count = self_healing.get('error_count', 0)
            items.append(('🔧', f"Fixing {healing_count}", 1))
        elif healing_state == 'completed':
            # Show success briefly (normal priority - celebratory)
            fixed_count = self_healing.get('fixed_count', 0)
            items.append(('✅', f"{fixed_count} fixed!", 2))
        else:
            # Idle state - only show if errors exist
            error_count = data.get('recent_errors', 0)
            if error_count > 0:
                items.append(('❌', f"{error_count} errors", 0))

        # High: Memory pressure
        if data.get('memory_pressure') == 'high':
            items.append(('⚠️', 'High memory', 1))

        # High: Storage warning
        storage_usage = data.get('storage_usage', 0)
        if storage_usage > 90:
            items.append(('💾', f"{storage_usage}% full", 0))
        elif storage_usage > 80:
            items.append(('💾', f"{storage_usage}% used", 1))

        # Memory system status - ALWAYS show
        memory_status = data.get('memory_status', {})
        if memory_status.get('status') == 'ok':
            display = memory_status.get('display', '🧠❓')
            priority = 1 if memory_status.get('active') or memory_status.get('recent_pull') else 2
            # Add just the compact status (already has emoji)
            items.append(('', display, priority))  # Empty emoji since display includes it
        else:
            items.append(('🧠', '❌', 0))  # Memory system error

        # High: Active ML training
        if data.get('mlx_training'):
            items.append(('🔥', 'MLX training', 1))

        # High: Active Claude Code skill
        active_skill = data.get('active_skill')
        if active_skill:
            items.append(('⚡', f"skill:{active_skill}", 1))

        # High: Critical services down
        if not data.get('temporal_running'):
            items.append(('⚠️', 'Temporal down', 1))
        if not data.get('autokitteh_running'):
            items.append(('⚠️', 'AK down', 1))

        # Normal: Agent activity
        agent_count = data.get('agent_count', 0)
        if agent_count > 0:
            items.append(('🤖', f"{agent_count}agents", 2))

        # Normal: Claude Code status (only show hook info if abnormal)
        if data.get('claude_running'):
            hook_count = data.get('hook_count', 0)
            expected_hooks = 2  # Normal state

            # Only show hook count if it's different from expected
            if hook_count != expected_hooks:
                items.append(('⚠️', f"{hook_count}hooks!", 1))  # High priority warning

            # Show session duration if available
            session_duration = data.get('session_duration', '')
            if session_duration:
                items.append(('💻', f"{session_duration}", 2))  # Session duration
            else:
                items.append(('💻', 'active', 2))  # Changed from 🧠 to avoid confusion with memory

            # Show token usage if available
            token_usage = data.get('token_usage', {})
            if token_usage and token_usage.get('current'):
                current = token_usage['current']
                limit = token_usage['limit']
                percentage = token_usage['percentage']

                # Format with k suffix for readability
                current_k = f"{current // 1000}k" if current >= 1000 else str(current)
                limit_k = f"{limit // 1000}k"

                items.append(('📊', f"{current_k}/{limit_k} ({percentage}%)", 2))
        else:
            items.append(('💻', 'idle', 2))

        # Normal: MCP configuration (ALWAYS show)
        mcp_count = data.get('mcp_count', 0)
        expected_mcp_min = 6
        expected_mcp_max = 10

        if mcp_count < expected_mcp_min:
            items.append(('⚠️', f"{mcp_count}mcp low!", 1))  # Warning - too few
        elif mcp_count > expected_mcp_max:
            items.append(('⚠️', f"{mcp_count}mcp high!", 1))  # Warning - too many
        else:
            items.append(('🔌', f"{mcp_count}mcp", 2))  # Normal - always show count

        # Workflow engines - removed from display per user request
        # (Status still checked in _collect_system_data but not shown on statusline)

        # Low: Current model for context
        model = data.get('model', 'sonnet-4.5')
        items.append(('🧬', model, 3))

        # Low: Current working directory for context
        cwd = data.get('cwd', 'unknown')
        items.append(('📁', cwd, 3))

        return items

    def format_statusline(self, items: List[Tuple[str, str, int]], use_colors: bool = True) -> str:
        """
        Format prioritized items into compact statusline with color coding

        Args:
            items: List of (emoji, text, priority) tuples
            use_colors: Whether to apply ANSI color codes

        Returns:
            Formatted statusline string
        """

        # Sort by priority (0=critical first, then 1, 2, 3)
        items.sort(key=lambda x: x[2])

        parts = []
        current_length = 0

        for emoji, text, priority in items:
            # Format text - handle empty text (emoji-only display)
            if text:
                formatted = f"{emoji} {text}"
            else:
                formatted = emoji

            # Apply color based on priority
            if use_colors:
                if priority == 0:  # Critical
                    colored_text = f"{Colors.RED}{formatted}{Colors.RESET}"
                elif priority == 1:  # High
                    colored_text = f"{Colors.YELLOW}{formatted}{Colors.RESET}"
                elif priority == 2:  # Normal
                    colored_text = f"{Colors.GREEN}{formatted}{Colors.RESET}"
                else:  # Low priority
                    colored_text = f"{Colors.WHITE}{formatted}{Colors.RESET}"
            else:
                colored_text = formatted

            # Calculate display length (without color codes)
            display_length = len(formatted)

            # Check length constraint
            separator_length = 3  # " | "
            if current_length + display_length + separator_length > self.max_length:
                break

            parts.append(colored_text)
            current_length += display_length + separator_length

        return " | ".join(parts)

    def generate(self) -> str:
        """
        Generate intelligent adaptive statusline

        Returns:
            Formatted statusline string with colors
        """
        try:
            # Collect comprehensive system data
            data = self.collect_system_data()

            # Use AI to prioritize what's important
            items = self.ai_prioritize_display(data)

            # Format with colors
            statusline = self.format_statusline(items, use_colors=True)

            return statusline

        except Exception as e:
            # Robust fallback for any unexpected errors
            print(f"Statusline generation error: {e}", file=sys.stderr)
            cwd = os.path.basename(os.getcwd())
            return f"🤖 Agentic System | 📁 {cwd}"


def main():
    """Command-line interface for intelligent statusline"""
    statusline = IntelligentStatusLine()
    output = statusline.generate()
    print(output)


if __name__ == "__main__":
    main()
