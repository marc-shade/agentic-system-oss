#!/usr/bin/env python3
"""
Claude Code Metrics Exporter for XRG
Production service that exposes Claude usage metrics via HTTP endpoint
Reads from Claude Code logs in real-time
"""

import sqlite3
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import threading
import time

DB_PATH = Path.home() / ".claude" / "monitoring" / "claude_usage.db"
CLAUDE_LOG = Path.home() / ".claude" / "logs" / "claude-code.log"
API_REQUESTS_LOG = Path.home() / ".claude" / "monitoring" / "api_requests.log"

# Pricing per 1M tokens (input, output)
PRICING = {
    "claude-sonnet-4.5": (3.00, 15.00),
    "claude-sonnet-3.5": (3.00, 15.00),
    "claude-opus": (15.00, 75.00),
    "gpt-4": (30.00, 60.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "gemini-pro": (0.50, 1.50),
    "gemini-ultra": (0.50, 1.50),
    "groq": (0.10, 0.10),
    "mistral": (0.25, 0.25),
    "together": (0.20, 0.20),
    "default": (3.00, 15.00)  # Claude Sonnet default
}

# Global metrics cache - now tracking by service
metrics_cache = {
    "claude_input": 0,
    "claude_output": 0,
    "codex_input": 0,
    "codex_output": 0,
    "gemini_input": 0,
    "gemini_output": 0,
    "other_input": 0,
    "other_output": 0,
    "total_cost": 0.0,
    "last_update": None,
    "log_positions": {}  # Track file positions for multiple logs
}
cache_lock = threading.Lock()


class MetricsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging
    
    def do_GET(self):
        if self.path == '/v1/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            
            with cache_lock:
                # Calculate totals
                total_input = (metrics_cache["claude_input"] + metrics_cache["codex_input"] +
                              metrics_cache["gemini_input"] + metrics_cache["other_input"])
                total_output = (metrics_cache["claude_output"] + metrics_cache["codex_output"] +
                               metrics_cache["gemini_output"] + metrics_cache["other_output"])

                output = []
                output.append("# HELP claude_code_token_usage Token usage by type")
                output.append("# TYPE claude_code_token_usage counter")
                output.append(f'claude_code_token_usage{{type="input"}} {total_input}')
                output.append(f'claude_code_token_usage{{type="output"}} {total_output}')
                output.append(f'claude_code_token_usage{{type="cache_read"}} 0')
                output.append(f'claude_code_token_usage{{type="cache_create"}} 0')
                output.append("")
                output.append("# HELP claude_code_cost_usage API cost in USD")
                output.append("# TYPE claude_code_cost_usage counter")
                output.append(f'claude_code_cost_usage {metrics_cache["total_cost"]:.4f}')
                output.append("")
                # Per-service metrics
                output.append("# HELP ai_service_tokens Token usage by AI service")
                output.append("# TYPE ai_service_tokens counter")
                output.append(f'ai_service_tokens{{service="claude",type="input"}} {metrics_cache["claude_input"]}')
                output.append(f'ai_service_tokens{{service="claude",type="output"}} {metrics_cache["claude_output"]}')
                output.append(f'ai_service_tokens{{service="codex",type="input"}} {metrics_cache["codex_input"]}')
                output.append(f'ai_service_tokens{{service="codex",type="output"}} {metrics_cache["codex_output"]}')
                output.append(f'ai_service_tokens{{service="gemini",type="input"}} {metrics_cache["gemini_input"]}')
                output.append(f'ai_service_tokens{{service="gemini",type="output"}} {metrics_cache["gemini_output"]}')
                output.append(f'ai_service_tokens{{service="other",type="input"}} {metrics_cache["other_input"]}')
                output.append(f'ai_service_tokens{{service="other",type="output"}} {metrics_cache["other_output"]}')

                self.wfile.write("\n".join(output).encode() + b"\n")
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health = {"status": "healthy", "last_update": metrics_cache["last_update"]}
            self.wfile.write(json.dumps(health).encode())
        else:
            self.send_response(404)
            self.end_headers()


def parse_token_line(line):
    """Parse token usage from Claude Code log line"""
    match = re.search(r'Token usage:\s*input=(\d+),\s*output=(\d+)', line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def calculate_cost(input_tokens, output_tokens):
    """Calculate API cost in USD"""
    input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    return input_cost + output_cost

def update_metrics_from_logs():
    """Real-time monitoring of Claude Code logs"""
    print(f"Monitoring Claude Code logs: {CLAUDE_LOG}")

    while True:
        try:
            if not CLAUDE_LOG.exists():
                time.sleep(1)
                continue

            with open(CLAUDE_LOG, 'r') as f:
                # Seek to last known position
                with cache_lock:
                    pos = metrics_cache["log_position"]
                f.seek(pos)

                # Read new lines
                new_lines = f.readlines()

                if new_lines:
                    for line in new_lines:
                        input_tokens, output_tokens = parse_token_line(line)

                        if input_tokens is not None:
                            with cache_lock:
                                # Add to cumulative totals
                                metrics_cache["input_tokens"] += input_tokens
                                metrics_cache["output_tokens"] += output_tokens

                                # Calculate and add cost
                                call_cost = calculate_cost(input_tokens, output_tokens)
                                metrics_cache["total_cost"] += call_cost

                                metrics_cache["last_update"] = datetime.now().isoformat()

                                # Log to console
                                total_in = metrics_cache["input_tokens"]
                                total_out = metrics_cache["output_tokens"]
                                total_cost = metrics_cache["total_cost"]
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                      f"+{input_tokens} in, +{output_tokens} out | "
                                      f"Total: {total_in:,} in, {total_out:,} out | "
                                      f"${total_cost:.4f}")

                    # Update position
                    with cache_lock:
                        metrics_cache["log_position"] = f.tell()

        except Exception as e:
            print(f"Error reading logs: {e}")

        time.sleep(0.5)  # Check for new log lines every 500ms


if __name__ == "__main__":
    # Start background log monitor
    log_monitor = threading.Thread(target=update_metrics_from_logs, daemon=True)
    log_monitor.start()

    # Start HTTP server
    server = HTTPServer(('localhost', 4318), MetricsHandler)
    print("Claude Code Metrics Exporter running on http://localhost:4318/v1/metrics")
    print("Health check: http://localhost:4318/health")
    print("Tracking live Claude Code token usage from logs")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        with cache_lock:
            print(f"Final totals: {metrics_cache['input_tokens']:,} input, "
                  f"{metrics_cache['output_tokens']:,} output, "
                  f"${metrics_cache['total_cost']:.2f}")
        server.shutdown()
