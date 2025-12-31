"""
Security Module

Following Kai's Multi-Layer Security Pattern:
1. Purpose Validator - Ensure requests align with agent purpose
2. Prompt Injection Detector - Detect malicious prompt patterns
3. Tool Access Controller - Limit tool availability by role
4. Permission Enforcer - Role-based access control
5. Human Review Gate - Flag sensitive operations for review

Each layer operates independently and must pass for action to proceed.
"""

from .prompt_injection_detector import PromptInjectionDetector
from .purpose_validator import PurposeValidator
from .tool_access_controller import ToolAccessController
from .permission_enforcer import PermissionEnforcer
from .human_review_gate import HumanReviewGate
from .security_pipeline import SecurityPipeline

__all__ = [
    'PromptInjectionDetector',
    'PurposeValidator',
    'ToolAccessController',
    'PermissionEnforcer',
    'HumanReviewGate',
    'SecurityPipeline',
]
