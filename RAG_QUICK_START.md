# RAG Code Generator - Quick Start Guide

## What is RAG?

Retrieval-Augmented Generation (RAG) enables the autonomous system to **learn from experience** by:
1. Storing every successful code optimization
2. Retrieving similar past optimizations when generating new code
3. Using historical context to make better decisions

**Result**: The system gets smarter with every successful modification.

## Quick Start

### 1. Verify System is Ready

```bash
# Check Qdrant is running
curl http://localhost:6333/collections

# Check Ollama is running
curl http://localhost:11434/api/tags

# Run integration test
cd /Volumes/SSDRAID0/agentic-system
python3 test_rag_integration.py
```

### 2. Use RAG in Python

```python
from intelligent-agents.rag_code_generator import RAGCodeGenerator

# Initialize
rag = RAGCodeGenerator()

# Store a successful optimization
await rag.store_successful_modification(
    modification_id="my_opt_001",
    target_function="my_function",
    code_before="# original code",
    code_after="# optimized code",
    optimization_type="list_comprehension",
    performance_gain=25.3,
    reasoning="Replaced loop with list comprehension"
)

# Generate optimized code using RAG
optimized, reasoning = await rag.generate_with_rag(
    target_code="# code to optimize",
    target_function="my_function",
    insights=["Use Python builtins", "Avoid repeated operations"],
    optimization_goal="performance"
)

print(f"Optimized:\n{optimized}")
print(f"\nReasoning:\n{reasoning}")
```

### 3. Autonomous Integration

RAG is **automatically used** by the autonomous loop:

- **After successful modifications**: Stored in Qdrant + metadata
- **Before code generation**: Retrieves similar patterns to inform decisions
- **No manual intervention required**: It just works!

## How It Works

### Storage Flow

```
Successful Modification
    ↓
Code Embedding (sentence-transformers)
    ↓
Store in Qdrant (vector) + Enhanced Memory (metadata)
    ↓
Available for future retrieval
```

### Generation Flow

```
New Code to Optimize
    ↓
Embed Code
    ↓
Retrieve Top-5 Similar Past Modifications
    ↓
Build Context from History
    ↓
Generate with Ollama + Context
    ↓
Return Optimized Code + Reasoning
```

## Check Status

### View Stored Modifications

```python
from intelligent-agents.rag_code_generator import RAGCodeGenerator

rag = RAGCodeGenerator()
stats = await rag.get_statistics()

print(f"Total modifications: {stats['total_modifications']}")
print(f"Average gain: {stats['avg_performance_gain']:.1f}%")
print(f"Max gain: {stats['max_performance_gain']:.1f}%")
print(f"Types: {stats['optimization_types']}")
```

### Query Qdrant Directly

```bash
# Count points
curl http://localhost:6333/collections/code_modifications

# View sample points
curl -X POST http://localhost:6333/collections/code_modifications/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": true, "with_vector": false}'
```

## Troubleshooting

### Problem: Qdrant not accessible
**Solution**:
```bash
cd /Volumes/SSDRAID0/agentic-system/scripts
./start-qdrant.sh
```

### Problem: Ollama not responding
**Solution**:
```bash
# Check if running
ps aux | grep ollama

# Start if needed
ollama serve
```

### Problem: Embeddings slow
**Solution**: First run loads model (2-3 seconds), subsequent runs are fast (<200ms)

### Problem: Generation takes long
**Solution**: Normal! Ollama gpt-oss:20b takes 10-15 seconds for quality results. Can use smaller model for speed.

## Performance Tips

1. **Batch Operations**: Store multiple modifications in one session
2. **Filter by Type**: Use optimization_type filter for targeted retrieval
3. **Adjust Similarity**: Lower threshold (0.3) for more results, higher (0.7) for precision
4. **Context Window**: Default top-5 is good, increase for complex cases

## Example Outputs

### List Comprehension Pattern

**Input**:
```python
result = []
for item in items:
    if item > 0:
        result.append(item * 2)
return result
```

**RAG Output**:
```python
return [item * 2 for item in items if item > 0]
```

**Gain**: ~20-30% faster

### Caching Pattern

**Input**:
```python
def get_user(user_id):
    return database.query(f"SELECT * FROM users WHERE id={user_id}")
```

**RAG Output**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user(user_id):
    return database.query(f"SELECT * FROM users WHERE id={user_id}")
```

**Gain**: ~90-95% faster (after cache warm-up)

### Vectorization Pattern

**Input**:
```python
result = []
for value in values:
    result.append(math.sqrt(value) * 2.5)
return result
```

**RAG Output**:
```python
import numpy as np
return np.sqrt(np.array(values)) * 2.5
```

**Gain**: ~80-150% faster (for large arrays)

## Configuration

### Change Embedding Model

```python
from intelligent-agents.rag_code_generator import CodeEmbedder

# Use CodeBERT (better for code)
embedder = CodeEmbedder(model_name="microsoft/codebert-base")

# Use smaller model (faster)
embedder = CodeEmbedder(model_name="sentence-transformers/all-MiniLM-L12-v2")
```

### Change LLM Model

```python
rag = RAGCodeGenerator(ollama_host="http://localhost:11434")

# In generate_with_rag, use different model
optimized, reasoning = await rag.generate_with_rag(
    target_code=code,
    target_function="func",
    insights=[...],
    optimization_goal="performance"
)

# Internally calls _call_ollama with model="gpt-oss:20b"
# Can modify to use: "deepseek-coder:33b", "codellama:13b", etc.
```

### Adjust Retrieval Parameters

```python
# Retrieve more similar modifications
similar = await rag.retrieve_similar_modifications(
    target_code=code,
    limit=10,  # Default: 5
    min_performance_gain=5.0,  # Default: 5.0
    optimization_type="list_comprehension"  # Optional filter
)

# Lower threshold for exploration
similar = await rag.retrieve_similar_modifications(
    target_code=code,
    limit=5,
    min_performance_gain=1.0  # Include smaller gains
)
```

## Key Files

- **Implementation**: `intelligent-agents/rag_code_generator.py`
- **Integration**: `autonomous_recursive_agi_loop.py`
- **Tests**: `test_rag_integration.py`
- **Documentation**: `RAG_CODE_GENERATOR_COMPLETE.md`
- **Quick Start**: This file

## Next Steps

1. **Let it Run**: The autonomous loop will use RAG automatically
2. **Monitor Growth**: Check statistics periodically to see learning progress
3. **Review Results**: Look at git commits to see RAG-generated optimizations
4. **Tune if Needed**: Adjust parameters based on results

## Success Indicators

✅ **System is learning** when:
- Modifications stored in Qdrant increase over time
- Retrieval finds similar patterns (similarity >0.3)
- Generated code references past successful patterns
- Optimization quality improves cycle-over-cycle

✅ **RAG is working** when you see:
- Log messages: "Using RAG to generate optimized code..."
- Log messages: "RAG generated optimized code"
- Log messages: "Storing in RAG system for future learning..."
- Qdrant collection growing: `code_modifications` point count increases

---

**Remember**: RAG learns from every successful modification. The more the system runs, the smarter it gets!
