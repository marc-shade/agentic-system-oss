# AGI System - Quick Start Guide

**Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2025-11-10

---

## 🚀 Getting Started (30 Seconds)

### Run Your First AGI Workflow

```bash
cd /Volumes/SSDRAID0/agentic-system
python3 demo_agi_workflow.py
```

**Expected Output**: Complete 6-phase AGI workflow in ~0.5 seconds

---

## 💻 Using the AGI System

### Option 1: Python API (Recommended)

```python
from agi_orchestrator import AGIOrchestrator
import asyncio

# Initialize
orchestrator = AGIOrchestrator()

# Execute a goal
result = await orchestrator.execute_goal(
    goal_description="Build a REST API for user authentication",
    context={"language": "Python", "framework": "FastAPI"},
    record_learning=True,
    propose_improvements=True
)

print(f"Success: {result['success']}")
print(f"Duration: {result['total_duration_seconds']:.2f}s")
```

### Option 2: Simple Task (No Full Workflow)

```python
# For quick tasks without full goal decomposition
result = await orchestrator.execute_simple_task(
    task_description="Optimize this database query",
    task_type="optimization"
)
```

### Option 3: SDK Agent Bridge

```python
from sdk_agent_bridge import get_sdk_agent_bridge

bridge = get_sdk_agent_bridge()

# Use specialized agent
result = await bridge.execute_task(
    agent_type="code_generation",
    task_description="Create a Fibonacci function",
    context={"language": "python", "optimized": True}
)
```

---

## 🧠 What Each Component Does

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| **Meta-Learning** | Learns from outcomes | Automatic - runs every execution |
| **Multi-Agent Coord** | Parallel task execution | Use via orchestrator |
| **Skill Evolution** | A/B test improvements | Automatic - tracks all skills |
| **Goal Decomposition** | NL to tasks | Use via `execute_goal()` |
| **Context Synthesis** | Gather information | Automatic in full workflow |
| **Darwin Gödel** | Self-improvement | Automatic - analyzes performance |

---

## 📊 Check System Status

### System Health
```python
health = orchestrator.get_system_health()
print(health)
```

### Learning Progress
```python
summary = orchestrator.meta_learning.get_learning_summary()
print(f"Total outcomes: {summary['total_outcomes']}")
print(f"Success rate: {summary['overall_success_rate']:.1%}")
print(f"Learning maturity: {summary['learning_maturity']:.1%}")
```

### Available Agents
```python
status = orchestrator.coordinator.get_system_status()
print(f"Agents: {status['total_agents']}")
print(f"Capacity: {status['total_capacity']}")
```

---

## 🛠️ Advanced Usage

### Start A/B Test for Skills

```python
from skill_evolution_system import SkillEvolutionSystem

system = SkillEvolutionSystem()

# Register two versions of a skill
system.register_skill("data_processor", code_v1, "Version 1")
system.register_skill("data_processor", code_v2, "Version 2")

# Start A/B test
test_id = system.start_ab_test(
    skill_name="data_processor",
    version_a="v1",
    version_b="v2",
    split_ratio=0.5
)

# After 50+ executions, analyze results
results = system.analyze_ab_test(test_id, min_samples=50)

# Promote winner
if results['recommendation']:
    system.promote_version("data_processor", results['winner'])
```

### Record Custom Outcomes

```python
from meta_learning_engine import MetaLearningEngine, TaskOutcome
from datetime import datetime

engine = MetaLearningEngine()

outcome = TaskOutcome(
    task_id="custom_task_001",
    task_type="optimization",
    agent_used="optimizer",
    success=True,
    execution_time_ms=1500,
    error_message=None,
    quality_score=0.9,
    timestamp=datetime.now(),
    context={"approach": "caching"}
)

engine.record_outcome(outcome)
```

### Get Agent Recommendations

```python
# Ask meta-learning which agent is best for a task type
agent, confidence = orchestrator.meta_learning.recommend_agent(
    task_type="code_generation",
    context={"language": "python"}
)

print(f"Recommended: {agent} (confidence: {confidence:.2f})")
```

---

## 📈 Monitoring

### Check Learning Progress
```bash
# View meta-learning database
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/meta_learning.db
> SELECT COUNT(*) FROM task_outcomes;
> SELECT agent_used, AVG(quality_score) FROM task_outcomes GROUP BY agent_used;
```

### Check Autonomous Daemon
```bash
# Check if running
ps aux | grep autonomous_improvement

# View logs
tail -f /Volumes/SSDRAID0/agentic-system/logs/autonomous_improvement.log

# View cycle reports
ls -lh /Volumes/SSDRAID0/agentic-system/logs/improvement_cycles/
cat /Volumes/SSDRAID0/agentic-system/logs/improvement_cycles/cycle_0001.json
```

