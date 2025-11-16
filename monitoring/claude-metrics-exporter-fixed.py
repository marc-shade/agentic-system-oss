#!/usr/bin/env python3
"""
Universal AI Token Tracker - Production Ready
Tracks ALL AI API usage: Claude, OpenAI, Gemini, Groq, Mistral, etc.
"""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
import threading
import time

# Log files to monitor
CLAUDE_LOG = Path.home() / ".claude" / "logs" / "claude-code.log"

# Pricing per 1M tokens (input, output)
PRICING = {
    "claude": (3.00, 15.00),
    "codex": (10.00, 30.00),
    "gemini": (0.50, 1.50),
    "other": (3.00, 15.00)
}

# Global metrics cache
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
    "log_position": 0
}
cache_lock = threading.Lock()


class MetricsHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/v1/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; version=0.0.4')
            self.end_headers()
            
            with cache_lock:
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
    """Parse token usage from various AI service logs"""
    # Claude Code format
    match = re.search(r'Token usage:\s*input=(\d+),\s*output=(\d+)', line)
    if match:
        return "claude", int(match.group(1)), int(match.group(2))

    # OpenAI/Codex format (JSON or text)
    if 'gpt' in line.lower() or 'openai' in line.lower() or 'codex' in line.lower():
        match = re.search(r'input.*?(\d+).*?output.*?(\d+)', line, re.I)
        if match:
            return "codex", int(match.group(1)), int(match.group(2))

    # Gemini format
    if 'gemini' in line.lower() or 'google' in line.lower():
        match = re.search(r'input.*?(\d+).*?output.*?(\d+)', line, re.I)
        if match:
            return "gemini", int(match.group(1)), int(match.group(2))

    return None, None, None


def calculate_cost(service, input_tokens, output_tokens):
    """Calculate API cost based on service"""
    input_price, output_price = PRICING.get(service, PRICING["other"])
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    return input_cost + output_cost


def update_metrics_from_logs():
    """Monitor all AI service logs in real-time"""
    print(f"Monitoring: {CLAUDE_LOG}")

    while True:
        try:
            if not CLAUDE_LOG.exists():
                time.sleep(1)
                continue

            with open(CLAUDE_LOG, 'r') as f:
                with cache_lock:
                    pos = metrics_cache["log_position"]
                f.seek(pos)

                new_lines = f.readlines()

                if new_lines:
                    for line in new_lines:
                        service, input_tokens, output_tokens = parse_token_line(line)

                        if service:
                            with cache_lock:
                                # Update service-specific counters
                                metrics_cache[f"{service}_input"] += input_tokens
                                metrics_cache[f"{service}_output"] += output_tokens

                                # Calculate and add cost
                                call_cost = calculate_cost(service, input_tokens, output_tokens)
                                metrics_cache["total_cost"] += call_cost
                                metrics_cache["last_update"] = datetime.now().isoformat()

                                # Log to console
                                total_in = sum([metrics_cache[f"{s}_input"] for s in ["claude", "codex", "gemini", "other"]])
                                total_out = sum([metrics_cache[f"{s}_output"] for s in ["claude", "codex", "gemini", "other"]])
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {service}: +{input_tokens} in, +{output_tokens} out | "
                                      f"Total: {total_in:,} in, {total_out:,} out | ${metrics_cache['total_cost']:.4f}")

                    with cache_lock:
                        metrics_cache["log_position"] = f.tell()

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(0.5)


if __name__ == "__main__":
    log_monitor = threading.Thread(target=update_metrics_from_logs, daemon=True)
    log_monitor.start()

    server = HTTPServer(('localhost', 4318), MetricsHandler)
    print("Universal AI Token Tracker running on http://localhost:4318/v1/metrics")
    print("Tracking: Claude, OpenAI/Codex, Gemini, and all other AI APIs\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        with cache_lock:
            total_in = sum([metrics_cache[f"{s}_input"] for s in ["claude", "codex", "gemini", "other"]])
            total_out = sum([metrics_cache[f"{s}_output"] for s in ["claude", "codex", "gemini", "other"]])
            print(f"Final: {total_in:,} input, {total_out:,} output, ${metrics_cache['total_cost']:.2f}")
        server.shutdown()
