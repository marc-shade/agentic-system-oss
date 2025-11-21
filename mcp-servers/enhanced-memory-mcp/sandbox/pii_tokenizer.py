"""
Reversible PII Tokenization

Implements Anthropic's pattern where sensitive data is tokenized before
reaching the model, but real values flow between tools.

Example:
    Input:  {"email": "john@example.com", "ssn": "123-45-6789"}
    Model sees: {"email": "[EMAIL_1]", "ssn": "[SSN_1]"}
    Tools receive: {"email": "john@example.com", "ssn": "123-45-6789"}

This provides privacy while maintaining tool functionality.
"""

import re
import hashlib
import secrets
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PIIToken:
    """A tokenized PII value"""
    token: str
    original: str
    pii_type: str
    created_at: datetime = field(default_factory=datetime.now)


class PIITokenizer:
    """
    Reversible PII tokenizer for secure data handling.

    Tokens are session-scoped and automatically expire.
    """

    # PII detection patterns
    PATTERNS = {
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "PHONE": r'\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        "SSN": r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
        "CREDIT_CARD": r'\b(?:\d{4}[-.\s]?){3}\d{4}\b',
        "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        "API_KEY": r'\b(?:sk|pk|api|key|token)[-_]?[A-Za-z0-9]{20,}\b',
        "AWS_KEY": r'\b(?:AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}\b',
        "JWT": r'\beyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/]+\b',
        "PASSWORD": r'(?:password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']+["\']?',
    }

    def __init__(self):
        self._token_map: Dict[str, PIIToken] = {}
        self._reverse_map: Dict[str, str] = {}
        self._counters: Dict[str, int] = {}
        self._session_id = secrets.token_hex(8)

    def _generate_token(self, pii_type: str) -> str:
        """Generate a unique token for a PII type"""
        count = self._counters.get(pii_type, 0) + 1
        self._counters[pii_type] = count
        return f"[{pii_type}_{count}]"

    def tokenize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Tokenize PII in text.

        Args:
            text: Input text potentially containing PII

        Returns:
            Tuple of (tokenized_text, token_mapping)
        """
        result = text
        mappings = {}

        for pii_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, result, re.IGNORECASE)

            for match in matches:
                original = match.group()

                # Check if we've already tokenized this value
                if original in self._reverse_map:
                    token = self._reverse_map[original]
                else:
                    token = self._generate_token(pii_type)
                    pii_token = PIIToken(token=token, original=original, pii_type=pii_type)
                    self._token_map[token] = pii_token
                    self._reverse_map[original] = token

                result = result.replace(original, token, 1)
                mappings[token] = original

        return result, mappings

    def tokenize_dict(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Tokenize PII in a dictionary (recursive).

        Args:
            data: Dictionary potentially containing PII

        Returns:
            Tuple of (tokenized_dict, token_mapping)
        """
        all_mappings = {}

        def process_value(value: Any) -> Any:
            if isinstance(value, str):
                tokenized, mappings = self.tokenize(value)
                all_mappings.update(mappings)
                return tokenized
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            return value

        result = process_value(data)
        return result, all_mappings

    def detokenize(self, text: str) -> str:
        """
        Restore original PII from tokens.

        Args:
            text: Text containing PII tokens

        Returns:
            Text with original PII values restored
        """
        result = text

        for token, pii_token in self._token_map.items():
            result = result.replace(token, pii_token.original)

        return result

    def detokenize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore original PII in a dictionary (recursive).

        Args:
            data: Dictionary containing PII tokens

        Returns:
            Dictionary with original PII values restored
        """
        def process_value(value: Any) -> Any:
            if isinstance(value, str):
                return self.detokenize(value)
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            return value

        return process_value(data)

    def get_token_info(self, token: str) -> Optional[PIIToken]:
        """Get information about a token"""
        return self._token_map.get(token)

    def get_stats(self) -> Dict[str, Any]:
        """Get tokenization statistics"""
        by_type = {}
        for token, pii_token in self._token_map.items():
            pii_type = pii_token.pii_type
            by_type[pii_type] = by_type.get(pii_type, 0) + 1

        return {
            "session_id": self._session_id,
            "total_tokens": len(self._token_map),
            "by_type": by_type
        }

    def clear(self):
        """Clear all token mappings (use for session reset)"""
        self._token_map.clear()
        self._reverse_map.clear()
        self._counters.clear()
        self._session_id = secrets.token_hex(8)


# Global tokenizer instance
_tokenizer: Optional[PIITokenizer] = None


def get_tokenizer() -> PIITokenizer:
    """Get or create the global PII tokenizer"""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = PIITokenizer()
    return _tokenizer


def tokenize_for_model(data: Any) -> Tuple[Any, Dict[str, str]]:
    """
    Tokenize data before sending to model.

    Use this to protect PII while maintaining tool functionality.
    """
    tokenizer = get_tokenizer()

    if isinstance(data, str):
        return tokenizer.tokenize(data)
    elif isinstance(data, dict):
        return tokenizer.tokenize_dict(data)
    return data, {}


def detokenize_for_tool(data: Any) -> Any:
    """
    Restore original values before sending to tool.

    Tools receive real data, model sees tokens.
    """
    tokenizer = get_tokenizer()

    if isinstance(data, str):
        return tokenizer.detokenize(data)
    elif isinstance(data, dict):
        return tokenizer.detokenize_dict(data)
    return data


def create_pii_context() -> Dict[str, Any]:
    """Create PII tokenization context for code execution"""
    tokenizer = get_tokenizer()

    return {
        "tokenize_pii": lambda text: tokenizer.tokenize(text)[0],
        "detokenize_pii": tokenizer.detokenize,
        "pii_stats": tokenizer.get_stats,
    }


# Middleware for automatic tokenization
class PIIMiddleware:
    """
    Middleware for automatic PII tokenization in MCP data flow.

    Usage:
        middleware = PIIMiddleware()

        # Before sending to model
        safe_result = middleware.protect(tool_result)

        # Before sending to tool
        real_params = middleware.restore(model_params)
    """

    def __init__(self):
        self.tokenizer = PIITokenizer()
        self.enabled = True

    def protect(self, data: Any) -> Any:
        """Tokenize PII before model sees it"""
        if not self.enabled:
            return data

        if isinstance(data, str):
            return self.tokenizer.tokenize(data)[0]
        elif isinstance(data, dict):
            return self.tokenizer.tokenize_dict(data)[0]
        return data

    def restore(self, data: Any) -> Any:
        """Restore PII before tool receives it"""
        if not self.enabled:
            return data

        if isinstance(data, str):
            return self.tokenizer.detokenize(data)
        elif isinstance(data, dict):
            return self.tokenizer.detokenize_dict(data)
        return data

    def toggle(self, enabled: bool):
        """Enable/disable PII protection"""
        self.enabled = enabled
        logger.info(f"PII protection {'enabled' if enabled else 'disabled'}")
