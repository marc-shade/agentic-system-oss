# SECURITY AND RELIABILITY AUDIT REPORT
**Autonomous Multi-Agent System**

**Date:** November 7, 2025
**Auditors:** Gemini CLI + Claude Code Analysis
**Scope:** System Health Guardian + System Remediation Agent
**Severity Levels:** CRITICAL | HIGH | MEDIUM | LOW

---

## EXECUTIVE SUMMARY

This audit identifies **6 CRITICAL** and **3 HIGH** severity issues in the autonomous agent system that MUST be addressed before production deployment. The system currently has fundamental security vulnerabilities and reliability gaps that could lead to:
- System compromise via symlink attacks
- Data corruption from race conditions
- Disk exhaustion from unbounded log growth
- Ineffective crash-loop protection
- Service restart failures going undetected

**RECOMMENDATION: DO NOT DEPLOY TO PRODUCTION** until at minimum the CRITICAL issues are resolved.

---

## CRITICAL SEVERITY ISSUES

### 🔴 CRITICAL-1: Insecure Temporary File Usage for IPC

**Category:** Security / Reliability / Data Loss
**Location:**
- `system_health_guardian.py:74` (recommendations_file)
- `system_health_guardian.py:73` (audit_log_path)
- `system_remediation_agent.py:66` (recommendations_file)
- `system_remediation_agent.py:67` (audit_log_path)

**Vulnerability:** Predictable file paths in world-writable `/tmp/` directory

**Attack Vectors:**
1. **Symlink Attack:** Attacker creates symlink from `/tmp/health_guardian_recommendations.json` to critical system file (e.g., `/etc/hosts`, `~/.bash_profile`). When guardian writes JSON data, it overwrites the target file → system compromise or command execution
2. **Recommendation Injection:** Attacker pre-creates `/tmp/health_guardian_recommendations.json` with malicious recommendations. Remediation agent blindly executes → denial of service or arbitrary code execution
3. **Directory-Based DoS:** Attacker creates directory named `health_guardian_recommendations.json` → prevents file creation → breaks entire monitoring loop

**Impact:**
- Arbitrary file overwrite on system
- Complete denial of service
- Potential arbitrary code execution
- System misconfiguration

**Fix Required:**
```python
# NEVER use /tmp for IPC or state
SECURE_RUN_DIR = "/Volumes/SSDRAID0/agentic-system/run/"

# Create secure directory with restricted permissions
os.makedirs(SECURE_RUN_DIR, mode=0o700, exist_ok=True)

# Use atomic writes
temp_file = f"{SECURE_RUN_DIR}/.recommendations.tmp"
final_file = f"{SECURE_RUN_DIR}/recommendations.json"

with open(temp_file, 'w') as f:
    json.dump(data, f)
os.rename(temp_file, final_file)  # Atomic on POSIX
```

---

### 🔴 CRITICAL-2: Race Condition in IPC Mechanism

**Category:** Reliability / Data Loss
**Location:**
- `system_health_guardian.py:559-589` (_write_recommendation)
- `system_remediation_agent.py:99-113` (gather_observations)

**Vulnerability:** Non-atomic read-modify-write sequence without file locking

**Failure Scenarios:**
1. **Lost Updates:** Guardian reads JSON → Remediation reads same stale JSON → Guardian writes update → Remediation acts on old data → New recommendation lost until next cycle
2. **Corrupted JSON:** Remediation reads file while Guardian is writing → Partial JSON read → JSON parse error → Remediation agent crashes → System fails to self-heal

**Impact:**
- Remediation agent crashes
- Recommendations lost
- Core self-healing functionality broken
- System remains in degraded state

**Fix Required:**
```python
import fcntl

def write_recommendation_safe(file_path, data):
    """Thread-safe, race-condition-free write"""
    temp_file = f"{file_path}.tmp"

    with open(temp_file, 'w') as f:
        # Acquire exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, indent=2)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Atomic rename
    os.rename(temp_file, file_path)

def read_recommendation_safe(file_path):
    """Thread-safe read"""
    with open(file_path, 'r') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock
        data = json.load(f)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return data
```

