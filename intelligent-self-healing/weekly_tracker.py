#!/usr/bin/env python3
"""
Automated weekly token tracker
Reads from accumulated session data instead of manual updates
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any

def get_weekly_from_accumulator() -> Optional[Dict[str, Any]]:
    """Get weekly usage from accumulated session data"""
    accumulator_file = Path.home() / ".claude" / "weekly_accumulator.json"
    
    if not accumulator_file.exists():
        return None
    
    try:
        with open(accumulator_file, 'r') as f:
            data = json.load(f)
        
        total_tokens = data.get('total', 0)
        weekly_limit = 200000  # Adjust to your actual limit
        percentage = min(int((total_tokens / weekly_limit) * 100), 100)
        
        return {
            'current': total_tokens,
            'limit': weekly_limit,
            'percentage': percentage,
            'source': 'accumulated',
            'session_count': len(data.get('sessions', []))
        }
    except Exception as e:
        return None

if __name__ == "__main__":
    result = get_weekly_from_accumulator()
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No accumulated data found")
