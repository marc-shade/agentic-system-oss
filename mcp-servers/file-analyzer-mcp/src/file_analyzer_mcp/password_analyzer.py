#!/usr/bin/env python3
"""
Password Policy Analyzer

Analyzes passwords and password policies for security compliance.
Part of the file-analyzer-mcp security toolkit.
"""

import hashlib
import json
import math
import re
import string
from collections import Counter
from pathlib import Path
from typing import Optional

# Common password patterns to check against
COMMON_PASSWORDS = {
    'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey', 'master',
    'dragon', 'letmein', 'login', 'admin', 'welcome', 'shadow', 'sunshine',
    'princess', '123456789', '654321', 'superman', 'qazwsx', 'michael',
    'football', 'password1', 'password123', 'iloveyou', 'starwars', 'trustno1'
}

# Keyboard patterns
KEYBOARD_PATTERNS = [
    'qwerty', 'asdfgh', 'zxcvbn', 'qwertyuiop', 'asdfghjkl', 'zxcvbnm',
    '1234567890', '!@#$%^&*()', 'qazwsx', 'edcrfv', 'tgbyhn', 'ujmik',
    'wsxedc', 'rfvtgb', 'yhnujm', 'aqwsed', 'zsxdcf', 'plokij'
]

# Character sets
LOWERCASE = set(string.ascii_lowercase)
UPPERCASE = set(string.ascii_uppercase)
DIGITS = set(string.digits)
SPECIAL = set(string.punctuation)


def calculate_entropy(password: str) -> float:
    """Calculate password entropy in bits."""
    charset_size = 0
    chars = set(password)

    if chars & LOWERCASE:
        charset_size += 26
    if chars & UPPERCASE:
        charset_size += 26
    if chars & DIGITS:
        charset_size += 10
    if chars & SPECIAL:
        charset_size += 32

    if charset_size == 0:
        return 0

    return len(password) * math.log2(charset_size)


def check_common_patterns(password: str) -> list:
    """Check for common weak patterns."""
    issues = []
    lower = password.lower()

    # Check against common passwords
    if lower in COMMON_PASSWORDS:
        issues.append({"type": "common_password", "severity": "critical", "message": "Password is in common password list"})

    # Check keyboard patterns
    for pattern in KEYBOARD_PATTERNS:
        if pattern in lower or pattern[::-1] in lower:
            issues.append({"type": "keyboard_pattern", "severity": "high", "message": f"Contains keyboard pattern: {pattern}"})
            break

    # Check for repeated characters
    if re.search(r'(.)\1{2,}', password):
        issues.append({"type": "repeated_chars", "severity": "medium", "message": "Contains repeated characters"})

    # Check for sequential numbers
    for seq in ['0123', '1234', '2345', '3456', '4567', '5678', '6789', '9876', '8765', '7654']:
        if seq in password:
            issues.append({"type": "sequential_numbers", "severity": "medium", "message": "Contains sequential numbers"})
            break

    # Check for sequential letters
    for seq in ['abcd', 'bcde', 'cdef', 'defg', 'efgh', 'fghi', 'ghij']:
        if seq in lower:
            issues.append({"type": "sequential_letters", "severity": "medium", "message": "Contains sequential letters"})
            break

    # Check for dates (common pattern)
    if re.search(r'(19|20)\d{2}', password):
        issues.append({"type": "contains_year", "severity": "low", "message": "Contains year pattern (19xx/20xx)"})

    # Check for l33tspeak substitutions of common passwords
    leet_map = {'@': 'a', '4': 'a', '3': 'e', '1': 'l', '0': 'o', '$': 's', '5': 's', '7': 't'}
    deleet = lower
    for leet, char in leet_map.items():
        deleet = deleet.replace(leet, char)
    if deleet in COMMON_PASSWORDS:
        issues.append({"type": "leet_common", "severity": "high", "message": "Password is leetspeak version of common password"})

    return issues


def estimate_crack_time(entropy: float) -> dict:
    """Estimate time to crack based on entropy."""
    # Assume 10 billion guesses per second (high-end GPU cluster)
    guesses_per_second = 10_000_000_000
    total_guesses = 2 ** entropy

    seconds = total_guesses / guesses_per_second

    if seconds < 1:
        return {"time": "instant", "severity": "critical"}
    elif seconds < 60:
        return {"time": f"{seconds:.1f} seconds", "severity": "critical"}
    elif seconds < 3600:
        return {"time": f"{seconds/60:.1f} minutes", "severity": "critical"}
    elif seconds < 86400:
        return {"time": f"{seconds/3600:.1f} hours", "severity": "high"}
    elif seconds < 86400 * 30:
        return {"time": f"{seconds/86400:.1f} days", "severity": "medium"}
    elif seconds < 86400 * 365:
        return {"time": f"{seconds/(86400*30):.1f} months", "severity": "low"}
    elif seconds < 86400 * 365 * 100:
        return {"time": f"{seconds/(86400*365):.1f} years", "severity": "good"}
    else:
        return {"time": "centuries+", "severity": "excellent"}