---

### 🔴 CRITICAL-3: Duplicated Logic and Conflicting State

**Category:** Reliability
**Location:** Both agents have duplicate restart logic

**Violation:** Observer-Actor pattern broken

**Problem:** Both `SystemHealthGuardian` and `SystemRemediationAgent` have:
- Independent `crash_history` dictionaries
- Independent `_should_restart_service()` methods
- Independent `_restart_service()` methods
- Independent `_investigate_service_failure()` methods

**Failure Scenario:**
```
1. Service is flapping
2. Guardian detects down, checks ITS crash_history → allows restart
3. Guardian attempts restart
4. Guardian writes recommendation
5. Remediation wakes up, reads recommendation
6. Remediation checks ITS OWN crash_history (empty!) → allows restart
7. Remediation ALSO attempts restart
8. Two concurrent restart attempts
9. Crash-loop protection completely bypassed
```

**Impact:**
- Crash-loop protection ineffective
- Resource exhaustion
- Multiple concurrent restart attempts
- System instability
- Maintenance nightmare (bug fixes needed in two places)

**Fix Required:**
```python
# system_health_guardian.py - REMOVE ALL EXECUTION LOGIC
# Observer should ONLY observe and write recommendations

class SystemHealthGuardian:
    def __init__(self):
        # REMOVE: self.crash_history
        # REMOVE: _restart_service()
        # REMOVE: _should_restart_service()
        # REMOVE: restart_service tool definition

    def _write_recommendation(self, service_name, action, reason):
        """ONLY job: write recommendations"""
        # No restart logic here!

# system_remediation_agent.py - SINGLE SOURCE OF TRUTH
# Actor is ONLY component that restarts services

class SystemRemediationAgent:
    def __init__(self):
        self.crash_history = {}  # ONLY copy

    def _should_restart_service(self):
        # ONLY implementation

    def _restart_service(self):
        # ONLY implementation
```

---

### 🔴 CRITICAL-4: Unbounded Log File Growth

**Category:** Reliability
**Location:**
- `system_health_guardian.py:640-651` (_audit_log)
- `system_remediation_agent.py:258-269` (_audit_log)
- Service stdout redirects (temporal, autokitteh)

**Problem:** No log rotation mechanism. Files opened in append mode indefinitely.

**Impact in 24/7 Operation:**
```
Day 1: 10 KB
Week 1: 70 KB
Month 1: 300 KB
Month 3: 900 KB
Month 6: 1.8 MB
Year 1: 3.6 MB
Year 2: 7.2 MB
...
Eventually: DISK FULL → agents crash → cascading system failure
```

**Fix Required:**
```python
import logging
from logging.handlers import RotatingFileHandler

# Replace manual file writes with logging framework
logger = logging.getLogger("SystemHealthGuardian")
handler = RotatingFileHandler(
    "/Volumes/SSDRAID0/agentic-system/logs/health_guardian.log",
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5  # Keep 5 backup files
)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Use it
logger.info("AUTO-RESTART: temporal")
```

---

### 🔴 CRITICAL-5: Missing Service Restart Verification

**Category:** Reliability
**Location:**
- `system_health_guardian.py:484-520` (_restart_service)
- `system_remediation_agent.py:144-194` (_restart_service)

**Problem:** `subprocess.Popen()` is non-blocking. Agents assume success immediately without verifying process actually started.

**Failure Scenario:**
```python
# Current code:
subprocess.Popen(["temporal", "server", "start-dev", ...])
return {"success": True}  # LIES! Don't know if it started

# What actually happens:
# 1. Popen returns immediately (success!)
# 2. Process starts
# 3. Port 7233 already in use
# 4. Process exits with error
# 5. Agent thinks service is running
# 6. No further restart attempts this cycle
# 7. Service remains down
```

**Impact:**
- False positive restart "success"
- Service remains down
- Feedback loop broken
- No remediation attempts until next cycle

