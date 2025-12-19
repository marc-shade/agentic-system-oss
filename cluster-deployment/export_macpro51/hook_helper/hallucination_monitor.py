#!/usr/bin/env python3
"""
Hallucination Monitor Hook
Integrates real-time hallucination detection into agent responses
Priority: 2 (after tool validation, before execution)
"""

import json
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add MCP base to path
sys.path.insert(0, str(Path.home() / "Documents/Cline/MCP"))

class HallucinationMonitor:
    """Monitor and mitigate hallucinations in agent responses"""

    def __init__(self):
        self.critical_agents = [
            "Backend Engineer",
            "Frontend Specialist",
            "System Architect",
            "QA Engineer",
            "Security Specialist",
            "DevOps Engineer",
            "Database Specialist"
        ]
        self.threshold = 0.7  # Abstain if hallucination score > 0.7
        self.stats = {
            "total_checks": 0,
            "hallucinations_detected": 0,
            "abstentions": 0,
            "entities_verified": 0
        }

    async def check_response(self, text: str, context: str = "") -> Dict[str, Any]:
        """Check response for hallucinations using detector MCP"""
        try:
            # Import detector client
            from hallucination_detector_mcp.client import HallucinationDetectorClient

            client = HallucinationDetectorClient()
            result = await client.validate_invocation(
                claimed_action="agent_response",
                claimed_result=text[:500],  # First 500 chars for efficiency
                actual_evidence=context,
                context_free_facts=self.extract_facts(text)
            )

            self.stats["total_checks"] += 1

            if result["judgment"] in ["hallucinated", "suspicious"]:
                self.stats["hallucinations_detected"] += 1

            return {
                "hallucination_detected": result["judgment"] in ["hallucinated", "suspicious"],
                "confidence": result.get("confidence", 0.5),
                "should_abstain": result["judgment"] == "hallucinated",
                "judgment": result["judgment"],
                "explanation": result.get("explanation", "")
            }

        except Exception as e:
            # Fallback to simple heuristics if detector unavailable
            return self.simple_heuristic_check(text)

    def simple_heuristic_check(self, text: str) -> Dict[str, Any]:
        """Simple heuristic fallback when detector unavailable"""
        risky_patterns = [
            "I can confirm",
            "definitely",
            "100% certain",
            "always works",
            "never fails",
            "guaranteed to"
        ]

        risk_score = sum(1 for pattern in risky_patterns if pattern.lower() in text.lower())
        risk_level = risk_score / len(risky_patterns)

        return {
            "hallucination_detected": risk_level > 0.3,
            "confidence": 1.0 - risk_level,
            "should_abstain": risk_level > 0.5,
            "judgment": "suspicious" if risk_level > 0.3 else "authentic",
            "explanation": f"Heuristic check: {risk_score} risky patterns found"
        }

    def extract_facts(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        facts = []

        # Extract sentences with numbers or specific claims
        sentences = text.split('.')
        for sentence in sentences[:10]:  # First 10 sentences
            if any(char.isdigit() for char in sentence):
                facts.append(sentence.strip())
            elif any(word in sentence.lower() for word in ["created", "deleted", "modified", "fixed"]):
                facts.append(sentence.strip())

        return facts[:5]  # Limit to 5 facts

    async def pre_response_hook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Hook called before agent response is sent"""

        # Check if this is an agent response
        if event.get("type") != "agent_response":
            return event

        agent_type = event.get("agent_type", "")
        response_text = event.get("response", "")
        context = event.get("context", "")

        # Only check critical agents
        if agent_type not in self.critical_agents:
            return event

        # Check for hallucinations
        check_result = await self.check_response(response_text, context)

        # Add metadata to event
        event["hallucination_check"] = check_result

        # If should abstain, modify response
        if check_result["should_abstain"]:
            self.stats["abstentions"] += 1
            event["response"] = self.generate_safe_response(
                agent_type,
                check_result["explanation"]
            )
            event["abstained"] = True

        # Log high-risk responses
        if check_result["hallucination_detected"]:
            self.log_risky_response(agent_type, response_text, check_result)

        return event

    def generate_safe_response(self, agent_type: str, reason: str) -> str:
        """Generate safe alternative response when abstaining"""
        safe_responses = {
            "Backend Engineer": "I need to verify the technical details before providing this implementation. Let me search for confirmed patterns.",
            "Frontend Specialist": "I should confirm the UI/UX best practices for this specific case. Let me research verified examples.",
            "System Architect": "This architectural decision requires verification. Let me check established patterns and documentation.",
            "QA Engineer": "I need to verify the testing approach before proceeding. Let me check testing best practices.",
            "Security Specialist": "Security claims require careful verification. Let me consult security documentation.",
            "default": f"I detected potential inaccuracies in my response ({reason}). Let me provide verified information instead."
        }

        return safe_responses.get(agent_type, safe_responses["default"])

    def log_risky_response(self, agent_type: str, response: str, check_result: Dict):
        """Log risky responses for analysis"""
        log_entry = {
            "agent_type": agent_type,
            "response_preview": response[:200],
            "judgment": check_result["judgment"],
            "confidence": check_result["confidence"],
            "timestamp": Path(__file__).stat().st_mtime
        }

        log_file = Path.home() / ".claude" / "logs" / "hallucination_detections.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_stats(self) -> Dict[str, Any]:
        """Get current monitoring statistics"""
        if self.stats["total_checks"] > 0:
            detection_rate = self.stats["hallucinations_detected"] / self.stats["total_checks"]
            abstention_rate = self.stats["abstentions"] / self.stats["total_checks"]
        else:
            detection_rate = 0
            abstention_rate = 0

        return {
            **self.stats,
            "detection_rate": round(detection_rate, 3),
            "abstention_rate": round(abstention_rate, 3),
            "health_status": "healthy" if detection_rate < 0.1 else "concerning"
        }


# Global monitor instance
monitor = HallucinationMonitor()


async def main(event: Dict[str, Any]) -> Dict[str, Any]:
    """Main hook entry point"""
    return await monitor.pre_response_hook(event)


def get_hook_metadata() -> Dict[str, Any]:
    """Return hook metadata for registration"""
    return {
        "name": "hallucination_monitor",
        "priority": 2,
        "description": "Monitor and mitigate hallucinations in agent responses",
        "events": ["agent_response", "tool_result"],
        "critical_agents": monitor.critical_agents,
        "stats": monitor.get_stats()
    }


if __name__ == "__main__":
    # Test mode
    import asyncio

    test_event = {
        "type": "agent_response",
        "agent_type": "Backend Engineer",
        "response": "I've created 500 files and optimized the system by 1000%. This always works perfectly.",
        "context": "Optimize the backend performance"
    }

    result = asyncio.run(main(test_event))
    print(json.dumps(result, indent=2))
    print("\nStats:", json.dumps(monitor.get_stats(), indent=2))