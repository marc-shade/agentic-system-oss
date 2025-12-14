#!/usr/bin/env python3
"""
Privacy Detection Hook
Auto-detects sensitive data and triggers Local Privacy Agent
"""
import sys
import json
import re

def contains_sensitive_data(prompt):
    """Check if prompt contains sensitive data patterns"""
    
    # Sensitive patterns that require local processing
    SENSITIVE_PATTERNS = [
        # Personal Identifiers
        r'\b(SSN|social\s+security|DOB|date\s+of\s+birth)\b',
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN format
        
        # Medical
        r'\b(medical\s+record|patient\s+data|HIPAA|PHI|diagnosis|prescription)\b',
        r'\b(health\s+record|medical\s+history|treatment\s+plan)\b',
        
        # Financial
        r'\b(credit\s+card|bank\s+account|routing\s+number|financial\s+record)\b',
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card format
        
        # Credentials
        r'\b(API[\s_]key|password|secret|credential|token|private[\s_]key)\b',
        
        # Business Sensitive
        r'\b(confidential|proprietary|classified|trade\s+secret)\b',
        r'\b(employee\s+record|HR\s+data|salary|compensation)\b',
        
        # Privacy Keywords
        r'\b(PII|GDPR|personal\s+information|sensitive\s+data)\b',
        r'\b(must\s+stay\s+local|cannot\s+leave|air[\s-]gapped|private|internal\s+only)\b'
    ]
    
    prompt_lower = prompt.lower()
    
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            return True, pattern
    
    return False, None

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"allow": True}))
        return
    
    user_prompt = sys.argv[1]
    
    is_sensitive, pattern = contains_sensitive_data(user_prompt)
    
    if is_sensitive:
        response = {
            "allow": False,
            "message": f"🔒 PRIVACY ALERT: Sensitive data detected (pattern: {pattern})\n\n" +
                      "MANDATORY ACTION: Spawning Local Privacy Agent for 100% local processing.\n" +
                      "• Model: gpt-oss:20b (via Ollama)\n" +
                      "• Processing: 100% local, no external API calls\n" +
                      "• Data sovereignty: Complete\n\n" +
                      "The Local Privacy Agent will handle this request securely.",
            "spawn_agent": "🔒 Local Privacy Agent",
            "reason": "sensitive_data_detected"
        }
    else:
        response = {"allow": True}
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()