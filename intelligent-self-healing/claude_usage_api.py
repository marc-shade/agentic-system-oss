#!/usr/bin/env python3
"""
Query Claude Code's actual usage by parsing /usage command output
Uses the CURRENT Claude session via environment variables
"""
import os
import sys
import json
import subprocess
import time

def get_usage_from_current_session():
    """
    The /usage command data comes from Claude's API
    We can't easily intercept it, but we can use OpenTelemetry cost metrics
    to estimate usage percentage more accurately
    """
    
    try:
        # Get cost metrics from OpenTelemetry
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:9464/metrics'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode != 0:
            return None
        
        metrics = result.stdout
        
        # Parse total cost
        total_cost = 0.0
        for line in metrics.split('\n'):
            if 'claude_code_cost_usage_total' in line and not line.startswith('#'):
                # Extract the cost value (last field)
                parts = line.split()
                if parts:
                    try:
                        total_cost += float(parts[-1])
                    except:
                        pass
        
        # Estimate weekly budget based on typical plan
        # Pro plan: ~$10/week, Max: ~$50/week  
        # Use cost to estimate percentage
        weekly_cost_budget = 10.0  # Adjust based on plan
        
        if total_cost > 0:
            weekly_pct_used = int((total_cost / weekly_cost_budget) * 100)
            weekly_pct_remaining = max(0, 100 - weekly_pct_used)
            
            return {
                'weekly_remaining': weekly_pct_remaining,
                'weekly_used': weekly_pct_used,
                'total_cost': round(total_cost, 2),
                'source': 'cost_estimate'
            }
    
    except Exception as e:
        return None
    
    return None

if __name__ == "__main__":
    usage = get_usage_from_current_session()
    if usage:
        print(json.dumps(usage, indent=2))
    else:
        print(json.dumps({"error": "Could not get usage data"}))
