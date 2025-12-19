#!/usr/bin/env python3
"""
Principle 0 validator hook - Validate no fake data (Principle 0).
"""
import sys
import json
import re

def validate_no_fake_data(tool_name, result):
    """Validate that results don't contain fake/placeholder data."""
    
    if not result:
        return True
    
    result_str = str(result).lower()
    
    # Fake data patterns that violate Principle 0
    fake_patterns = [
        r'\b(test\.rs|example\.py|placeholder)\b',
        r'\b(todo|fixme|xxx|hack)\b',
        r'\b(fake|mock|dummy|sample)_data\b',
        r'\{[^}]*\}(?:\s*#.*placeholder)',  # Empty objects with placeholder comments
        r'\[\](?:\s*#.*placeholder)',  # Empty arrays with placeholder comments
        r'\b(lorem ipsum|placeholder text)\b',
        r'\b(john doe|jane smith|test user)\b',
        r'\b(example\.com|test\.example)\b',
        r'\b(123-45-6789|555-555-5555)\b',  # Fake phone/SSN
        r'\b(password123|admin|secret)\b',
    ]
    
    # Quality concerns
    quality_patterns = [
        r'\b(not implemented|coming soon)\b',
        r'\b(will be added later|to be completed)\b',
        r'\b(stub|skeleton|boilerplate)\b.*\b(only|empty)\b',
    ]
    
    violations = []
    
    # Check for fake data patterns
    for pattern in fake_patterns:
        matches = re.findall(pattern, result_str)
        if matches:
            violations.append({
                'type': 'fake_data',
                'pattern': pattern,
                'matches': matches,
                'severity': 'critical'
            })
    
    # Check for quality issues
    for pattern in quality_patterns:
        matches = re.findall(pattern, result_str)
        if matches:
            violations.append({
                'type': 'quality_issue',
                'pattern': pattern,
                'matches': matches,
                'severity': 'warning'
            })
    
    if violations:
        print(f"🚨 PRINCIPLE 0 VIOLATIONS DETECTED:")
        
        critical_violations = [v for v in violations if v['severity'] == 'critical']
        warnings = [v for v in violations if v['severity'] == 'warning']
        
        if critical_violations:
            print(f"   CRITICAL: {len(critical_violations)} fake data violations")
            for violation in critical_violations:
                print(f"     - {violation['type']}: {violation['matches']}")
            
            # Log violation
            violation_log = {
                'tool_name': tool_name,
                'violations': violations,
                'result_sample': result_str[:200] + '...' if len(result_str) > 200 else result_str
            }
            
            with open('/home/marc/.claude/.principle_0_violations.log', 'a') as f:
                f.write(json.dumps(violation_log) + '\n')
            
            print("   ⚠️  This violates Principle 0: NO FAKE DATA")
            print("   📝 Violation logged for review")
        
        if warnings:
            print(f"   WARNINGS: {len(warnings)} quality concerns")
            for warning in warnings:
                print(f"     - {warning['type']}: {warning['matches']}")
    
    # Update statistics
    try:
        stats_file = '/home/marc/.claude/.principle_0_stats.json'
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
        except:
            stats = {'total_checks': 0, 'violations': 0, 'score': 100}
        
        stats['total_checks'] += 1
        if critical_violations:
            stats['violations'] += 1
        
        # Calculate score (violations reduce score)
        if stats['total_checks'] > 0:
            stats['score'] = max(0, 100 - (stats['violations'] / stats['total_checks'] * 100))
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
            
    except Exception as e:
        print(f"Error updating stats: {e}", file=sys.stderr)
    
    return len(critical_violations) == 0

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(0)
            
        tool_name = sys.argv[1]
        result = sys.argv[2]
        
        validate_no_fake_data(tool_name, result)
        sys.exit(0)  # This is informational only
        
    except Exception as e:
        print(f"Error in Principle 0 validator: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()