#!/usr/bin/env python3
"""
Claude Code Telemetry Collector
Scrapes Claude Code's Prometheus endpoint and stores in database
"""

import sqlite3
import re
import time
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error

DB_PATH = Path.home() / ".claude" / "monitoring" / "claude_usage.db"
PROMETHEUS_URL = "http://localhost:9464/metrics"
SCRAPE_INTERVAL = 15  # seconds

def parse_prometheus_metrics(text):
    """Parse Prometheus format metrics"""
    metrics = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_create_tokens": 0,
        "total_cost": 0.0
    }
    
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Parse claude_code metrics
        if 'claude_code_token_usage' in line:
            if 'type="input"' in line:
                match = re.search(r'}\s+(\d+)', line)
                if match:
                    metrics["input_tokens"] = int(match.group(1))
            elif 'type="output"' in line:
                match = re.search(r'}\s+(\d+)', line)
                if match:
                    metrics["output_tokens"] = int(match.group(1))
            elif 'type="cache_read"' in line or 'type="cache_creation"' in line:
                match = re.search(r'}\s+(\d+)', line)
                if match:
                    val = int(match.group(1))
                    if 'cache_read' in line:
                        metrics["cache_read_tokens"] = val
                    else:
                        metrics["cache_create_tokens"] = val
        
        elif 'claude_code_cost' in line or 'cost_usage' in line:
            match = re.search(r'}\s+([\d.]+)', line)
            if match:
                metrics["total_cost"] = float(match.group(1))
    
    return metrics

def fetch_prometheus_metrics():
    """Fetch metrics from Claude Code's Prometheus endpoint"""
    try:
        with urllib.request.urlopen(PROMETHEUS_URL, timeout=5) as response:
            return response.read().decode('utf-8')
    except urllib.error.URLError:
        return None
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return None

def update_database(metrics):
    """Update session in database with current metrics"""
    total_tokens = (
        metrics["input_tokens"] + 
        metrics["output_tokens"] + 
        metrics["cache_read_tokens"] + 
        metrics["cache_create_tokens"]
    )
    
    if total_tokens == 0:
        return  # No data yet
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Check if there's an active session today
        cursor.execute("""
            SELECT id, tokens_used, estimated_cost 
            FROM sessions 
            WHERE date(start_time) = date('now')
            ORDER BY id DESC LIMIT 1
        """)
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing session
            session_id, old_tokens, old_cost = existing
            cursor.execute("""
                UPDATE sessions 
                SET tokens_used = ?, 
                    estimated_cost = ?,
                    end_time = datetime('now')
                WHERE id = ?
            """, (total_tokens, metrics["total_cost"], session_id))
        else:
            # Create new session for today
            cursor.execute("""
                INSERT INTO sessions (
                    start_time, end_time, tokens_used, estimated_cost
                ) VALUES (
                    datetime('now'), datetime('now'), ?, ?
                )
            """, (total_tokens, metrics["total_cost"]))
        
        conn.commit()
        print(f"Updated: {total_tokens} tokens, ${metrics['total_cost']:.4f} cost")

def main():
    """Main collection loop"""
    print(f"Claude Code Telemetry Collector starting...")
    print(f"Scraping: {PROMETHEUS_URL}")
    print(f"Database: {DB_PATH}")
    print(f"Interval: {SCRAPE_INTERVAL}s")
    
    while True:
        try:
            # Fetch metrics from Claude Code
            metrics_text = fetch_prometheus_metrics()
            
            if metrics_text:
                metrics = parse_prometheus_metrics(metrics_text)
                update_database(metrics)
            else:
                print("Waiting for Claude Code to start exporting metrics...")
            
            time.sleep(SCRAPE_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error in collection loop: {e}")
            time.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    main()
