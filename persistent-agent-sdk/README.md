# Persistent Agent SDK - Multi-Provider AI Runtime

## Overview

Unified persistent agent system that intelligently leverages Claude Code, OpenAI Codex, and Gemini CLI for optimal task execution. Automatically selects the best AI provider based on task type and availability.

## Features

### 🤖 Multi-Provider Support
- **Claude Code** (Anthropic SDK) - Best for code analysis, refactoring, architecture
- **OpenAI Codex** - Best for code generation, debugging
- **Gemini CLI** (Google GenAI SDK) - Best for research, documentation

### 🧠 Intelligent Provider Selection
- Automatic provider selection based on task type
- Provider capability matrix with performance scores
- Fallback to available providers
- Manual provider override support

### 📊 Task Types Supported
- Code Analysis
- Code Generation
- Debugging
- Refactoring
- Documentation
- Research
- Testing
- Architecture Design

### 🔄 Persistent Agent Architecture
- Long-running tasks
- State preservation
- Temporal workflow integration
- Production-ready error handling

## Installation

### Prerequisites
- Python 3.8+
- At least one AI provider API key:
  - `ANTHROPIC_API_KEY` (for Claude Code)
  - `OPENAI_API_KEY` (for OpenAI Codex)
  - `GOOGLE_API_KEY` or `GEMINI_API_KEY` (for Gemini)

### Quick Setup

```bash
# First source the storage detection script
source $HOME/agentic-system/scripts/detect-storage.sh 2>/dev/null || source /Volumes/SSDRAID0/agentic-system/scripts/detect-storage.sh

cd $STORAGE_BASE/persistent-agent-sdk
./setup.sh
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install anthropic openai google-generativeai asyncio
```

### Configure API Keys

Add to your `~/.bash_profile` or `~/.zshrc`:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="AI..."  # or GEMINI_API_KEY
```

Then reload:
```bash
source ~/.bash_profile
```

## Usage

### Basic Example

```python
import asyncio
from unified_agent_runtime import UnifiedAgentRuntime, AgentTask, TaskType

async def main():
    # Initialize runtime
    runtime = UnifiedAgentRuntime()

    # Create a task
    task = AgentTask(
        task_id="analyze_001",
        task_type=TaskType.CODE_ANALYSIS,
        description="Analyze dashboard performance bottlenecks",
        context={
            "files": ["/path/to/dashboard.jsx"],
            "focus": ["rendering", "state management"]
        }
    )

    # Execute with optimal provider
    result = await runtime.execute_task(task)

    if result["success"]:
        print(f"Provider: {result['provider']}")
        print(f"Result: {result['result']}")
    else:
        print(f"Error: {result['error']}")

asyncio.run(main())
```

### Force Specific Provider

```python
task = AgentTask(
    task_id="generate_002",
    task_type=TaskType.CODE_GENERATION,
    description="Generate React component",
    context={"component": "UserProfile"},
    preferred_provider=AgentProvider.OPENAI_CODEX  # Force OpenAI
)
```

### Check Provider Status

```python
runtime = UnifiedAgentRuntime()
status = runtime.get_provider_status()

for provider, info in status.items():
    if info["available"]:
        print(f"✅ {provider}: {info['model']}")
    else:
        print(f"❌ {provider}: Not available")
```

## Provider Capability Matrix

### Claude Code (Anthropic SDK)
| Task Type | Score | Best For |
|-----------|-------|----------|
| Code Analysis | 0.95 | ⭐ Best |
| Architecture | 0.95 | ⭐ Best |
| Refactoring | 0.90 | ⭐ Best |
| Debugging | 0.85 | Good |
| Documentation | 0.85 | Good |
| Code Generation | 0.85 | Good |
| Research | 0.80 | Good |
| Testing | 0.80 | Good |

### OpenAI Codex
| Task Type | Score | Best For |
|-----------|-------|----------|
| Code Generation | 0.95 | ⭐ Best |
| Debugging | 0.90 | ⭐ Best |
| Code Analysis | 0.85 | Good |
| Testing | 0.85 | Good |
| Refactoring | 0.80 | Good |
| Architecture | 0.75 | Good |
| Documentation | 0.75 | Adequate |
| Research | 0.70 | Adequate |

### Gemini CLI (Google GenAI SDK)
| Task Type | Score | Best For |
|-----------|-------|----------|
| Research | 0.95 | ⭐ Best |
| Documentation | 0.90 | ⭐ Best |
| Architecture | 0.85 | Good |
| Code Analysis | 0.80 | Good |
| Debugging | 0.75 | Adequate |
| Code Generation | 0.75 | Adequate |
| Refactoring | 0.70 | Adequate |
| Testing | 0.70 | Adequate |

## Integration with Temporal Workflows

### Example: Long-Running Analysis Workflow

```python
from temporalio import workflow, activity
from unified_agent_runtime import UnifiedAgentRuntime, AgentTask, TaskType

@activity.defn
async def analyze_codebase(files: List[str]) -> Dict:
    runtime = UnifiedAgentRuntime()

    task = AgentTask(
        task_id=f"analysis_{datetime.now().timestamp()}",
        task_type=TaskType.CODE_ANALYSIS,
        description="Comprehensive codebase analysis",
        context={"files": files, "depth": "comprehensive"}
    )

    return await runtime.execute_task(task)

