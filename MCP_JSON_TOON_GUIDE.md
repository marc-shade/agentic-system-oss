# MCP Server Data Format Guide: JSON vs TOON

## Critical Distinction

**JSON (JavaScript Object Notation)** and **TOON (Typed Object Oriented Notation)** are NOT interchangeable. Each MCP server must consistently use one format throughout its codebase.

## MCP Protocol Requirement

The **MCP (Model Context Protocol) specification** requires **JSON-RPC 2.0** format, which means:
- All stdin/stdout communication MUST be valid JSON
- All tool responses MUST be valid JSON
- All error messages MUST be valid JSON-RPC 2.0 format

## Current System Architecture

### Standard Pattern: Pure JSON

**All active MCP servers use JSON:**

```python
# Correct pattern - used by all active servers
import json

def send_response(response: dict):
    """Send MCP response to stdout"""
    print(json.dumps(response), flush=True)

def send_result(request_id: str, result: dict):
    """Send success response"""
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    })
```

**Verified JSON-only servers:**
- ✅ `enhanced-memory-mcp` - Pure JSON
- ✅ `agent-runtime-mcp` - Pure JSON
- ✅ `agi-mcp` - Pure JSON
- ✅ `research-paper-mcp` - Pure JSON
- ✅ `video-transcript-mcp` - Pure JSON
- ✅ `cluster-execution-mcp` - Pure JSON
- ✅ `arduino-surface` (both versions) - Pure JSON

### Optional Pattern: TOON with JSON Fallback

**Only nuclei-mcp uses TOON** (with proper fallback):

```python
# TOON with graceful fallback
import sys
from pathlib import Path

# Add SHARED to path for TOON utilities
sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

# Import TOON utilities for token-optimized responses
try:
    from toon_utils import toon_response, estimate_token_savings
    TOON_ENABLED = True
except ImportError:
    # Fallback to JSON if TOON not available
    TOON_ENABLED = False
    def toon_response(data, **kwargs):
        import json
        return json.dumps(data)
```

## TOON Infrastructure

**Location**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/SHARED/`

**Purpose**: Token-optimized responses for reduced context usage

**Files**:
- `toon_utils.py` - Core TOON utilities
- `toon_codec.py` - TOON encoding/decoding
- `demo_token_savings.py` - Token savings demonstrations
- `validate_toon_rollout.py` - Validation tools

**Status**: ⚠️ **EXPERIMENTAL** - Only used by nuclei-mcp with fallback

## Decision Matrix: When to Use What

### Use JSON (Default - Recommended)

✅ **Use JSON when:**
- Building standard MCP servers
- Maximum compatibility is required
- You need Claude Desktop to parse responses
- You're creating cluster-aware or distributed servers
- You want simple, maintainable code

**Example**: All production MCP servers (enhanced-memory, agent-runtime, etc.)

### Use TOON (Advanced - Experimental)

⚠️ **Only consider TOON when:**
- You have TOON utilities available and tested
- Token reduction is critical (>50% context savings needed)
- You implement proper JSON fallback
- You're willing to maintain custom serialization

**Example**: nuclei-mcp (security scanning with large reports)

## Migration Guidance

### If You Have TOON Code Without Libraries

**Problem**: Code references `_encode_response()` or TOON but libraries not available

**Solution**: Replace with JSON

```python
# OLD (TOON - doesn't work without libraries)
from toon_utils import _encode_response
result = _encode_response(data)

# NEW (JSON - always works)
import json
result = json.dumps(data)
```

### If You Want to Add TOON Support

**Requirements**:
1. Ensure `SHARED/toon_utils.py` exists and works
2. Test TOON encoding/decoding thoroughly
3. Implement JSON fallback (MANDATORY)
4. Document token savings with benchmarks

**Template**:
```python
# Add TOON with proper fallback
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "SHARED"))

try:
    from toon_utils import toon_response, estimate_token_savings
    TOON_ENABLED = True
except ImportError:
    TOON_ENABLED = False
    import json
    def toon_response(data, **kwargs):
        return json.dumps(data)

# Use toon_response() everywhere instead of json.dumps()
def send_result(request_id: str, result: dict):
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }
    print(toon_response(response), flush=True)
```

## Verification Checklist

Before deploying any MCP server:

- [ ] Check imports: `grep -E "import json|from.*toon" server.py`
- [ ] Verify serialization: `grep -E "json\.dumps|toon_response" server.py`
- [ ] Test with MCP client: Send initialize, tools/list, tools/call
- [ ] Check responses are valid JSON: `python3 -m json.tool < response.json`
- [ ] If using TOON: Verify fallback works when SHARED unavailable
- [ ] Document format choice in server docstring

## Common Issues

### Issue 1: Mixed JSON/TOON Usage

**Symptom**: Some responses JSON, others TOON
**Fix**: Choose one format and use consistently

### Issue 2: TOON Without Fallback

**Symptom**: Server crashes when TOON libraries unavailable
**Fix**: Add try/except with JSON fallback (see template above)

### Issue 3: Invalid JSON-RPC Format

**Symptom**: Claude Desktop can't parse responses
**Fix**: Ensure all responses have `"jsonrpc": "2.0"` and proper structure

### Issue 4: Merge Conflicts with TOON Code

**Symptom**: `_encode_response` references in merged code
**Fix**: Replace with `json.dumps()` unless TOON libraries confirmed working

## Best Practices

1. **Default to JSON** - It always works, is well-tested, and is the MCP standard
2. **Document your choice** - State clearly in README and server docstring
3. **Test fallbacks** - If using TOON, verify JSON fallback works
4. **Verify compatibility** - Test with actual Claude Desktop MCP client
5. **Measure token savings** - Only use TOON if you can prove >30% savings
6. **Version carefully** - TOON changes could break existing integrations

## Status of This System

**Current State** (2025-01-21):
- ✅ All 7 active Python MCP servers use **pure JSON**
- ⚠️ 1 server (nuclei-mcp) has **TOON with JSON fallback**
- ✅ Arduino cluster-aware MCP uses **pure JSON**
- ✅ No broken TOON references in production code

**Recommendation**: Continue using **pure JSON** for all new MCP servers unless you have specific token reduction requirements and can commit to maintaining TOON infrastructure.

## References

- MCP Specification: https://modelcontextprotocol.io/specification
- JSON-RPC 2.0: https://www.jsonrpc.org/specification
- TOON Implementation: `/Volumes/SSDRAID0/agentic-system/mcp-servers/SHARED/`
