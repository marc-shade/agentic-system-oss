"""Pattern matching: regex pattern finder"""

def regex_matcher(text: str, pattern: str) -> List[str]:
    """
    Find all matches for a regex pattern.

    Args:
        text: Text to search
        pattern: Regex pattern

    Returns:
        List of matches
    """
    return re.findall(pattern, text)