async def analyze_password(password: str, check_hibp: bool = False) -> str:
    """
    Analyze a password's strength and security.

    Args:
        password: Password to analyze (NOT logged or stored)
        check_hibp: Check against Have I Been Pwned (requires API call)

    Returns:
        JSON with detailed strength analysis
    """
    length = len(password)
    chars = set(password)

    # Character analysis
    has_lower = bool(chars & LOWERCASE)
    has_upper = bool(chars & UPPERCASE)
    has_digit = bool(chars & DIGITS)
    has_special = bool(chars & SPECIAL)

    char_types = sum([has_lower, has_upper, has_digit, has_special])

    # Entropy calculation
    entropy = calculate_entropy(password)

    # Pattern checking
    issues = check_common_patterns(password)

    # Crack time estimation
    crack_time = estimate_crack_time(entropy)

    # Calculate overall score (0-100)
    score = 0
    score += min(length * 4, 40)  # Up to 40 points for length
    score += char_types * 10  # Up to 40 points for character diversity
    score += min(entropy / 2, 20)  # Up to 20 points for entropy

    # Deduct for issues
    for issue in issues:
        if issue['severity'] == 'critical':
            score -= 40
        elif issue['severity'] == 'high':
            score -= 20
        elif issue['severity'] == 'medium':
            score -= 10
        else:
            score -= 5

    score = max(0, min(100, score))

    # Strength rating
    if score >= 80:
        strength = "Strong"
    elif score >= 60:
        strength = "Moderate"
    elif score >= 40:
        strength = "Weak"
    else:
        strength = "Very Weak"

    # Generate recommendations
    recommendations = []
    if length < 12:
        recommendations.append("Increase length to at least 12 characters")
    if not has_lower:
        recommendations.append("Add lowercase letters")
    if not has_upper:
        recommendations.append("Add uppercase letters")
    if not has_digit:
        recommendations.append("Add numbers")
    if not has_special:
        recommendations.append("Add special characters (!@#$%^&*)")
    if issues:
        recommendations.append("Avoid common patterns and dictionary words")

    result = {
        "success": True,
        "length": length,
        "character_analysis": {
            "has_lowercase": has_lower,
            "has_uppercase": has_upper,
            "has_digits": has_digit,
            "has_special": has_special,
            "character_types": char_types
        },
        "entropy_bits": round(entropy, 2),
        "crack_time_estimate": crack_time,
        "issues": issues,
        "score": round(score),
        "strength": strength,
        "recommendations": recommendations,
        "note": "Password was analyzed locally and NOT transmitted or stored"
    }

    # HIBP check (hash only)
    if check_hibp:
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1[:5]
        result["hibp_check"] = {
            "hash_prefix": prefix,
            "check_url": f"https://api.pwnedpasswords.com/range/{prefix}",
            "note": "Use k-anonymity API - only hash prefix is sent"
        }

    return json.dumps(result, indent=2)


