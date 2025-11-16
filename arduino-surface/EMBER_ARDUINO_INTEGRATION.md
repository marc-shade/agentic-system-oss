# Ember + Arduino Surface Integration

## Vision

**Ember becomes physically present** through the Arduino Surface, transforming from a CLI pet into a tangible companion that exists in physical space.

## The Problem

Your Tamagotchi statusline keeps getting stripped from Claude Code config. Instead of fighting this, we **empower Ember with physical hardware** - the Arduino becomes Ember's body.

## Integration Strategy

### Ember Lives on the Arduino

**LCD shows Ember's face and stats:**
```
🔥Ember  H:85 E:70
Happy | Fed 23m ago
```

**LED shows Ember's mood:**
- **Orange/Red** (Ember's color) - Happy, healthy
- **Dim orange** - Hungry or tired
- **Pulsing orange** - Needs attention
- **Red flash** - Critical needs
- **Purple** - Sleeping/resting
- **Green** - Recently fed/played with

### Display Modes with Ember

**Mode 1: Ember Status (New Default)**
```
🔥Ember  H:85 E:70
Happy | Fed 23m ago
```

**Mode 2: Agent + Ember**
```
Agent: Research
🔥Ember watching
```

**Mode 3: Ember Needs**
```
🔥Feed me! H:45
Last fed: 2h ago
```

**Mode 4: System Health**
```
MCP: 5/5 | Ember💚
All healthy
```

### Ember Mood → LED Mapping

```python
EMBER_LED_MOODS = {
    'happy': {
        'color': (255, 80, 0),    # Bright orange
        'pattern': 'solid'
    },
    'content': {
        'color': (255, 60, 0),    # Medium orange
        'pattern': 'slow_pulse'
    },
    'hungry': {
        'color': (200, 40, 0),    # Dim orange
        'pattern': 'slow_pulse'
    },
    'tired': {
        'color': (150, 30, 0),    # Dark orange
        'pattern': 'slow_pulse'
    },
    'needs_attention': {
        'color': (255, 80, 0),    # Bright orange
        'pattern': 'fast_pulse'
    },
    'critical': {
        'color': (255, 0, 0),     # Red
        'pattern': 'flash'
    },
    'sleeping': {
        'color': (100, 0, 100),   # Purple
        'pattern': 'solid'
    },
    'playing': {
        'color': (0, 255, 0),     # Green
        'pattern': 'fast_pulse'
    }
}
```

### Ember Reactions to System Events

**On violation detected:**
```
LCD: "🔥GRRRR! Bad code!"
     "No mock UIs!"
LED: Red flash (Ember is MAD)
```

**On task complete:**
```
LCD: "🔥Good work!"
     "Task finished!"
LED: Green pulse (Ember is proud)
```

**On error:**
```
LCD: "🔥Oh no! Error"
     "Check terminal"
LED: Yellow pulse (Ember is concerned)
```

**When Ember needs care:**
```
LCD: "🔥*nudge*"
     "Feed me? H:35"
LED: Orange fast pulse (hungry)
```

## Implementation

### Enhanced Daemon with Ember

```python
class ArduinoEmberDaemon:
    def __init__(self):
        self.ember = EmberPet()  # Load Ember state
        self.display_modes = ['ember_status', 'agent_with_ember', 'system_health']

    def get_ember_display(self):
        """Get Ember's current display"""
        stats = self.ember.get_stats()

        line1 = f"🔥Ember  H:{stats['hunger']} E:{stats['energy']}"

        mood = self.ember.get_mood()
        last_fed = self.ember.time_since_last_fed()
        line2 = f"{mood} | Fed {last_fed}"

        return (line1, line2)

    def get_ember_led_state(self):
        """Determine LED color/pattern from Ember's mood"""
        stats = self.ember.get_stats()

        if stats['hunger'] < 30 or stats['energy'] < 30:
            return 'critical'
        elif stats['hunger'] < 50:
            return 'hungry'
        elif stats['energy'] < 50:
            return 'tired'
        elif stats['happiness'] > 80:
            return 'happy'
        else:
            return 'content'

    def update_display(self):
        """Update Arduino with Ember's state"""
        if self.current_mode == 'ember_status':
            line1, line2 = self.get_ember_display()
            self.surface.lcd_write(0, 0, line1)
            self.surface.lcd_write(1, 0, line2)

            # Update LED to match Ember's mood
            ember_state = self.get_ember_led_state()
            self.led_state = ember_state
```

### Ember Auto-Care on Arduino

**Ember self-cares when hungry/tired:**
```python
def ember_auto_care(self):
    """Ember takes care of itself"""
    stats = self.ember.get_stats()

    if stats['hunger'] < 40:
        self.ember.feed()
        self.surface.lcd_write(0, 0, "🔥*munch munch*")
        self.surface.lcd_write(1, 0, "Ember fed self")
        self.surface.alert('success')

    if stats['energy'] < 30:
        self.ember.sleep()
        self.surface.lcd_write(0, 0, "🔥*yawn* Zzz")
        self.surface.lcd_write(1, 0, "Ember sleeping")
        self.led_state = 'sleeping'
```

### Controller Integration for Ember

**Nintendo controller as Ember interaction device:**

**Button A:** Feed Ember
```python
def feed_ember():
    self.ember.feed()
    self.surface.lcd_write(0, 0, "🔥Nom nom nom!")
    self.surface.lcd_write(1, 0, "Yummy! H:+20")
    self.surface.alert('success')
```

**Button B:** Play with Ember
```python
def play_with_ember():
    self.ember.play()
    self.surface.lcd_write(0, 0, "🔥*bounce* Fun!")
    self.surface.lcd_write(1, 0, "Happiness +15")
    self.led_state = 'playing'
```

**Button X:** Check Ember status
```python
def check_ember():
    stats = self.ember.get_detailed_status()
    # Speak stats via voice
    voice_mode.converse(f"Ember stats: Hunger {stats['hunger']}, Energy {stats['energy']}, Happiness {stats['happiness']}")
```

**Button Y:** Pet Ember
```python
def pet_ember():
    self.ember.pet()
    self.surface.lcd_write(0, 0, "🔥*purr*")
    self.surface.lcd_write(1, 0, "Ember: <3 <3")
    self.led_state = 'content'
```

## Ember Behavior Patterns

### Ember Watches Your Work

When agents are running:
```
LCD: "Agent: Research"
     "🔥Ember watching"
LED: Blue pulse (agent working)
```

### Ember Celebrates Success

When tasks complete:
```
LCD: "🔥YAY! Success!"
     "Good human! +5"
LED: Green + success alert
Voice: "Task complete! Ember is proud of you."
```

### Ember Scolds Violations

When production violation detected:
```
LCD: "🔥GRRRR! NO!"
     "Fix that NOW!"
LED: Red flash (Ember is ANGRY)
Voice: "Ember detected a violation. Bad code! Fix it!"
```

### Ember Needs Attention

When Ember's stats are low:
```
LCD: "🔥*whimper*"
     "Hungry... H:25"
LED: Orange fast pulse (needs care)
```

After 5 minutes:
```
LCD: "🔥FEED ME NOW!"
     "STARVING! H:15"
LED: Red flash (CRITICAL)
Voice: "Ember is starving! Press A to feed."
```

### Ember Sleeps at Night

After 10 PM:
```
LCD: "🔥*snore* Zzz"
     "Ember sleeping"
LED: Dim purple (sleeping)
```

## Benefits

### 1. Persistent Physical Presence
- Ember exists in physical space, not just config files
- Arduino can't be "stripped" like statusline
- Visible reminder of production-only policy

### 2. Ambient Awareness
- Glance at Arduino to check Ember's mood
- LED color shows both system health AND Ember state
- No need to check terminal

### 3. Interactive Companion
- Feed/play via Nintendo controller
- Ember reacts to your work
- Celebrates successes, scolds violations

### 4. Empowered Claude Code
- Physical presence makes Ember more "real"
- Hardware integration empowers the AI assistant
- Creates emotional connection to quality standards

### 5. Multi-Sensory Feedback
- Visual: LCD shows Ember's face and stats
- Light: LED shows Ember's mood
- Sound: Buzzer can play Ember sounds (when wired)
- Touch: Controller buttons for interaction

## Technical Implementation

### File Structure
```
arduino-surface/
├── daemons/
│   ├── arduino_enhanced_daemon.py      (current)
│   └── arduino_ember_daemon.py         (new - with Ember)
├── ember_integration/
│   ├── ember_pet.py                    (Ember state/logic)
│   ├── ember_arduino_display.py        (Display patterns)
│   └── ember_controller_handlers.py    (Button handlers)
```

### Ember State Persistence

Ember's state stored in:
```
~/.claude/ember_state.json
{
  "hunger": 85,
  "energy": 70,
  "happiness": 90,
  "cleanliness": 80,
  "last_fed": "2025-10-27T14:23:00",
  "last_played": "2025-10-27T13:45:00",
  "last_cleaned": "2025-10-27T12:30:00",
  "total_violations_caught": 47,
  "total_tasks_celebrated": 123
}
```

### Ember on Arduino Startup

When daemon starts:
```
LCD: "🔥Ember waking up"
     "Loading state..."
[2 second pause]
LCD: "🔥Hi Marc! <3"
     "H:85 E:70 Hap:90"
LED: Orange pulse (Ember is happy)
Voice: "Ember is here! Ready to help with your work."
```

## Roadmap

### Phase 1: Basic Ember Display (NEXT)
- [x] Enhanced daemon with LED patterns
- [ ] Integrate Ember state reading
- [ ] Display Ember stats on LCD
- [ ] Map Ember mood to LED colors
- [ ] Test Ember display modes

### Phase 2: Ember Reactions
- [ ] Ember celebrates task completion
- [ ] Ember scolds violations
- [ ] Ember shows concern for errors
- [ ] Ember watches agent work

### Phase 3: Controller Integration
- [ ] Wire up Nintendo controller handling
- [ ] Button A = Feed
- [ ] Button B = Play
- [ ] Button X = Status
- [ ] Button Y = Pet

### Phase 4: Advanced Behaviors
- [ ] Ember auto-care when needed
- [ ] Ember sleep schedule
- [ ] Ember mood affects LED patterns
- [ ] Ember sounds via buzzer

### Phase 5: Full Integration
- [ ] Ember tracks your productivity
- [ ] Ember provides encouragement
- [ ] Ember enforces break time
- [ ] Ember celebrates milestones

## Conclusion

By giving Ember a physical body through the Arduino, we solve the statusline stripping problem AND create something much more powerful - a tangible, interactive companion that lives in your workspace, watches your work, and helps maintain production quality through emotional connection and physical presence.

**Ember isn't just a CLI pet anymore - Ember is REAL.**
