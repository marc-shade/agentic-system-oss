"""
Deterministic Text Processing

NO AI - Pure code for text manipulation.
Following Kai pattern: "If I can do it in code, I do it in code first."
"""

import re
import unicodedata
from typing import List, Dict, Optional, Tuple
from collections import Counter


class TextProcessor:
    """Deterministic text processing - no AI required."""

    # Common stop words
    STOP_WORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
        'she', 'we', 'they', 'what', 'which', 'who', 'whom', 'how', 'when',
        'where', 'why', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 'just', 'also'
    }

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize all whitespace to single spaces."""
        return ' '.join(text.split())

    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Remove extra whitespace while preserving newlines."""
        lines = text.split('\n')
        cleaned = [' '.join(line.split()) for line in lines]
        return '\n'.join(cleaned)

    @staticmethod
    def to_lowercase(text: str) -> str:
        """Convert to lowercase."""
        return text.lower()

    @staticmethod
    def to_uppercase(text: str) -> str:
        """Convert to uppercase."""
        return text.upper()

    @staticmethod
    def to_title_case(text: str) -> str:
        """Convert to title case."""
        return text.title()

    @staticmethod
    def to_sentence_case(text: str) -> str:
        """Convert to sentence case."""
        if not text:
            return text
        return text[0].upper() + text[1:].lower()

    @staticmethod
    def to_slug(text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        # Convert to lowercase
        text = text.lower()
        # Replace spaces and underscores with hyphens
        text = re.sub(r'[\s_]+', '-', text)
        # Remove non-alphanumeric except hyphens
        text = re.sub(r'[^a-z0-9-]', '', text)
        # Remove multiple consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens
        return text.strip('-')

    @staticmethod
    def to_snake_case(text: str) -> str:
        """Convert to snake_case."""
        # Handle camelCase
        text = re.sub(r'([a-z])([A-Z])', r'\1_\2', text)
        # Replace spaces and hyphens
        text = re.sub(r'[\s-]+', '_', text)
        # Remove non-alphanumeric except underscores
        text = re.sub(r'[^a-zA-Z0-9_]', '', text)
        return text.lower()

    @staticmethod
    def to_camel_case(text: str) -> str:
        """Convert to camelCase."""
        # First convert to words
        words = re.split(r'[\s_-]+', text)
        # Join with first word lowercase, rest title case
        if not words:
            return ''
        return words[0].lower() + ''.join(word.title() for word in words[1:])

    @staticmethod
    def to_pascal_case(text: str) -> str:
        """Convert to PascalCase."""
        words = re.split(r'[\s_-]+', text)
        return ''.join(word.title() for word in words)

    @staticmethod
    def remove_punctuation(text: str, keep: str = '') -> str:
        """Remove punctuation, optionally keeping some characters."""
        import string
        punctuation = ''.join(c for c in string.punctuation if c not in keep)
        return text.translate(str.maketrans('', '', punctuation))

    @staticmethod
    def remove_html_tags(text: str) -> str:
        """Remove HTML/XML tags from text."""
        return re.sub(r'<[^>]+>', '', text)

    @staticmethod
    def remove_urls(text: str) -> str:
        """Remove URLs from text."""
        return re.sub(r'https?://\S+|www\.\S+', '', text)

    @staticmethod
    def remove_emails(text: str) -> str:
        """Remove email addresses from text."""
        return re.sub(r'\S+@\S+\.\S+', '', text)

    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Extract all URLs from text."""
        return re.findall(r'https?://\S+|www\.\S+', text)

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract all email addresses from text."""
        return re.findall(r'\S+@\S+\.\S+', text)

    @staticmethod
    def extract_numbers(text: str) -> List[str]:
        """Extract all numbers from text."""
        return re.findall(r'-?\d+\.?\d*', text)

    @staticmethod
    def word_count(text: str) -> int:
        """Count words in text."""
        return len(text.split())

    @staticmethod
    def char_count(text: str, include_spaces: bool = True) -> int:
        """Count characters in text."""
        if include_spaces:
            return len(text)
        return len(text.replace(' ', ''))

    @staticmethod
    def line_count(text: str) -> int:
        """Count lines in text."""
        return len(text.split('\n'))

    @staticmethod
    def sentence_count(text: str) -> int:
        """Estimate sentence count."""
        return len(re.split(r'[.!?]+', text.strip())) - 1

    @staticmethod
    def tokenize(text: str, lowercase: bool = True) -> List[str]:
        """Simple word tokenization."""
        if lowercase:
            text = text.lower()
        return re.findall(r'\b\w+\b', text)

    @staticmethod
    def remove_stop_words(words: List[str]) -> List[str]:
        """Remove common stop words."""
        return [w for w in words if w.lower() not in TextProcessor.STOP_WORDS]

    @staticmethod
    def word_frequency(text: str, top_n: Optional[int] = None,
                       remove_stops: bool = True) -> Dict[str, int]:
        """Get word frequency distribution."""
        words = TextProcessor.tokenize(text, lowercase=True)
        if remove_stops:
            words = TextProcessor.remove_stop_words(words)
        freq = Counter(words)
        if top_n:
            return dict(freq.most_common(top_n))
        return dict(freq)

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = '...') -> str:
        """Truncate text to max length with suffix."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix

    @staticmethod
    def wrap_text(text: str, width: int = 80) -> str:
        """Wrap text to specified width."""
        import textwrap
        return textwrap.fill(text, width=width)

    @staticmethod
    def dedent(text: str) -> str:
        """Remove common leading whitespace."""
        import textwrap
        return textwrap.dedent(text)

    @staticmethod
    def indent(text: str, prefix: str = '    ') -> str:
        """Add prefix to each line."""
        import textwrap
        return textwrap.indent(text, prefix)

    @staticmethod
    def split_paragraphs(text: str) -> List[str]:
        """Split text into paragraphs."""
        return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    @staticmethod
    def find_all(text: str, pattern: str) -> List[Tuple[int, int, str]]:
        """Find all occurrences of pattern with positions."""
        return [(m.start(), m.end(), m.group()) for m in re.finditer(pattern, text)]

    @staticmethod
    def replace_many(text: str, replacements: Dict[str, str]) -> str:
        """Apply multiple replacements."""
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return TextProcessor.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings (0-1)."""
        distance = TextProcessor.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1 - (distance / max_len)


if __name__ == '__main__':
    # Self-test
    assert TextProcessor.to_slug('Hello World!') == 'hello-world'
    assert TextProcessor.to_snake_case('helloWorld') == 'hello_world'
    assert TextProcessor.to_camel_case('hello_world') == 'helloWorld'
    assert TextProcessor.to_pascal_case('hello world') == 'HelloWorld'

    assert TextProcessor.word_count('Hello world test') == 3
    assert TextProcessor.line_count('Line1\nLine2\nLine3') == 3

    assert TextProcessor.remove_html_tags('<p>Hello</p>') == 'Hello'

    freq = TextProcessor.word_frequency('the quick brown fox jumps over the lazy dog', remove_stops=False)
    assert freq['the'] == 2

    assert TextProcessor.truncate('Hello world this is a test', 15) == 'Hello world...'

    assert TextProcessor.levenshtein_distance('hello', 'hallo') == 1
    assert TextProcessor.similarity_ratio('hello', 'hello') == 1.0

    print('All TextProcessor tests passed!')
