#!/usr/bin/env python3
"""
System Event Optimizer - AutoKitteh Handler
Responds to system events and optimizes configuration in real-time

INTEGRATION: Uses agentic marker system to signal intentional changes
STATUS: Production Ready
TRIGGERS: High memory, high CPU, error spikes, MCP latency
"""

import json
import os
import platform
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent


_STORAGE_BASE = _get_storage_base()

# Add intelligent healing system to path
sys.path.insert(0, str(_STORAGE_BASE / 'intelligent-self-healing'))
from intelligent_config_agent import IntelligentConfigAgent


class SystemEventOptimizer:
    """Real-time optimizer responding to system events"""

    def __init__(self):
        self.agent = IntelligentConfigAgent()
        self.settings_file = Path.home() / ".claude" / "settings.json"
        self.mcp_config_file = Path.home() / ".claude.json"
        self.event_log = Path("/tmp/autokitteh_events.jsonl")

    def log_event(self, event: Dict):
        """Log event for analysis"""
        with open(self.event_log, 'a') as f:
            f.write(json.dumps(event) + '\n')

    def handle_high_memory_event(self, memory_percent: float) -> Dict:
        """
        Handle high memory usage event

        Args:
            memory_percent: Current memory usage (0.0-1.0)

        Returns:
            Optimization result
        """
        if memory_percent < 0.85:
            return {"status": "ok", "message": "Memory usage normal"}

        print(f"⚠️  High memory detected: {memory_percent:.1%}")

        # Check if we can optimize caching
        is_modifiable, reason = self.agent.is_key_modifiable("cachingStrategy")
        if not is_modifiable:
            print(f"⚠️  Cannot optimize caching: {reason}")
            return {"status": "skipped", "reason": reason}

        # Load current settings
        with open(self.settings_file, 'r') as f:
            settings = json.load(f)

        old_strategy = settings.get('cachingStrategy', 'aggressive')

        # Only change if currently aggressive
        if old_strategy == 'conservative':
            return {"status": "already_optimized", "message": "Caching already conservative"}

        # Optimize: reduce caching to free memory
        settings['cachingStrategy'] = 'conservative'

        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        session_id = f"autokitteh_memory_{int(memory_percent*100)}"

        # Mark change using marker system
        self.agent.mark_agentic_change(
            file="settings.json",
            key="cachingStrategy",
            reason=f"Memory usage at {memory_percent:.1%}, reducing caching to free memory",
            change_type="agentic_optimization",
            confidence=0.93,
            session_id=session_id
        )

        print(f"✅ Optimized caching: {old_strategy} → conservative")

        # Notify user
        self.agent.notify_change(
            change_info={
                "event": "high_memory",
                "memory_percent": memory_percent,
                "optimization": "caching_reduced",
                "reason": f"Reduced caching due to {memory_percent:.1%} memory usage"
            },
            severity="warning",
            use_voice=True
        )

        # Log event
        self.log_event({
            "timestamp": datetime.now().isoformat(),
            "event_type": "high_memory",
            "memory_percent": memory_percent,
            "optimization": {
                "key": "cachingStrategy",
                "old": old_strategy,
                "new": "conservative"
            }
        })

        return {
            "status": "optimized",
            "key": "cachingStrategy",
            "old_value": old_strategy,
            "new_value": "conservative",
            "confidence": 0.93
        }

    def handle_high_cpu_event(self, cpu_percent: float) -> Dict:
        """
        Handle high CPU usage event

        Args:
            cpu_percent: Current CPU usage (0.0-1.0)

        Returns:
            Optimization result
        """
        if cpu_percent < 0.90:
            return {"status": "ok", "message": "CPU usage normal"}

        print(f"⚠️  High CPU detected: {cpu_percent:.1%}")

        # Check if we can optimize parallel tools
        is_modifiable, reason = self.agent.is_key_modifiable("maxParallelTools")
        if not is_modifiable:
            print(f"⚠️  Cannot optimize parallel tools: {reason}")
            return {"status": "skipped", "reason": reason}

        # Load current settings
        with open(self.settings_file, 'r') as f:
            settings = json.load(f)

        current_parallel = settings.get('maxParallelTools', 10)

        # Reduce parallel execution to ease CPU
        new_parallel = max(2, current_parallel - 2)  # Reduce by 2, min 2

        if new_parallel == current_parallel:
            return {"status": "already_optimized", "message": "Parallel tools already minimal"}

        settings['maxParallelTools'] = new_parallel

        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        session_id = f"autokitteh_cpu_{int(cpu_percent*100)}"

        # Mark change
        self.agent.mark_agentic_change(
            file="settings.json",
            key="maxParallelTools",
            reason=f"CPU at {cpu_percent:.1%}, reducing parallel tools to ease load",
            change_type="agentic_optimization",
            confidence=0.91,
            session_id=session_id
        )

        print(f"✅ Reduced parallel tools: {current_parallel} → {new_parallel}")

        # Notify
        self.agent.notify_change(
            change_info={
                "event": "high_cpu",
                "cpu_percent": cpu_percent,
                "optimization": "parallel_reduced"
            },
            severity="warning",
            use_voice=True
        )

        # Log
        self.log_event({
            "timestamp": datetime.now().isoformat(),
            "event_type": "high_cpu",
            "cpu_percent": cpu_percent,
            "optimization": {
                "key": "maxParallelTools",
                "old": current_parallel,
                "new": new_parallel
            }
        })

        return {
            "status": "optimized",
            "key": "maxParallelTools",
            "old_value": current_parallel,
            "new_value": new_parallel,
            "confidence": 0.91
        }

    def handle_error_spike_event(self, error_rate: float) -> Dict:
        """
        Handle error rate spike

        Args:
            error_rate: Current error rate (0.0-1.0)

        Returns:
            Optimization result
        """
        if error_rate < 0.10:  # <10% error rate
            return {"status": "ok", "message": "Error rate normal"}

        print(f"⚠️  Error spike detected: {error_rate:.1%}")

        # Check if we can enable debug logging
        is_modifiable, reason = self.agent.is_key_modifiable("loggingLevel")
        if not is_modifiable:
            print(f"⚠️  Cannot modify logging: {reason}")
            return {"status": "skipped", "reason": reason}

        # Load current settings
        with open(self.settings_file, 'r') as f:
            settings = json.load(f)

        current_level = settings.get('loggingLevel', 'INFO')

        # Enable debug logging for analysis
        if current_level == 'DEBUG':
            return {"status": "already_optimized", "message": "Debug logging already enabled"}

        settings['loggingLevel'] = 'DEBUG'

        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        session_id = f"autokitteh_errors_{int(error_rate*100)}"

        # Mark change
        self.agent.mark_agentic_change(
            file="settings.json",
            key="loggingLevel",
            reason=f"Error rate at {error_rate:.1%}, enabling debug logging for analysis",
            change_type="agentic_optimization",
            confidence=0.90,
            session_id=session_id
        )

        print(f"✅ Enabled debug logging: {current_level} → DEBUG")

        # Notify
        self.agent.notify_change(
            change_info={
                "event": "error_spike",
                "error_rate": error_rate,
                "optimization": "debug_logging_enabled"
            },
            severity="error",
            use_voice=True
        )

        # Log
        self.log_event({
            "timestamp": datetime.now().isoformat(),
            "event_type": "error_spike",
            "error_rate": error_rate,
            "optimization": {
                "key": "loggingLevel",
                "old": current_level,
                "new": "DEBUG"
            }
        })

        return {
            "status": "optimized",
            "key": "loggingLevel",
            "old_value": current_level,
            "new_value": "DEBUG",
            "confidence": 0.90
        }

    def handle_mcp_latency_event(self, server_name: str, avg_latency_ms: float) -> Dict:
        """
        Handle MCP server latency spike

        Args:
            server_name: MCP server name
            avg_latency_ms: Average latency in milliseconds

        Returns:
            Optimization result
        """
        if avg_latency_ms < 1000:  # <1s latency
            return {"status": "ok", "message": "Latency normal"}

        print(f"⚠️  MCP latency spike detected: {server_name} at {avg_latency_ms}ms")

        # Check if we can modify timeout
        key = f"mcpServers.{server_name}.timeout"
        is_modifiable, reason = self.agent.is_key_modifiable(key)
        if not is_modifiable:
            print(f"⚠️  Cannot modify timeout: {reason}")
            return {"status": "skipped", "reason": reason}

        # Load MCP config
        with open(self.mcp_config_file, 'r') as f:
            config = json.load(f)

        # Check if server exists
        if server_name not in config.get('mcpServers', {}):
            return {"status": "error", "message": f"Server {server_name} not in config"}

        # Calculate optimal timeout (3x latency + buffer)
        optimal_timeout = int(avg_latency_ms * 3 + 1000)
        current_timeout = config['mcpServers'][server_name].get('timeout', 5000)

        # Only change if significantly different
        if abs(optimal_timeout - current_timeout) < 500:
            return {"status": "already_optimized", "message": "Timeout already optimal"}

        # Update timeout
        config['mcpServers'][server_name]['timeout'] = optimal_timeout

        with open(self.mcp_config_file, 'w') as f:
            json.dump(config, f, indent=2)

        session_id = f"autokitteh_mcp_{server_name}_{int(avg_latency_ms)}"

        # Mark change
        self.agent.mark_agentic_change(
            file=".claude.json",
            key=key,
            reason=f"Latency at {avg_latency_ms}ms, optimizing timeout for reliability",
            change_type="agentic_optimization",
            confidence=0.88,
            session_id=session_id
        )

        print(f"✅ Optimized {server_name} timeout: {current_timeout}ms → {optimal_timeout}ms")

        # Notify
        self.agent.notify_change(
            change_info={
                "event": "mcp_latency",
                "server": server_name,
                "latency_ms": avg_latency_ms,
                "optimization": "timeout_adjusted"
            },
            severity="warning",
            use_voice=False  # Don't spam for MCP optimizations
        )

        # Log
        self.log_event({
            "timestamp": datetime.now().isoformat(),
            "event_type": "mcp_latency",
            "server_name": server_name,
            "latency_ms": avg_latency_ms,
            "optimization": {
                "key": key,
                "old": current_timeout,
                "new": optimal_timeout
            }
        })

        return {
            "status": "optimized",
            "key": key,
            "old_value": current_timeout,
            "new_value": optimal_timeout,
            "confidence": 0.88
        }


