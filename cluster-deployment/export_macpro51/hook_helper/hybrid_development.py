#!/usr/bin/env python3
"""
Hybrid Development Hook
Intelligently chooses between vibe coding, light specs, and full specs
Tracks token efficiency and time-to-MVP
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

class HybridDevelopmentHook:
    def __init__(self):
        self.claude_home = Path.home() / ".claude"
        self.learning_db = self.claude_home / "learning.db"
        self.memory_db = self.claude_home / "enhanced_memory.db"
        self.metrics_file = self.claude_home / "hybrid_metrics.json"
        
        # Decision thresholds
        self.VIBE_THRESHOLD = 0.9  # 90% of cases
        self.LIGHT_SPEC_THRESHOLD = 0.09  # 9% of cases
        self.FULL_SPEC_THRESHOLD = 0.01  # 1% of cases
        
        # Token budgets
        self.TOKEN_BUDGETS = {
            "vibe": 3000,
            "light_spec": 6000,
            "full_spec": 20000
        }
        
        # Initialize metrics tracking
        self.current_session = {
            "start_time": time.time(),
            "approach": None,
            "tokens_used": 0,
            "features_completed": 0
        }
    
    def analyze_request(self, request: str) -> Tuple[str, float]:
        """Analyze request to determine best approach"""
        request_lower = request.lower()
        
        # Keywords indicating complexity
        complexity_indicators = {
            "banking": 1.0,
            "medical": 1.0,
            "financial": 0.9,
            "security": 0.8,
            "critical": 0.8,
            "algorithm": 0.7,
            "distributed": 0.7,
            "team": 0.6,
            "api": 0.5,
            "contract": 0.5
        }
        
        # Keywords indicating simplicity
        simplicity_indicators = {
            "prototype": -0.9,
            "mvp": -0.9,
            "demo": -0.8,
            "quick": -0.8,
            "simple": -0.7,
            "ui": -0.6,
            "frontend": -0.5,
            "test": -0.5,
            "explore": -0.4,
            "try": -0.4
        }
        
        complexity_score = 0.0
        
        # Calculate complexity score
        for keyword, weight in complexity_indicators.items():
            if keyword in request_lower:
                complexity_score += weight
        
        for keyword, weight in simplicity_indicators.items():
            if keyword in request_lower:
                complexity_score += weight
        
        # Normalize score between 0 and 1
        complexity_score = max(0, min(1, (complexity_score + 1) / 2))
        
        # Determine approach based on score
        if complexity_score < 0.3:
            return "vibe", complexity_score
        elif complexity_score < 0.7:
            return "light_spec", complexity_score
        else:
            return "full_spec", complexity_score
    
    def track_token_usage(self, tokens: int, feature: str = None):
        """Track token usage for current session"""
        self.current_session["tokens_used"] += tokens
        
        if feature:
            self.current_session["features_completed"] += 1
            
            # Store in learning database
            conn = sqlite3.connect(self.learning_db)
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO interactions 
                (timestamp, input_hash, input_type, tools_used, success, duration, context_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                feature[:8],  # Use first 8 chars as hash
                self.current_session["approach"],
                "hybrid_development",
                True,
                time.time() - self.current_session["start_time"],
                tokens
            ))
            
            conn.commit()
            conn.close()
    
    def get_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate efficiency metrics for current session"""
        duration = time.time() - self.current_session["start_time"]
        
        metrics = {
            "approach": self.current_session["approach"],
            "duration_seconds": duration,
            "duration_minutes": duration / 60,
            "tokens_used": self.current_session["tokens_used"],
            "features_completed": self.current_session["features_completed"],
            "tokens_per_feature": (
                self.current_session["tokens_used"] / self.current_session["features_completed"]
                if self.current_session["features_completed"] > 0 else 0
            ),
            "time_per_feature": (
                duration / self.current_session["features_completed"]
                if self.current_session["features_completed"] > 0 else 0
            ),
            "efficiency_score": self.calculate_efficiency_score()
        }
        
        return metrics
    
    def calculate_efficiency_score(self) -> float:
        """Calculate efficiency score (0-100)"""
        if self.current_session["features_completed"] == 0:
            return 0
        
        tokens_per_feature = (
            self.current_session["tokens_used"] / 
            self.current_session["features_completed"]
        )
        
        # Compare to budget
        budget = self.TOKEN_BUDGETS.get(self.current_session["approach"], 3000)
        
        # Score is 100 if at or under budget, decreases as we go over
        if tokens_per_feature <= budget:
            return 100
        else:
            # Lose 10 points for every 1000 tokens over budget
            over_budget = tokens_per_feature - budget
            return max(0, 100 - (over_budget / 100))
    
    def suggest_tools_for_approach(self, approach: str, request: str) -> List[str]:
        """Suggest tools based on approach"""
        if approach == "vibe":
            # Minimal tools for rapid prototyping
            return ["Write", "Edit", "Bash"]
        elif approach == "light_spec":
            # Add some structure
            return ["Read", "Write", "Edit", "Bash", "Grep"]
        else:  # full_spec
            # Full toolset
            return ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "TodoWrite"]
    
    def generate_approach_guide(self, approach: str, request: str) -> str:
        """Generate guidance for the chosen approach"""
        if approach == "vibe":
            return f"""
## Vibe Coding Approach Selected

**Why**: Your request appears to be a prototype/MVP/exploration task.

**Strategy**:
1. Start with UI and dummy data
2. Get something visible in 3 minutes
3. Iterate based on what you see
4. Add backend only when needed

**Token Budget**: {self.TOKEN_BUDGETS['vibe']} tokens

**Focus**: Speed and iteration over planning
"""
        elif approach == "light_spec":
            return f"""
## Light Specification Approach Selected

**Why**: Your request has moderate complexity or team coordination needs.

**Strategy**:
1. Quick 3-expert conversation (UX, PM, Architect)
2. 20-line specification maximum
3. Focus on API contracts or core algorithms
4. Build incrementally

**Token Budget**: {self.TOKEN_BUDGETS['light_spec']} tokens

**Focus**: Essential structure without over-planning
"""
        else:  # full_spec
            return f"""
## Full Specification Approach Selected

**Why**: Your request involves critical systems or high complexity.

**Strategy**:
1. Comprehensive specification
2. Detailed planning and risk assessment
3. Test-driven development
4. Full documentation

**Token Budget**: {self.TOKEN_BUDGETS['full_spec']} tokens

**Focus**: Correctness and safety over speed
"""
    
    def learn_from_outcome(self, success: bool, actual_time: float, actual_tokens: int):
        """Learn from the outcome of the chosen approach"""
        conn = sqlite3.connect(self.learning_db)
        c = conn.cursor()
        
        # Store pattern
        pattern_data = {
            "approach": self.current_session["approach"],
            "success": success,
            "time_minutes": actual_time / 60,
            "tokens": actual_tokens,
            "efficiency": self.calculate_efficiency_score()
        }
        
        c.execute("""
            INSERT OR REPLACE INTO patterns 
            (pattern_type, pattern_data, frequency, success_rate, last_seen)
            VALUES (?, ?, 
                COALESCE((SELECT frequency + 1 FROM patterns 
                          WHERE pattern_type = ?), 1),
                ?, ?)
        """, (
            f"hybrid_{self.current_session['approach']}",
            json.dumps(pattern_data),
            f"hybrid_{self.current_session['approach']}",
            1.0 if success else 0.0,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_metrics(self):
        """Save session metrics to file"""
        metrics = self.get_efficiency_metrics()
        
        # Load existing metrics
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                all_metrics = json.load(f)
        else:
            all_metrics = []
        
        # Add current session
        metrics["timestamp"] = datetime.now().isoformat()
        all_metrics.append(metrics)
        
        # Save
        with open(self.metrics_file, 'w') as f:
            json.dump(all_metrics, f, indent=2)

def hook(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main hook entry point"""
    
    if event_type != "pre-tool-use":
        return {"continue": True}
    
    hook = HybridDevelopmentHook()
    
    # Check for development-related requests
    tool = event_data.get("tool", "")
    
    if tool == "Task":
        request = event_data.get("prompt", "")
        
        # Analyze and choose approach
        approach, complexity = hook.analyze_request(request)
        hook.current_session["approach"] = approach
        
        # Generate guidance
        guidance = hook.generate_approach_guide(approach, request)
        
        # Suggest tools
        suggested_tools = hook.suggest_tools_for_approach(approach, request)
        
        # Add to event data
        event_data["hybrid_approach"] = {
            "approach": approach,
            "complexity_score": complexity,
            "guidance": guidance,
            "suggested_tools": suggested_tools,
            "token_budget": hook.TOKEN_BUDGETS[approach]
        }
        
        print(f"\n[Hybrid Development] Approach: {approach} (complexity: {complexity:.2f})")
        print(f"[Hybrid Development] Token budget: {hook.TOKEN_BUDGETS[approach]}")
    
    return {"continue": True, "modified_data": event_data}

if __name__ == "__main__":
    # Test the hook
    hook = HybridDevelopmentHook()
    
    test_cases = [
        "Build a quick prototype for a todo app",
        "Create an API contract for user authentication",
        "Develop a banking system with regulatory compliance"
    ]
    
    for test in test_cases:
        approach, complexity = hook.analyze_request(test)
        print(f"\nRequest: {test}")
        print(f"Approach: {approach}")
        print(f"Complexity: {complexity:.2f}")
        print(f"Token Budget: {hook.TOKEN_BUDGETS[approach]}")
        print("-" * 50)