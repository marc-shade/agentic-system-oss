"""
Deterministic Data Validation

NO AI - Pure code for data validation.
Following Kai pattern: "If I can do it in code, I do it in code first."
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    level: ValidationLevel
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None


class DataValidator:
    """Deterministic data validation - no AI required."""

    # Common regex patterns
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(
        r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\-.?=&%#]*$'
    )
    SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    SEMVER_PATTERN = re.compile(
        r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
    )

    @staticmethod
    def is_email(value: str) -> bool:
        """Check if value is valid email."""
        return bool(DataValidator.EMAIL_PATTERN.match(value))

    @staticmethod
    def is_url(value: str) -> bool:
        """Check if value is valid URL."""
        return bool(DataValidator.URL_PATTERN.match(value))

    @staticmethod
    def is_slug(value: str) -> bool:
        """Check if value is valid slug (lowercase-hyphenated)."""
        return bool(DataValidator.SLUG_PATTERN.match(value))

    @staticmethod
    def is_uuid(value: str) -> bool:
        """Check if value is valid UUID."""
        return bool(DataValidator.UUID_PATTERN.match(value))

    @staticmethod
    def is_semver(value: str) -> bool:
        """Check if value is valid semantic version."""
        return bool(DataValidator.SEMVER_PATTERN.match(value))

    @staticmethod
    def is_not_empty(value: Any) -> bool:
        """Check if value is not empty/None."""
        if value is None:
            return False
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict, set)):
            return len(value) > 0
        return True

    @staticmethod
    def is_in_range(value: Union[int, float], min_val: Optional[float] = None,
                    max_val: Optional[float] = None) -> bool:
        """Check if numeric value is in range."""
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True

    @staticmethod
    def is_length_valid(value: Union[str, list], min_len: Optional[int] = None,
                        max_len: Optional[int] = None) -> bool:
        """Check if value length is valid."""
        length = len(value)
        if min_len is not None and length < min_len:
            return False
        if max_len is not None and length > max_len:
            return False
        return True

    @staticmethod
    def is_type(value: Any, expected_type: type) -> bool:
        """Check if value is of expected type."""
        return isinstance(value, expected_type)

    @staticmethod
    def matches_pattern(value: str, pattern: str) -> bool:
        """Check if value matches regex pattern."""
        return bool(re.match(pattern, value))

    @staticmethod
    def is_one_of(value: Any, allowed_values: List[Any]) -> bool:
        """Check if value is in allowed list."""
        return value in allowed_values

    @staticmethod
    def has_required_keys(data: Dict, required_keys: List[str]) -> List[str]:
        """Check which required keys are missing."""
        return [key for key in required_keys if key not in data]

    @staticmethod
    def validate_schema(data: Dict[str, Any], schema: Dict[str, Dict]) -> List[ValidationResult]:
        """
        Validate data against a schema.

        Schema format:
        {
            'field_name': {
                'type': str,  # expected type
                'required': True,  # is field required
                'min_length': 1,  # for strings
                'max_length': 100,
                'min_value': 0,  # for numbers
                'max_value': 100,
                'pattern': r'^...$',  # regex pattern
                'allowed_values': [...]  # enum-like
            }
        }
        """
        results = []

        for field, rules in schema.items():
            value = data.get(field)

            # Check required
            if rules.get('required', False) and value is None:
                results.append(ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Required field '{field}' is missing",
                    field=field
                ))
                continue

            if value is None:
                continue  # Skip optional missing fields

            # Check type
            expected_type = rules.get('type')
            if expected_type and not isinstance(value, expected_type):
                results.append(ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Field '{field}' should be {expected_type.__name__}, got {type(value).__name__}",
                    field=field,
                    value=value
                ))
                continue

            # Check length for strings/lists
            if isinstance(value, (str, list)):
                min_len = rules.get('min_length')
                max_len = rules.get('max_length')
                if not DataValidator.is_length_valid(value, min_len, max_len):
                    results.append(ValidationResult(
                        valid=False,
                        level=ValidationLevel.ERROR,
                        message=f"Field '{field}' length must be between {min_len} and {max_len}",
                        field=field,
                        value=len(value)
                    ))

            # Check range for numbers
            if isinstance(value, (int, float)):
                min_val = rules.get('min_value')
                max_val = rules.get('max_value')
                if not DataValidator.is_in_range(value, min_val, max_val):
                    results.append(ValidationResult(
                        valid=False,
                        level=ValidationLevel.ERROR,
                        message=f"Field '{field}' must be between {min_val} and {max_val}",
                        field=field,
                        value=value
                    ))

            # Check pattern
            pattern = rules.get('pattern')
            if pattern and isinstance(value, str):
                if not DataValidator.matches_pattern(value, pattern):
                    results.append(ValidationResult(
                        valid=False,
                        level=ValidationLevel.ERROR,
                        message=f"Field '{field}' doesn't match required pattern",
                        field=field,
                        value=value
                    ))

            # Check allowed values
            allowed = rules.get('allowed_values')
            if allowed and not DataValidator.is_one_of(value, allowed):
                results.append(ValidationResult(
                    valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Field '{field}' must be one of {allowed}",
                    field=field,
                    value=value
                ))

        return results

    @staticmethod
    def is_valid_python_identifier(name: str) -> bool:
        """Check if string is valid Python identifier."""
        return name.isidentifier()

    @staticmethod
    def sanitize_string(value: str, allowed_chars: Optional[str] = None) -> str:
        """Remove disallowed characters from string."""
        if allowed_chars is None:
            # Default: alphanumeric, underscore, hyphen, space
            allowed_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- '
        return ''.join(c for c in value if c in allowed_chars)


if __name__ == '__main__':
    # Self-test
    assert DataValidator.is_email('test@example.com')
    assert not DataValidator.is_email('invalid-email')

    assert DataValidator.is_url('https://example.com/path')
    assert not DataValidator.is_url('not-a-url')

    assert DataValidator.is_slug('valid-slug-123')
    assert not DataValidator.is_slug('Invalid Slug')

    assert DataValidator.is_uuid('550e8400-e29b-41d4-a716-446655440000')
    assert not DataValidator.is_uuid('not-a-uuid')

    assert DataValidator.is_semver('1.2.3')
    assert DataValidator.is_semver('1.0.0-alpha+001')
    assert not DataValidator.is_semver('1.2')

    # Test schema validation
    schema = {
        'name': {'type': str, 'required': True, 'min_length': 1},
        'age': {'type': int, 'required': True, 'min_value': 0, 'max_value': 150},
        'email': {'type': str, 'required': False}
    }

    valid_data = {'name': 'John', 'age': 30}
    invalid_data = {'name': '', 'age': 200}

    results = DataValidator.validate_schema(valid_data, schema)
    assert len(results) == 0

    results = DataValidator.validate_schema(invalid_data, schema)
    assert len(results) == 2

    print('All DataValidator tests passed!')