# AutoKitteh Event Handlers
def on_high_memory(event: Dict) -> Dict:
    """AutoKitteh handler for high memory events"""
    optimizer = SystemEventOptimizer()
    memory_percent = event.get('memory_percent', 0)
    return optimizer.handle_high_memory_event(memory_percent)


def on_high_cpu(event: Dict) -> Dict:
    """AutoKitteh handler for high CPU events"""
    optimizer = SystemEventOptimizer()
    cpu_percent = event.get('cpu_percent', 0)
    return optimizer.handle_high_cpu_event(cpu_percent)


def on_error_spike(event: Dict) -> Dict:
    """AutoKitteh handler for error spike events"""
    optimizer = SystemEventOptimizer()
    error_rate = event.get('error_rate', 0)
    return optimizer.handle_error_spike_event(error_rate)


def on_mcp_latency(event: Dict) -> Dict:
    """AutoKitteh handler for MCP latency events"""
    optimizer = SystemEventOptimizer()
    server_name = event.get('server_name', 'unknown')
    avg_latency = event.get('avg_latency_ms', 0)
    return optimizer.handle_mcp_latency_event(server_name, avg_latency)


# Standalone testing
def main_test():
    """Test event handlers in standalone mode"""
    print("=" * 60)
    print("🔧 System Event Optimizer - Test Mode")
    print("=" * 60)
    print()

    optimizer = SystemEventOptimizer()

    # Test 1: High memory event
    print("Test 1: High Memory Event (92%)")
    result = optimizer.handle_high_memory_event(0.92)
    print(f"Result: {result['status']}")
    print()

    # Test 2: High CPU event
    print("Test 2: High CPU Event (95%)")
    result = optimizer.handle_high_cpu_event(0.95)
    print(f"Result: {result['status']}")
    print()

    # Test 3: Error spike
    print("Test 3: Error Spike (15%)")
    result = optimizer.handle_error_spike_event(0.15)
    print(f"Result: {result['status']}")
    print()

    # Test 4: MCP latency
    print("Test 4: MCP Latency (voice-mode, 3500ms)")
    result = optimizer.handle_mcp_latency_event('voice-mode', 3500)
    print(f"Result: {result['status']}")
    print()

    print("=" * 60)
    print("✅ All event handlers tested")
    print("=" * 60)


if __name__ == "__main__":
    # Run tests in standalone mode
    main_test()