async def analyze_password_policy(
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False,
    max_length: int = 128,
    disallow_username: bool = True,
    password_history: int = 5,
    max_age_days: int = 90
) -> str:
    """
    Analyze a password policy against security best practices.

    Args:
        min_length: Minimum password length
        require_uppercase: Require uppercase letters
        require_lowercase: Require lowercase letters
        require_digit: Require numbers
        require_special: Require special characters
        max_length: Maximum password length
        disallow_username: Disallow username in password
        password_history: Number of previous passwords to remember
        max_age_days: Maximum password age in days

    Returns:
        JSON with policy analysis and recommendations
    """
    issues = []
    recommendations = []
    score = 100

    # Check minimum length
    if min_length < 8:
        issues.append({"type": "min_length_too_short", "severity": "critical", "message": "Minimum length should be at least 8"})
        score -= 30
    elif min_length < 12:
        issues.append({"type": "min_length_short", "severity": "medium", "message": "Consider minimum length of 12+"})
        score -= 10
    elif min_length >= 14:
        recommendations.append("Good: Strong minimum length requirement")

    # Check maximum length
    if max_length < 64:
        issues.append({"type": "max_length_too_short", "severity": "high", "message": "Max length should allow passphrases (64+)"})
        score -= 15

    # Character requirements
    char_requirements = sum([require_uppercase, require_lowercase, require_digit, require_special])
    if char_requirements < 3:
        issues.append({"type": "weak_complexity", "severity": "medium", "message": "Require at least 3 character types"})
        score -= 10

    if not require_special and min_length < 14:
        issues.append({"type": "no_special_short", "severity": "medium", "message": "Short passwords should require special characters"})
        score -= 10

    # Password history
    if password_history < 5:
        issues.append({"type": "short_history", "severity": "low", "message": "Password history should remember at least 5 passwords"})
        score -= 5
    elif password_history >= 12:
        recommendations.append("Good: Strong password history requirement")

    # Password age
    if max_age_days > 0 and max_age_days < 30:
        issues.append({"type": "too_frequent_rotation", "severity": "medium", "message": "Very frequent rotation may lead to weak passwords"})
        score -= 10
    elif max_age_days == 0 or max_age_days > 365:
        issues.append({"type": "no_rotation", "severity": "low", "message": "Consider password rotation between 90-365 days"})
        score -= 5

    # NIST 800-63B compliance check
    nist_compliant = True
    nist_notes = []

    if min_length < 8:
        nist_compliant = False
        nist_notes.append("NIST requires minimum 8 characters")
    if max_length < 64:
        nist_compliant = False
        nist_notes.append("NIST requires supporting at least 64 characters")

    # Modern recommendation: complexity rules are discouraged
    if require_special and require_digit and min_length < 12:
        nist_notes.append("NIST discourages complexity rules in favor of length")

    if max_age_days > 0 and max_age_days < 365:
        nist_notes.append("NIST recommends against mandatory periodic rotation")

    # Calculate grade
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    return json.dumps({
        "success": True,
        "policy_analyzed": {
            "min_length": min_length,
            "max_length": max_length,
            "require_uppercase": require_uppercase,
            "require_lowercase": require_lowercase,
            "require_digit": require_digit,
            "require_special": require_special,
            "disallow_username": disallow_username,
            "password_history": password_history,
            "max_age_days": max_age_days
        },
        "score": max(0, score),
        "grade": grade,
        "issues": issues,
        "recommendations": recommendations if recommendations else ["Consider passphrase-based policies with longer minimum lengths"],
        "nist_800_63b": {
            "compliant": nist_compliant,
            "notes": nist_notes
        },
        "best_practices": [
            "Use minimum 12-14 character length",
            "Allow maximum 64+ characters for passphrases",
            "Block common/breached passwords",
            "Avoid mandatory periodic rotation",
            "Support password managers (allow paste)",
            "Implement MFA as additional layer"
        ]
    }, indent=2)


async def generate_password_requirements(
    security_level: str = "standard"
) -> str:
    """
    Generate recommended password requirements based on security level.

    Args:
        security_level: "basic", "standard", "high", or "critical"

    Returns:
        JSON with recommended password policy
    """
    policies = {
        "basic": {
            "min_length": 8,
            "max_length": 128,
            "require_mixed_case": True,
            "require_digit": True,
            "require_special": False,
            "password_history": 3,
            "max_age_days": 365,
            "lockout_threshold": 10,
            "use_case": "Low-sensitivity internal systems"
        },
        "standard": {
            "min_length": 12,
            "max_length": 128,
            "require_mixed_case": True,
            "require_digit": True,
            "require_special": True,
            "password_history": 6,
            "max_age_days": 180,
            "lockout_threshold": 5,
            "use_case": "General business applications"
        },
        "high": {
            "min_length": 14,
            "max_length": 128,
            "require_mixed_case": True,
            "require_digit": True,
            "require_special": True,
            "password_history": 12,
            "max_age_days": 90,
            "lockout_threshold": 3,
            "mfa_required": True,
            "use_case": "Financial, healthcare, privileged accounts"
        },
        "critical": {
            "min_length": 16,
            "max_length": 128,
            "require_mixed_case": True,
            "require_digit": True,
            "require_special": True,
            "password_history": 24,
            "max_age_days": 60,
            "lockout_threshold": 3,
            "mfa_required": True,
            "hardware_token": True,
            "use_case": "Critical infrastructure, admin accounts, secrets"
        }
    }

    if security_level not in policies:
        return json.dumps({
            "success": False,
            "error": f"Unknown security level: {security_level}",
            "valid_levels": list(policies.keys())
        })

    policy = policies[security_level]

    return json.dumps({
        "success": True,
        "security_level": security_level,
        "recommended_policy": policy,
        "implementation_notes": [
            "Block passwords found in breach databases",
            "Implement rate limiting on login attempts",
            "Use secure password hashing (bcrypt, Argon2)",
            "Support password managers",
            "Provide clear error messages without revealing info"
        ]
    }, indent=2)


# Functions are imported and registered by main server.py