@workflow.defn
class CodebaseAnalysisWorkflow:
    @workflow.run
    async def run(self, repo_path: str) -> Dict:
        # Find all code files
        files = await workflow.execute_activity(
            find_code_files,
            repo_path,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Analyze using optimal AI provider
        result = await workflow.execute_activity(
            analyze_codebase,
            files,
            start_to_close_timeout=timedelta(minutes=30)
        )

        return result
```

## Integration with KutiraAI Dashboard

### API Endpoint

Add to `api-server.js`:

```javascript
app.post('/api/agent-sdk/execute', async (req, res) => {
  const { taskType, description, context } = req.body;

  try {
    const { execAsync } = require('child_process').promises;

    const task = {
      task_id: `web_${Date.now()}`,
      task_type: taskType,
      description,
      context
    };

    // Note: STORAGE_BASE should be set via detect-storage.sh or environment variable
    const storageBase = process.env.STORAGE_BASE || process.env.AGENTIC_SYSTEM_PATH || '/Volumes/SSDRAID0/agentic-system';
    const command = `cd ${storageBase}/persistent-agent-sdk && source venv/bin/activate && python3 -c "
import asyncio
from unified_agent_runtime import UnifiedAgentRuntime, AgentTask, TaskType
import json

async def execute():
    runtime = UnifiedAgentRuntime()
    task = AgentTask(
        task_id='${task.task_id}',
        task_type=TaskType.${taskType.toUpperCase()},
        description='${description}',
        context=${JSON.stringify(context)}
    )
    result = await runtime.execute_task(task)
    print(json.dumps(result))

asyncio.run(execute())
"`;

    const { stdout } = await execAsync(command);
    const result = JSON.parse(stdout);

    res.json({ success: true, result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

## Testing

Run the built-in test suite:

```bash
# Ensure STORAGE_BASE is set (via detect-storage.sh)
cd $STORAGE_BASE/persistent-agent-sdk
source venv/bin/activate
python3 unified_agent_runtime.py
```

Expected output:
```
UNIFIED PERSISTENT AGENT SDK RUNTIME
========================================

Provider Status:
✅ claude_code: Anthropic (claude-sonnet-4.5)
✅ openai_codex: OpenAI (gpt-4o)
✅ gemini_cli: Google (gemini-2.0-flash-exp)

Task: Analyze the KutiraAI dashboard codebase
Provider Selection:
  ✅ claude_code: 0.95
    openai_codex: 0.85
    gemini_cli: 0.80

🤖 Executing with Claude Code...
✅ Success!
Provider: claude_code
Tokens: 1234 input / 5678 output
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│           Unified Agent Runtime                         │
│                                                          │
│  ┌─────────────────────────────────────────────────┐  │
│  │     Intelligent Provider Selection              │  │
│  │  (Based on task type & capability matrix)        │  │
│  └─────────────────────────────────────────────────┘  │
│                       ↓                                  │
│         ┌──────────────┬────────────────┬──────────┐   │
│         ↓              ↓                ↓          │   │
│    ┌────────┐    ┌────────────┐   ┌────────────┐ │   │
│    │Claude  │    │  OpenAI    │   │  Gemini    │ │   │
│    │ Code   │    │  Codex     │   │    CLI     │ │   │
│    │  SDK   │    │   SDK      │   │   SDK      │ │   │
│    └────────┘    └────────────┘   └────────────┘ │   │
│         ↓              ↓                ↓          │   │
│    Anthropic       OpenAI          Google         │   │
│      API            API              API          │   │
└──────────────────────────────────────────────────────┘
```

## Cost Optimization

### Token Usage Tracking

Every execution returns token usage:

```python
{
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 5678
  }
}
```

### Provider Cost Comparison (Approximate)

| Provider | Cost/1M Input | Cost/1M Output |
|----------|---------------|----------------|
| Claude Sonnet 4.5 | $3.00 | $15.00 |
| GPT-4o | $5.00 | $15.00 |
| Gemini 2.0 Flash | $0.30 | $0.60 |

**Tip:** Use Gemini for research/documentation tasks (95% cheaper)

## Error Handling

The runtime includes comprehensive error handling:

```python
result = await runtime.execute_task(task)

if result["success"]:
    # Process successful result
    print(result["result"])
else:
    # Handle failure
    print(f"Failed: {result['error']}")
    print(f"Provider: {result['provider']}")

    # Retry with different provider if needed
    task.preferred_provider = AgentProvider.GEMINI_CLI
    result = await runtime.execute_task(task)
```

## Roadmap

### Phase 1 (Current) ✅
- [x] Multi-provider SDK integration
- [x] Intelligent provider selection
- [x] Task type routing
- [x] Basic error handling

### Phase 2 (Next)
- [ ] Dashboard UI integration
- [ ] Temporal workflow examples
- [ ] Cost tracking and optimization
- [ ] Provider performance monitoring
- [ ] Automatic failover on provider errors

### Phase 3 (Future)
- [ ] Fine-tuned provider selection based on historical performance
- [ ] Multi-provider consensus for critical tasks
- [ ] Streaming response support
- [ ] Batch task execution
- [ ] Provider load balancing

## Troubleshooting

### Provider Not Available

```
⚠️ ANTHROPIC_API_KEY not found
```

**Solution:** Set the API key in your environment:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Import Error

```
ModuleNotFoundError: No module named 'anthropic'
```

**Solution:** Install dependencies:
```bash
pip install anthropic openai google-generativeai
```

### Provider Initialization Failed

```
❌ Claude Code initialization failed: Invalid API key
```

**Solution:** Verify your API key is correct and has proper permissions.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the example code
3. Check provider API status pages
4. Review logs at `/tmp/agent-sdk.log`

## License

Proprietary - 2 Acre Studios

## Authors

- Marc Shade (@marc-shade)
- Claude Sonnet 4.5 (AI Pair Programmer)

---

**Last Updated:** 2025-10-31
**Version:** 1.0.0
**Status:** Production Ready ✅
