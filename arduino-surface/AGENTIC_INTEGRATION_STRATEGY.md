# Arduino Surface - Agentic System Integration Strategy

## Executive Summary

The Arduino Surface transforms from a hardware project into a **Tier0 physical interface layer** that bridges digital AI agents with physical reality. This creates a multi-sensory communication channel that complements voice and screen-based interaction with ambient awareness, physical feedback, and human-in-loop gating.

## Strategic Vision

### The Core Insight
**The Arduino is not output-only - it's a bidirectional physical interface** that:
1. **Shows** agent state to Marc (LCD + LED)
2. **Captures** Marc's decisions (buttons - when wired)
3. **Senses** environmental context (sensors - when wired)
4. **Creates** tangible connection between digital agents and physical world

### Why This Matters
Current AI agents are **screen-bound** - they exist only in terminal windows and chat interfaces. The Arduino Surface makes agent activity **physically present**:
- **Ambient awareness** - Status visible without screen focus
- **Attention hierarchy** - Physical urgency signals (color, sound, motion)
- **Human-in-loop** - Physical approval gates for critical decisions
- **Environmental grounding** - Sensors inform agent behavior

## Communication Philosophy

### Complementary, Not Redundant

**Voice Mode** (Primary communication):
- Detailed information
- Questions and conversations
- Complex explanations
- Waiting for responses

**Screen** (Primary workspace):
- Code, files, terminal output
- Detailed logs and traces
- Multiple concurrent contexts

**Arduino Surface** (Ambient awareness):
- **Persistent current state** (not transient messages)
- **At-a-glance health status** (color coding)
- **Attention-grabbing alerts** (sound + light for critical events)
- **Confirmation of digital operations** (physical feedback loop)

### Design Principles

1. **Persistence Over Transience**
   - LCD shows CURRENT STATE, not scrolling messages
   - Update LCD when state CHANGES
   - LED color reflects CURRENT HEALTH, not momentary events

2. **Attention Hierarchy**
   - **Info**: Blue LED, subtle → "System thinking"
   - **Success**: Green LED + ascending beeps → "Task complete"
   - **Warning**: Yellow LED + mid beeps + LCD details → "Needs attention"
   - **Error**: Red LED + descending beeps + LCD details → "Failure occurred"
   - **Critical**: Flashing red + continuous beeps → "Immediate action required"

