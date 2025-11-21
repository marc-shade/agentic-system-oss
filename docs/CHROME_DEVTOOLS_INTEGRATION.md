# Chrome DevTools MCP Integration Guide

**Date**: 2025-11-10
**Status**: Active Integration
**Purpose**: Automated web testing, performance monitoring, and browser automation

---

## Overview

Chrome DevTools MCP provides programmatic access to Chrome browser capabilities for:
- Automated web application testing
- Performance monitoring (Core Web Vitals)
- Network request inspection
- Console error detection
- Screenshot capture
- UI interaction testing

## Available Tools

### Page Management
- `mcp__chrome-devtools__navigate_page` - Navigate to URL
- `mcp__chrome-devtools__new_page` - Open new tab
- `mcp__chrome-devtools__close_page` - Close tab
- `mcp__chrome-devtools__select_page` - Switch active tab
- `mcp__chrome-devtools__list_pages` - List all open tabs
- `mcp__chrome-devtools__resize_page` - Resize viewport

### Interaction
- `mcp__chrome-devtools__click` - Click element by UID
- `mcp__chrome-devtools__fill` - Fill input field
- `mcp__chrome-devtools__fill_form` - Fill multiple form fields
- `mcp__chrome-devtools__hover` - Hover over element
- `mcp__chrome-devtools__drag` - Drag and drop
- `mcp__chrome-devtools__upload_file` - Upload file
- `mcp__chrome-devtools__wait_for` - Wait for text to appear

### Inspection
- `mcp__chrome-devtools__take_snapshot` - Text snapshot with UIDs
- `mcp__chrome-devtools__take_screenshot` - Capture screenshot (PNG/JPEG/WebP)
- `mcp__chrome-devtools__list_console_messages` - Console logs and errors
- `mcp__chrome-devtools__list_network_requests` - Network activity
- `mcp__chrome-devtools__get_network_request` - Specific request details

### Performance
- `mcp__chrome-devtools__performance_start_trace` - Start performance recording
- `mcp__chrome-devtools__performance_stop_trace` - Stop and analyze
- `mcp__chrome-devtools__performance_analyze_insight` - Deep performance analysis
- `mcp__chrome-devtools__emulate_cpu` - CPU throttling
- `mcp__chrome-devtools__emulate_network` - Network throttling

### Scripting
- `mcp__chrome-devtools__evaluate_script` - Execute JavaScript
- `mcp__chrome-devtools__handle_dialog` - Handle browser dialogs

---

## Integration Patterns

### 1. Automated Testing Workflow

```python
from intelligent_agents.web_testing_agent import run_test_suite

# Run basic test suite
results = run_test_suite(
    url="http://localhost:3000",
    test_suite="basic"  # or "performance" or "full"
)

# Results include:
# - Navigation success
# - Console errors (if any)
# - Network request failures
# - Performance metrics (if requested)
# - Screenshots (if requested)
```

### 2. Performance Monitoring

```python
# Start performance trace
mcp__chrome-devtools__performance_start_trace({
    "reload": True,
    "autoStop": True
})

# Analyze Core Web Vitals
insights = mcp__chrome-devtools__performance_analyze_insight({
    "insightName": "LCPBreakdown"  # Largest Contentful Paint
})
```

### 3. Console Error Detection

```python
# Navigate and check console
mcp__chrome-devtools__navigate_page({
    "url": "http://localhost:3000"
})

# Get console messages
messages = mcp__chrome-devtools__list_console_messages()

# Filter errors
errors = [m for m in messages if m['level'] == 'error']
```

### 4. Network Request Inspection

```python
# List all network requests
requests = mcp__chrome-devtools__list_network_requests({
    "resourceTypes": ["xhr", "fetch"],  # Filter by type
    "pageSize": 50
})

# Check for failed requests
failed = [r for r in requests if r['status'] >= 400]
```

### 5. Screenshot Capture

```python
# Capture full page screenshot
mcp__chrome-devtools__take_screenshot({
    "fullPage": True,
    "format": "png",
    "filePath": "/path/to/screenshot.png"
})

# Capture specific element
mcp__chrome-devtools__take_screenshot({
    "uid": "element-uid-from-snapshot",
    "format": "jpeg",
    "quality": 90
})
```

---

## Use Cases

### 1. CI/CD Integration
- Automated regression testing on every deploy
- Performance budget enforcement
- Visual regression detection

### 2. Monitoring Dashboard Testing
- Verify dashboard data loads correctly
- Check real-time updates
- Validate chart rendering
- Test user interactions

### 3. API Integration Testing
- Monitor network requests
- Validate request/response format
- Check authentication flows
- Verify error handling

### 4. Accessibility Testing
- Keyboard navigation
- Screen reader compatibility
- Color contrast validation
- ARIA attribute verification

### 5. Performance Optimization
- Core Web Vitals tracking
- Resource loading analysis
- JavaScript execution profiling
- Network waterfall inspection

---

## Task Consumer Integration

The web testing agent is integrated with the task consumer. Tasks containing keywords like:
- "test web", "test website", "test application"
- "check performance", "performance test"
- "screenshot", "capture page"
- "console errors", "network errors"

Will be automatically routed to the web testing agent.

---

## Example Workflows

### Basic Health Check
```python
# Quick health check for production site
results = run_test_suite(
    url="https://production-site.com",
    test_suite="basic"
)

if results['summary']['failed'] > 0:
    # Alert on failures
    send_alert(results)
```

### Performance Regression Test
```python
# Compare performance against baseline
results = run_test_suite(
    url="http://staging.example.com",
    test_suite="performance"
)

metrics = results['tests'][3]['metrics']  # Performance test
if metrics['LCP'] > '2.5s':
    fail_build("LCP regression detected")
```

### Visual Regression Test
```python
# Capture screenshots for comparison
results = run_test_suite(
    url="http://localhost:3000",
    test_suite="full"
)

screenshot_path = results['tests'][4]['file_path']
compare_with_baseline(screenshot_path)
```

---

## Configuration

Chrome DevTools MCP is configured in `~/.claude.json`:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "node",
      "args": ["/path/to/chrome-devtools-mcp/build/src/index.js"],
      "env": {
        "NODE_ENV": "production"
      }
    }
  }
}
```

---

## Troubleshooting

### Chrome not found
Ensure Chrome/Chromium is installed and in PATH.

### Connection timeout
Increase timeout in tool parameters:
```python
mcp__chrome-devtools__navigate_page({
    "url": "...",
    "timeout": 30000  # 30 seconds
})
```

### Element not found
Use `take_snapshot` first to get current UIDs:
```python
snapshot = mcp__chrome-devtools__take_snapshot()
# Find element UID in snapshot
# Then use UID in click/fill operations
```

---

## Future Enhancements

1. **Parallel Testing**: Run multiple test suites concurrently
2. **Test Reports**: Generate HTML test reports with screenshots
3. **Video Recording**: Capture test execution videos
4. **Accessibility Scoring**: Automated WCAG compliance checks
5. **A/B Testing**: Compare two versions side-by-side

---

## References

- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/
- Core Web Vitals: https://web.dev/vitals/
- Web Testing Best Practices: https://web.dev/testing/

---

**Last Updated**: 2025-11-10
**Maintained By**: Intelligent Agents System
