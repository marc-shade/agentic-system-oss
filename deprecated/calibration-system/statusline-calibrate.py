#!/usr/bin/env python3
"""
Statusline Weekly Usage Calibration Tool

Allows user to manually calibrate weekly token usage tracking by providing
the current week's percentage from Claude Code's /usage command.

Prometheus only provides cumulative totals, so we need a baseline to calculate
weekly usage correctly.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
import requests
import pytz

BASELINE_FILE = Path.home() / ".claude" / "weekly_usage_baseline.json"
PROMETHEUS_URL = "http://127.0.0.1:9090"


def get_prometheus_cumulative():
    """Get current cumulative token total from Prometheus"""
    queries = {
        'input': 'sum(claude_code_token_usage_total{type="input"})',
        'output': 'sum(claude_code_token_usage_total{type="output"})',
        'cache_creation': 'sum(claude_code_token_usage_total{type="cacheCreation"})',
        'cache_read': 'sum(claude_code_token_usage_total{type="cacheRead"})'
    }

    tokens = {}
    for name, query in queries.items():
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={'query': query},
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success' and data['data']['result']:
                    tokens[name] = int(float(data['data']['result'][0]['value'][1]))
                else:
                    tokens[name] = 0
            else:
                tokens[name] = 0
        except Exception:
            tokens[name] = 0

    # Calculate API cost: full price for input/output/cache_creation, 10% for cache_read
    api_cost = (tokens['input'] +
               tokens['output'] +
               tokens['cache_creation'] +
               (tokens['cache_read'] * 0.1))

    return int(api_cost)


def parse_reset_time(reset_str):
    """Parse reset time string like 'Nov 19, 4pm (America/New_York)'"""
    # Example: "Nov 19, 4pm (America/New_York)"
    # Simple parsing - user will provide in interactive mode
    return reset_str


def calculate_next_reset(current_reset, schedule="weekly"):
    """Calculate next reset time from current reset"""
    # Add 7 days for weekly reset
    next_reset = current_reset + timedelta(days=7)
    return next_reset.isoformat()


def interactive_calibrate():
    """Interactive calibration wizard"""
    print("=" * 60)
    print("Claude Code Weekly Usage Calibration")
    print("=" * 60)
    print()
    print("This tool calibrates weekly token usage tracking for the statusline.")
    print("Prometheus only tracks cumulative totals, so we need your help!")
    print()
    print("Step 1: Check your current usage")
    print("  In Claude Code, run: /usage")
    print()

    # Get current week percentage
    while True:
        week_pct_str = input("Current week percentage (e.g., 60): ")
        try:
            week_pct = int(week_pct_str.strip().replace('%', ''))
            if 0 <= week_pct <= 200:
                break
            print("Please enter a number between 0 and 200")
        except ValueError:
            print("Please enter a valid number")

    print()

    # Get reset time
    print("Step 2: When does your week reset?")
    print("  Example from /usage: 'Resets Nov 19, 4pm (America/New_York)'")
    print()

    reset_date_str = input("Reset date (e.g., Nov 19, 4pm): ")
    timezone_str = input("Timezone (e.g., America/New_York): ").strip()

    # Parse date
    try:
        # Try to parse "Nov 19, 4pm" format
        from dateutil import parser
        reset_dt = parser.parse(f"{reset_date_str} {datetime.now().year}")

        # Add timezone
        if timezone_str:
            tz = pytz.timezone(timezone_str)
            reset_dt = tz.localize(reset_dt)

        # If reset time is in the past, assume next year
        if reset_dt < datetime.now(reset_dt.tzinfo if reset_dt.tzinfo else None):
            reset_dt = reset_dt.replace(year=reset_dt.year + 1)

    except Exception as e:
        print(f"Could not parse date: {e}")
        print("Using default: 7 days from now")
        reset_dt = datetime.now() + timedelta(days=7)

    print()
    print("Step 3: Estimating weekly limit...")

    # Get Prometheus current total
    prometheus_total = get_prometheus_cumulative()

    # Estimate weekly limit based on percentage
    # If user is at 60% and has used X tokens this week,
    # then limit = X / 0.60
    # But we don't know how much was used THIS week vs before
    # So we'll use a reasonable default and let user override

    default_limit = 1000000  # 1M tokens
    limit_str = input(f"Weekly limit in tokens (default {default_limit}): ")

    if limit_str.strip():
        try:
            weekly_limit = int(limit_str.strip())
        except ValueError:
            weekly_limit = default_limit
    else:
        weekly_limit = default_limit

    # Calculate current usage in tokens
    current_week_tokens = int((week_pct / 100) * weekly_limit)

    # Calculate prometheus checkpoint (total - current week)
    prometheus_checkpoint = prometheus_total - current_week_tokens

    print()
    print("=" * 60)
    print("Calibration Summary")
    print("=" * 60)
    print(f"Current week usage:     {week_pct}% ({current_week_tokens:,} tokens)")
    print(f"Weekly limit:           {weekly_limit:,} tokens")
    print(f"Next reset:             {reset_dt.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print(f"Prometheus checkpoint:  {prometheus_checkpoint:,} tokens")
    print(f"Prometheus current:     {prometheus_total:,} tokens")
    print()

    confirm = input("Save this calibration? (y/n): ")
    if confirm.lower() != 'y':
        print("Calibration cancelled.")
        return

    # Save baseline
    baseline = {
        "calibration_date": datetime.now().isoformat(),
        "prometheus_checkpoint": prometheus_checkpoint,
        "current_week_percentage": week_pct,
        "weekly_limit_tokens": weekly_limit,
        "next_reset": reset_dt.isoformat(),
        "timezone": timezone_str or "UTC",
        "prometheus_total_at_calibration": prometheus_total
    }

    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w') as f:
        json.dump(baseline, f, indent=2)

    print()
    print("✅ Calibration saved!")
    print()
    print("The statusline will now show accurate weekly usage.")
    print("Re-run this command if you notice drift or after the weekly reset.")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        print("Usage: statusline-calibrate")
        print()
        print("Interactively calibrates weekly token usage tracking.")
        sys.exit(1)

    interactive_calibrate()


if __name__ == "__main__":
    main()