3. **Non-Blocking Operations**
   - Arduino updates happen in parallel with main work
   - Timeouts on all operations (don't hang if Arduino disconnects)
   - Graceful degradation if hardware unavailable

4. **Privacy Aware**
   - Never display PII or sensitive data on LCD (visible to room)
   - Timeout and clear sensitive displays
   - Audit all Arduino interactions in enhanced-memory

## Integration Patterns

### Pattern 1: Agent Activity Monitor

**The LCD becomes a persistent dashboard** for the agentic system:

```
LCD Line 1: Current active agent/task
LCD Line 2: Status/progress indicator
LED Color: System health
LED Brightness: Activity level (PWM 0-255)
```

**Example**:
```
LCD: "Agent: Research"
     "Spawning 3 tasks"
LED: Blue (processing)
```

**When task completes**:
```
LCD: "Research: Done"
     "Found 12 sources"
LED: Green + success beeps
Voice: "Research complete. Found 12 sources."
```

### Pattern 2: Ember Violation Enforcement

**Ember (conscience keeper) uses Arduino for physical enforcement**:

When Ember detects a production-policy violation:
```python
surface.lcd_write(0, 0, "VIOLATION")
surface.lcd_write(1, 0, violation_type[:16])  # "Mock UI detected"
surface.set_led(0, 255, 0, 0)  # RED
surface.alert('error')  # Red LED + descending beeps
voice_mode.converse(f"Production violation: {violation_type}", wait_for_response=False)
```

**Visual**: Red LED + error beeps make violations **impossible to ignore**
**Benefit**: Physical reinforcement of production-only policy

### Pattern 3: Human-in-Loop Decision Gates

**For critical operations requiring approval** (after buttons wired):

```python
def request_approval(action, description, timeout=30):
    """Request physical button press approval"""
    surface.lcd_write(0, 0, action[:16])
    surface.lcd_write(1, 0, "Press Confirm")
    surface.set_led(0, 255, 255, 0)  # Yellow warning

    voice_mode.converse(
        f"{description}. Please press Confirm button or Cancel.",
        wait_for_response=False
    )

    event = surface.wait_event(timeout=timeout)

    if event and event['button'] == 'confirm':
        surface.alert('success')
        return True
    else:
        surface.alert('error')
        return False
```

**Use cases**:
- Destructive operations (delete files, drop databases)
- Expensive API calls (>$10 cost)
- System modifications (update configs, restart services)
- Git force push to main/master

**Example**:
```
LCD: "Delete 1000 logs?"
     "Press Confirm"
LED: Yellow (warning)
Voice: "This will delete 1000 log files. Press confirm or cancel."
[Wait for physical button press]
```

### Pattern 4: Multi-Agent Orchestration

**When spawning parallel agents** (Kenny's pattern):

```python
# Before spawning
surface.lcd_write(0, 0, "Spawning Agents")
surface.lcd_write(1, 0, "Count: 3")
surface.set_led(0, 0, 0, 255)  # Blue = processing

# Spawn agents in parallel
agents = [
    Task("research-coordinator", "Research AI tools"),
    Task("web-analyst", "Extract analytics"),
    Task("documentation-researcher", "Create guide")
]

# While agents work - pulse LED to show activity
# (background thread modulates LED brightness)

# On completion
surface.lcd_write(0, 0, "Agents: Done")
surface.lcd_write(1, 0, "All Complete")
surface.alert('success')  # Green + ascending beeps
```

### Pattern 5: Memory State Visualization

**enhanced-memory-mcp status monitoring**:

```python
def update_memory_display():
    status = mcp__enhanced_memory_mcp__get_memory_status()

    entity_count = status['entity_count']
    health = 'healthy' if entity_count < 10000 else 'warning'

    surface.lcd_write(0, 0, f"Memory: {entity_count}")
    surface.lcd_write(1, 0, f"Status: {health}")

    led_color = {
        'healthy': (0, 255, 0),
        'warning': (255, 255, 0),
        'error': (255, 0, 0)
    }[health]

    surface.set_led(0, *led_color)

    # Servo shows utilization (when wired)
    # 0° = empty, 180° = full
    utilization = min(entity_count / 20000.0, 1.0)
    surface.set_servo(int(utilization * 180))
```

### Pattern 6: Cost Tracking & Budget Awareness

**Track expensive operations** (GPT-5 calls, API usage):

```python
def check_cost_approval(estimated_cost):
    """Display cost and request approval for expensive operations"""

    if estimated_cost < 1.0:
        return True  # Auto-approve cheap operations

    surface.lcd_write(0, 0, f"Cost: ${estimated_cost:.2f}")
    surface.lcd_write(1, 0, "Confirm to run")
    surface.set_led(0, 255, 255, 0)  # Yellow warning

    voice_mode.converse(
        f"This operation will cost approximately ${estimated_cost:.2f}. Please confirm.",
        wait_for_response=False
    )

    event = surface.wait_event(timeout=30)
    return event and event['button'] == 'confirm'
```

### Pattern 7: Environmental Context Integration

**Use sensors to inform agent decisions** (after sensors wired):

```python
def get_environmental_context():
    """Read physical environment to inform agent behavior"""
    status = surface.get_status()

    context = {
        'room_temp_c': status['temp_c'],
        'ambient_light': status['light'],
        'time_of_day': 'night' if status['light'] < 100 else 'day',
        'user_activity': check_recent_interaction()
    }

    # Store in enhanced-memory for agent decision-making
    mcp__enhanced_memory_mcp__create_entities([{
        'name': f'environment-{timestamp}',
        'entityType': 'environmental_context',
        'observations': [
            f'temp: {context["room_temp_c"]}°C',
            f'light: {context["ambient_light"]}',
            f'time: {context["time_of_day"]}'
        ]
    }])

    # Agent behavior adjustments
    if context['room_temp_c'] > 30:
        # Hot room - throttle CPU-intensive operations
        return {'processing_mode': 'low_power'}

    if context['time_of_day'] == 'night':
        # Night time - defer non-urgent tasks
        return {'defer_non_urgent': True}

    return context
```

## Technical Implementation

### Approach 1: Background Daemon (Recommended)

**Create persistent status monitor**:

```python
# ~/.claude/daemons/arduino_status_daemon.py

class ArduinoStatusDaemon:
    """Persistent daemon monitoring system state and updating Arduino"""

    def __init__(self, port='/dev/tty.usbmodem8344401'):
        self.surface = ArduinoSurface(port)
        self.surface.connect()
        self.last_state = None
        self.last_update = 0

    def run(self):
        """Main update loop"""
        while True:
            try:
                current_state = self.get_system_state()
                current_time = time.time()

                # Update if state changed or 5 seconds elapsed
                if (current_state != self.last_state or
                    current_time - self.last_update > 5):

                    self.update_display(current_state)
                    self.last_state = current_state
                    self.last_update = current_time

                time.sleep(1)

            except Exception as e:
                print(f"Daemon error: {e}")
                time.sleep(5)

    def get_system_state(self):
        """Read current system state from enhanced-memory, etc."""
        # Query enhanced-memory for recent activity
        recent = mcp__enhanced_memory_mcp__search_nodes(
            query="entityType:agent_activity",
            limit=1
        )

        if recent:
            return {
                'agent': recent[0].get('agent_type', 'Idle'),
                'status': recent[0].get('status', 'Unknown'),
                'health': self.get_system_health()
            }

        return {
            'agent': 'Idle',
            'status': 'Ready',
            'health': 'healthy'
        }

    def get_system_health(self):
        """Determine overall system health"""
        # Check MCP servers, memory status, etc.
        # Return: 'healthy', 'warning', 'error'
        return 'healthy'

    def update_display(self, state):
        """Update LCD and LED based on state"""
        agent = state['agent'][:16]
        status = state['status'][:16]

        self.surface.lcd_write(0, 0, f"Agent: {agent}")
        self.surface.lcd_write(1, 0, f"Stat: {status}")

        led_colors = {
            'healthy': (0, 255, 0),
            'warning': (255, 255, 0),
            'error': (255, 0, 0)
        }

        self.surface.set_led(0, *led_colors[state['health']])
```

**Start daemon on session start**:
```bash
# In ~/.claude/hooks/session-start.sh
python3 ~/.claude/daemons/arduino_status_daemon.py &
echo $! > /tmp/arduino_daemon.pid
```

### Approach 2: Hook Integration

**Update Arduino in existing hooks**:

```python
# In ~/.claude/hooks/post-tool-use.py

def update_arduino_after_tool(tool_name, tool_result, success):
    """Update Arduino display after tool execution"""

    try:
        surface = ArduinoSurface(port)
        surface.connect()

        if tool_name == 'Task':
            # Agent spawned
            surface.lcd_write(1, 0, f"Task: {tool_result[:16]}")
            surface.set_led(0, 0, 0, 255)  # Blue = processing

        elif tool_name in ['Write', 'Edit', 'MultiEdit']:
            # File operation
            if success:
                surface.lcd_write(1, 0, f"{tool_name}: Done")
                surface.set_led(0, 0, 255, 0)  # Green
            else:
                surface.set_led(0, 255, 0, 0)  # Red

        elif tool_name == 'Bash':
            # Command execution
            surface.lcd_write(1, 0, "Bash: Running")
            surface.set_led(0, 0, 0, 255)  # Blue

        surface.disconnect()

    except Exception as e:
        # Graceful degradation - don't fail if Arduino unavailable
        pass
```

### Approach 3: MCP Tool Direct Use

**Agents in Claude Desktop can directly control Arduino**:

```python
# From any Claude Desktop agent
mcp__arduino_surface__surface_display(
    row=0,
    col=0,
    text="Agent Working..."
)

mcp__arduino_surface__surface_led_set(
    tier=0,
    r=0, g=0, b=255  # Blue
)

# Do work...

mcp__arduino_surface__surface_alert(type="success")
```

## Specific Use Cases

### Use Case 1: MCP Server Health Monitor

**Create `examples/mcp_monitor.py`**:
- Polls MCP server status every 5 seconds
- LCD: Shows active/total server count
- LED: Overall health (green/yellow/red)
- Alerts on server failures

### Use Case 2: Git Operations

**During git commits/pushes**:
```
LCD: "Git: Committing..."
LED: Blue (processing)
→ On success: Green alert + "Git: Pushed"
→ On error: Red alert + error message
```

### Use Case 3: Parallel Research

**When using /parallel-research**:
```
LCD: "Research: 3/5"
     "In Progress"
LED: Blue (processing)
→ Complete: Green alert + "Research: Done"
```

### Use Case 4: File Operations

**Large file writes**:
```
LCD: "Write: data.json"
     "Size: 2.3MB"
LED: Blue → Green (completion)
```

### Use Case 5: Ember Violations

**Production policy enforcement**:
```
LCD: "VIOLATION"
     "Mock UI detected"
LED: Red + error beeps
Voice: "Production violation detected"
```

## Integration Points

### 1. Voice Mode + Arduino
**Complementary communication**:
- Voice: Detailed information, conversations
- Arduino LCD: Persistent current state
- Arduino LED: At-a-glance health
- Arduino Alerts: Attention-grabbing

### 2. Enhanced Memory + Arduino
**Store all Arduino interactions**:
```python
mcp__enhanced_memory_mcp__create_entities([{
    'name': f'arduino-display-{timestamp}',
    'entityType': 'physical_feedback',
    'observations': [
        f'displayed: {text}',
        f'led_color: {color}',
        f'alert_type: {alert}'
    ]
}])
```

### 3. Agent Runtime + Arduino
**Track agent lifecycle**:
```python
# On agent spawn
surface.lcd_write(0, 0, f"Agent: {type}")
surface.set_led(0, 0, 0, 255)  # Blue

# On agent complete
surface.alert('success' if success else 'error')
```

### 4. Ember + Arduino
**Physical violation enforcement**:
```python
# On violation detected
surface.lcd_write(0, 0, "VIOLATION")
surface.lcd_write(1, 0, violation[:16])
surface.set_led(0, 255, 0, 0)  # Red
surface.alert('error')
```

## Roadmap

### Phase 1: Basic Status Display (CURRENT)
- [x] Hardware working (LCD + LED)
- [ ] Background daemon displaying agent activity
- [ ] LED color coding for system health
- [ ] Integration with post-tool-use hook

### Phase 2: Task Completion Alerts (NEXT)
- [ ] Alert on task completion
- [ ] Voice + Arduino coordinated feedback
- [ ] Enhanced-memory logging of interactions

### Phase 3: Human-in-Loop (AFTER BUTTONS)
- [ ] Wire confirm/cancel buttons
- [ ] Implement approval workflow
- [ ] Critical operation gating
- [ ] Timeout handling

### Phase 4: Environmental Context (AFTER SENSORS)
- [ ] Wire sensors (pot, temp, light, tilt)
- [ ] Environmental context gathering
- [ ] Agent behavior adjustment based on context
- [ ] Emergency stop via tilt switch

### Phase 5: Advanced Visualization (AFTER SERVO/BUZZER)
- [ ] Wire servo motor
- [ ] Wire buzzer
- [ ] Servo shows utilization/progress
- [ ] Rich audio feedback patterns

## Success Metrics

1. **Ambient Awareness**: Can Marc glance at Arduino and know system status without checking terminal?
2. **Attention Management**: Do critical alerts reliably get Marc's attention?
3. **Confirmation Loop**: Does physical feedback confirm digital operations?
4. **Human-in-Loop**: Can Marc approve/deny operations via physical buttons?
5. **Environmental Grounding**: Do agents adjust behavior based on physical context?

## Conclusion

The Arduino Surface transforms from a hardware project into a **Tier0 physical nervous system** for our agentic framework. It creates:

- **Ambient awareness** without screen focus
- **Multi-sensory feedback** (visual + audio + tactile)
- **Human-in-loop gating** for critical decisions
- **Environmental context** for agent behavior
- **Attention hierarchy** for urgency management
- **Physical presence** for digital agents

This aligns with the vision of production-ready agentic systems that exist in and interact with the physical world, not just in chat windows and terminals.

**Next Step**: Implement Phase 1 background daemon for basic status display.