**Fix Required:**
```python
import socket
import time

def _restart_service(self, service_name: str) -> Dict[str, Any]:
    """Restart service and VERIFY it started"""

    # Start process
    if service_name == "temporal":
        subprocess.Popen([...])
        port = 7233
    elif service_name == "autokitteh":
        subprocess.Popen([...])
        port = 9980
    # ...

    # VERIFY startup with health check
    max_attempts = 30  # 30 seconds
    for i in range(max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result == 0:
                return {"success": True, "verified": True}
        except:
            pass

        time.sleep(1)

    return {"success": False, "error": "Service did not start within 30s"}
```

---

### 🔴 CRITICAL-6: In-Memory Crash History Lost on Restart

**Category:** Reliability / Data Loss
**Location:**
- `system_health_guardian.py:71` (crash_history = {})
- `system_remediation_agent.py:68` (crash_history = {})

**Problem:** Crash history stored only in memory. Lost when agent restarts.

**Failure Scenario:**
```
06:00 - Temporal crashes (crash #1)
06:10 - Temporal crashes (crash #2)
06:20 - Temporal crashes (crash #3) → Max reached, investigation triggered
06:25 - Remediation agent crashes or is restarted
06:26 - Agent starts fresh, crash_history = {} (EMPTY!)
06:30 - Temporal down again
06:30 - Agent checks crash_history → EMPTY → restart allowed
06:30 - Crash loop continues undetected
```

**Impact:**
- Crash-loop protection completely bypassed on agent restart
- Infinite restart loops possible
- Resource exhaustion
- System instability

**Fix Required:**
```python
import json
import datetime

CRASH_HISTORY_FILE = "/Volumes/SSDRAID0/agentic-system/run/crash_history.json"

def _load_crash_history(self):
    """Load crash history from persistent storage"""
    if not os.path.exists(CRASH_HISTORY_FILE):
        return {}

    with open(CRASH_HISTORY_FILE, 'r') as f:
        data = json.load(f)

    # Clean up old entries
    now = datetime.datetime.now()
    for service, timestamps in data.items():
        data[service] = [
            ts for ts in timestamps
            if datetime.datetime.fromisoformat(ts) > now - datetime.timedelta(hours=1)
        ]

    return data

def _save_crash_history(self):
    """Persist crash history to disk"""
    # Convert datetime objects to ISO strings
    serializable = {
        service: [ts.isoformat() for ts in timestamps]
        for service, timestamps in self.crash_history.items()
    }

    with open(CRASH_HISTORY_FILE, 'w') as f:
        json.dump(serializable, f, indent=2)

def __init__(self):
    # Load from disk
    self.crash_history = self._load_crash_history()
```

---

## HIGH SEVERITY ISSUES

### 🟠 HIGH-1: Hardcoded User-Specific Paths

**Category:** Reliability / Portability
**Location:**
- `system_health_guardian.py:323`
- `system_remediation_agent.py:183`

**Problem:** PM2 path hardcoded to specific user's NVM directory

```python
# This will ONLY work for user 'marc' with this exact Node version
"/Users/marc/.nvm/versions/node/v24.3.0/bin/pm2"
```

**Impact:**
- Fails for any other user
- Fails if Node version changes
- Not portable across environments
- Breaks on system updates

**Fix:**
```python
# Option 1: Use PATH
result = subprocess.run(["pm2", "resurrect"], ...)

# Option 2: Configuration file
config = {
    "pm2_path": os.environ.get("PM2_PATH", "pm2")
}

# Option 3: Search for pm2
import shutil
pm2_path = shutil.which("pm2")
if not pm2_path:
    raise RuntimeError("pm2 not found in PATH")
```

---

### 🟠 HIGH-2: Arduino Serial Port Edge Cases

**Category:** Reliability
**Location:** `system_health_guardian.py:65` (ArduinoSurface initialization)