### Check Registered Skills
```bash
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/skill_evolution.db
> SELECT skill_name, version, status FROM skill_versions;
```

---

## 🔧 Common Tasks

### Register a New Skill
```python
from skill_evolution_system import SkillEvolutionSystem

system = SkillEvolutionSystem()

code = '''
def my_new_skill(data):
    """Process data efficiently"""
    return [x * 2 for x in data if x > 0]
'''

skill = system.register_skill(
    skill_name="my_new_skill",
    code=code,
    description="Efficient data processing"
)

print(f"Registered: {skill.skill_name} v{skill.version}")
```

### Execute Custom Goal
```python
result = await orchestrator.execute_goal(
    goal_description="Your custom goal here",
    context={
        "language": "Python",
        "framework": "FastAPI",
        "requirements": ["authentication", "database"]
    }
)

# Check each phase
for phase, data in result['phases'].items():
    print(f"{phase}: {data['status']}")
```

### Search Unified Memory
```python
from unified_memory import get_unified_memory

memory = get_unified_memory()

results = await memory.retrieve(
    query="optimization patterns",
    limit=10,
    search_all=True
)

for result in results:
    print(f"- {result}")
```

---

## 🎯 Real-World Examples

### Example 1: Code Generation Task
```python
result = await orchestrator.execute_goal(
    goal_description="Create a Python class for managing user sessions with Redis",
    context={
        "language": "Python",
        "database": "Redis",
        "requirements": ["session expiry", "thread safety"]
    }
)
```

### Example 2: Data Analysis Task
```python
result = await orchestrator.execute_goal(
    goal_description="Analyze CSV sales data and create visualization",
    context={
        "input_format": "CSV",
        "output_format": "PNG",
        "requirements": ["statistical analysis", "charts"]
    }
)
```

### Example 3: Optimization Task
```python
result = await orchestrator.execute_simple_task(
    task_description="Optimize this SQL query for better performance",
    task_type="optimization"
)
```

---

## 🐛 Troubleshooting

### Issue: Import errors
```bash
# Make sure you're in the right directory
cd /Volumes/SSDRAID0/agentic-system

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### Issue: Database locked
```bash
# Close any open database connections
pkill -f sqlite3

# Or manually check
lsof /Volumes/SSDRAID0/agentic-system/databases/*.db
```

### Issue: MCP tools not visible
The AGI system works perfectly via direct Python import even if MCP tools aren't showing up. Use the Python API as shown above.

---

## 📚 Documentation

- **Complete Integration**: `AGI_INTEGRATION_COMPLETE.md`
- **Final Status**: `FINAL_STATUS.md`
- **System Status**: `AGI_SYSTEM_STATUS.md`
- **Gap Analysis**: `AGI_SYSTEM_GAPS.md`
- **SAFLA Guide**: `SAFLA_ACTIVATION_REQUIRED.md`

---

## 🚦 System Status

**Check if everything is running**:
```bash
# AGI orchestrator
python3 -c "from agi_orchestrator import AGIOrchestrator; print('✓ AGI working')"

# Autonomous daemon
ps aux | grep autonomous_improvement | grep -v grep && echo "✓ Daemon running"

# Databases
ls -lh databases/*.db && echo "✓ Databases exist"

# Skills
sqlite3 databases/skill_evolution.db "SELECT COUNT(*) FROM skill_versions;" && echo "✓ Skills registered"
```

---

## ⚡ Quick Commands

```bash
# Run demo
python3 demo_agi_workflow.py

# Register skills
python3 intelligent-agents/register_skills.py

# Check daemon status
cat /tmp/agi_improvement_daemon.pid

# View latest cycle
cat logs/improvement_cycles/cycle_$(ls logs/improvement_cycles/ | sort -r | head -1)

# Check learning progress
sqlite3 databases/meta_learning.db "SELECT COUNT(*) FROM task_outcomes;"
```

---

## 🎓 Next Steps

1. **Run the demo** to see the full workflow
2. **Execute your first real goal** with custom requirements
3. **Monitor meta-learning** as it accumulates data
4. **Check improvement cycles** from autonomous daemon
5. **Watch learning maturity** increase over time

---

**The AGI system is ready to use right now. Start with the demo, then try your own goals!**

For more information, see the complete documentation in `AGI_INTEGRATION_COMPLETE.md` and `FINAL_STATUS.md`.
