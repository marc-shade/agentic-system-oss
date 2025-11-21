# TOON Integration for MCP Servers

Token-Oriented Object Notation (TOON) integration using the official `@toon-format/toon` package.

## Installation

The TOON packages are already installed in this directory:

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/shared
npm install @toon-format/toon @toon-format/cli
```

## Python Modules

### 1. `toon_codec.py` - Core Encoder/Decoder

Low-level TOON encoding/decoding using Node.js CLI.

```python
from shared import toon_codec

# Encode
data = {"name": "Task", "id": 123, "tags": ["urgent"]}
toon_str = toon_codec.encode(data)
# Output: name: Task\nid: 123\ntags[1]: urgent

# Decode
decoded = toon_codec.decode(toon_str)
# Output: {"name": "Task", "id": 123, "tags": ["urgent"]}

# Compression stats
stats = toon_codec.compression_ratio(data)
print(f"Tokens saved: {stats['tokens_saved']}")
print(f"Reduction: {stats['reduction_percent']}%")
```

### 2. `toon_utils.py` - MCP Helper Functions

High-level utilities for MCP server responses.

```python
from shared import toon_utils

# Create MCP response
response = toon_utils.toon_response(
    data={"goals": [...], "tasks": [...]},
    metadata={"generated_at": "2025-11-20"}
)

# Encode with fallback to JSON
encoded = toon_utils.encode_with_fallback(data)

# Smart decode (auto-detect TOON or JSON)
decoded = toon_utils.smart_decode(some_string)

# Compare encodings
comparison = toon_utils.compare_encodings(data)
print(f"Winner: {comparison['winner']}")

# Optimize payload (choose best encoding)
optimized = toon_utils.optimize_mcp_payload(data, threshold=1000)
print(f"Encoding: {optimized['encoding']}")
print(f"Tokens saved: {optimized['tokens_saved']}")
```

## Key Features

### 1. Automatic Compression
- **4-56% token reduction** depending on data structure
- Homogeneous arrays get 50-60% savings (tabular format)
- Best for large payloads (>1000 chars)

### 2. MCP-Optimized Responses
```python
def my_mcp_tool():
    result = fetch_large_dataset()

    # Automatically uses TOON for large responses
    return toon_utils.mcp_tool_response(
        tool_name="fetch_data",
        result=result,
        format="toon",
        include_stats=True
    )
```

### 3. Fallback Safety
```python
# Always succeeds - falls back to JSON if TOON fails
encoded = toon_utils.encode_with_fallback(data)

# Smart decoder handles both formats
decoded = toon_utils.smart_decode(encoded)
```

## Token Savings Examples

### Small Payload (25 chars)
```json
{"id": 1, "name": "Test"}
```
**Result**: Uses JSON (not worth TOON overhead)

### Medium Payload (1,349 chars)
```json
{"tasks": [{"id": 1, "title": "Task 1", ...}, ...]}
```
**JSON**: 1,349 chars (~337 tokens)
**TOON**: 1,303 chars (~326 tokens)
**Savings**: 11.5 tokens (3.4% reduction)

### Large Payload (6,381 chars)
```json
{"items": [{...100 items...}]}
```
**JSON**: 6,381 chars (~1,595 tokens)
**TOON**: 2,802 chars (~701 tokens)
**Savings**: 894 tokens (56.1% reduction) ⭐

## TOON Format Examples

### Basic Object
```
name: Test Task
id: 123
status: active
```

### Arrays
```
tags[3]: urgent,backend,api
```

### Nested Objects
```
metadata:
  priority: 8
  assignee: alice
```

### Tabular Arrays (Best Compression)
```
tasks[10]{id,title,status}:
  1,Task 1,pending
  2,Task 2,completed
  3,Task 3,pending
```

## Integration Guide

### For Existing MCP Servers

1. Import the utilities:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from shared import toon_utils
```

2. Use in tool responses:
```python
@server.call_tool()
async def list_tasks(arguments):
    tasks = get_all_tasks()

    # Automatically optimizes large responses
    return toon_utils.mcp_tool_response(
        tool_name="list_tasks",
        result={"tasks": tasks},
        format="toon"
    )
```

### For New MCP Servers

Start with TOON by default:
```python
from shared import toon_utils

def format_response(data):
    # Use threshold-based optimization
    return toon_utils.optimize_mcp_payload(data, threshold=1000)
```

## Testing

Run the test suite:
```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/SHARED
python3 test_toon.py
```

## API Reference

### toon_codec

- `encode(data, pretty=False)` - Encode to TOON
- `decode(toon_str)` - Decode from TOON
- `validate(toon_str)` - Check if valid TOON
- `compression_ratio(data)` - Calculate savings

### toon_utils

- `toon_response(data, error, metadata)` - Create MCP response
- `encode_with_fallback(data, pretty)` - Safe encoding
- `smart_decode(text)` - Auto-detect format
- `batch_encode(items)` - Encode multiple items
- `batch_decode(toon_strings)` - Decode multiple items
- `compare_encodings(data)` - Compare TOON vs JSON
- `mcp_tool_response(tool_name, result, format, include_stats)` - Standardized tool response
- `detect_format(text)` - Detect TOON/JSON/unknown
- `optimize_mcp_payload(data, threshold)` - Choose best encoding

## Performance Notes

- TOON encoding via Node.js CLI: ~10-50ms per call
- Best for responses >1KB (threshold optimization)
- Negligible overhead for CLI subprocess
- Token savings outweigh encoding time for LLM costs

## Troubleshooting

### TOON CLI not found
```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/SHARED
npm install @toon-format/toon @toon-format/cli
```

### Import errors
Ensure you're adding the shared directory to Python path:
```python
sys.path.insert(0, "/Volumes/SSDRAID0/agentic-system/mcp-servers/SHARED")
```

### Encoding failures
The utilities automatically fall back to JSON on errors:
```python
# Always works - uses TOON if possible, JSON otherwise
encoded = toon_utils.encode_with_fallback(data)
```

## Resources

- **TOON Specification**: https://github.com/johannschopplich/toon-format
- **NPM Package**: https://www.npmjs.com/package/@toon-format/toon
- **CLI Tool**: https://www.npmjs.com/package/@toon-format/cli