**Missing Edge Cases:**
1. Port doesn't exist (`/dev/tty.usbmodem8344401` not found)
2. Port exists but Arduino not responding
3. Arduino disconnects during operation
4. Serial port permissions denied
5. Port in use by another process

**Impact:**
- Agent crash on initialization
- Undefined behavior during operation
- No graceful degradation

**Fix Required:**
```python
def __init__(self, arduino_port: str):
    try:
        if not os.path.exists(arduino_port):
            logger.warning(f"Arduino port {arduino_port} not found. Running without hardware.")
            self.surface = None
        else:
            self.surface = ArduinoSurface(arduino_port)
    except Exception as e:
        logger.error(f"Failed to initialize Arduino: {e}")
        logger.warning("Running without Arduino hardware")
        self.surface = None

def execute_decision(self, decision, observations):
    # Check if Arduino available before using
    if self.surface:
        self.surface.display_text(line1, line2)
    # Continue without Arduino if not available
```

---

### 🟠 HIGH-3: Missing Error Handling in Service Monitoring

**Category:** Reliability
**Location:** `system_health_guardian.py:214-313` (_check_service_status)

**Problem:** Multiple subprocess calls with minimal error handling

```python
# What if lsof hangs?
result = subprocess.run(["lsof", "-ti:7233"], timeout=2)

# What if pgrep crashes?
result = subprocess.run(["pgrep", "-f", "pattern"])

# What if nc is not installed?
result = subprocess.run(["nc", "-z", "localhost", "9980"])
```

**Missing:**
- Timeout handling for hanging commands
- Alternative check methods if tool unavailable
- Graceful degradation
- Error reporting vs. crashing

**Fix Required:**
```python
def _check_port(self, port: int) -> bool:
    """Robust port check with multiple fallback methods"""
    # Method 1: Try socket connection (most reliable)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.debug(f"Socket check failed: {e}")

    # Method 2: Try lsof
    try:
        result = subprocess.run(
            ["lsof", f"-ti:{port}"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug(f"lsof check failed: {e}")

    # Method 3: Try netstat
    try:
        result = subprocess.run(
            ["netstat", "-an"],
            capture_output=True,
            timeout=5,
            text=True
        )
        return f":{port}" in result.stdout
    except Exception as e:
        logger.debug(f"netstat check failed: {e}")

    logger.warning(f"All port check methods failed for {port}")
    return False  # Conservative: assume down
```

---

## RECOMMENDATIONS SUMMARY

### Immediate Actions (Before Production):
1. ✅ Move all IPC files from `/tmp/` to secure directory
2. ✅ Implement file locking for all JSON operations
3. ✅ Remove duplicate restart logic from Health Guardian
4. ✅ Implement log rotation with Python logging module
5. ✅ Add health checks after service restarts
6. ✅ Persist crash history to disk

### High Priority (Next Sprint):
7. ✅ Remove hardcoded paths, use configuration
8. ✅ Add Arduino error handling and graceful degradation
9. ✅ Improve service monitoring error handling

### System Design Improvements:
10. ✅ Consider using message queue instead of JSON files (Redis, ZMQ, etc.)
11. ✅ Add monitoring for the monitors (watchdog for agents)
12. ✅ Implement circuit breaker pattern for crash-looping services
13. ✅ Add metrics collection (Prometheus/Grafana)
14. ✅ Create runbook for common failure scenarios

---

## CONCLUSION

**Current Risk Level: HIGH**

The system has fundamental security and reliability issues that make it **unsuitable for production deployment** in its current state. The CRITICAL issues represent real attack vectors and failure modes that WILL occur in a 24/7 production environment.

**Estimated Remediation Time:** 2-3 days for CRITICAL issues

**Testing Required After Fixes:**
- Symlink attack resistance testing
- Concurrent access stress testing
- Disk full scenario testing
- Agent restart scenario testing
- Service crash-loop scenario testing
- Week-long soak test

---

**Report Generated:** November 7, 2025
**Auditor:** Gemini CLI
**Next Review:** After CRITICAL issues resolved
