#!/usr/bin/env python3
"""
LCD Message Filter
Intelligently formats messages for 16x2 LCD display using LLM + regex
"""

import json
import os
import re
from typing import Optional

import requests


# Environment-driven configuration so we can point at any local LLM runtime.
LLM_ENABLED = os.environ.get("LCD_FILTER_USE_LLM", "1").lower() not in {"0", "false", "off"}
LLM_ENDPOINT = os.environ.get(
    "LCD_FILTER_LLM_ENDPOINT",
    "http://127.0.0.1:11434/v1/chat/completions",  # OpenAI-compatible default (LM Studio, llamafile)
)
LLM_MODEL = os.environ.get("LCD_FILTER_LLM_MODEL", "llama-3.1-8b-instruct")
LLM_API_KEY = os.environ.get("LCD_FILTER_LLM_API_KEY")
LLM_TIMEOUT = float(os.environ.get("LCD_FILTER_LLM_TIMEOUT", "8.0"))


class LCDFilter:
    """Intelligent LCD message filter"""

    def __init__(self, width=16, height=2):
        self.width = width
        self.height = height

    def filter_message(self, message: str, use_llm: bool = True) -> tuple[str, str]:
        """
        Filter a message for LCD display

        Args:
            message: Raw message text
            use_llm: Whether to use LLM for intelligent filtering

        Returns:
            Tuple of (line1, line2) formatted for LCD
        """
        # First pass: Clean special characters with regex
        cleaned = self._regex_clean(message)

        # Second pass: Intelligent formatting with LLM
        if LLM_ENABLED and use_llm and len(cleaned) > self.width:
            try:
                return self._llm_format(cleaned)
            except Exception as e:
                print(f"LLM formatting failed: {e}, using fallback")
                return self._fallback_format(cleaned)
        else:
            return self._fallback_format(cleaned)

    def _regex_clean(self, text: str) -> str:
        """Clean special characters and emojis that LCD can't display"""

        # Remove most emojis but keep simple ones we know work
        safe_emojis = {
            '🔥': '🔥',  # Fire - Ember's symbol (works on this LCD)
            '✓': '✓',   # Checkmark
            '⚠': '⚠',   # Warning
            '❌': 'X',  # X mark
            '💻': 'CPU', # Computer
            '📚': 'Lrn', # Books
            '💕': '<3',  # Heart
            '🍖': 'Fd',  # Food
            '🎮': 'Ply', # Game
            '🧼': 'Cln', # Clean
        }

        # Replace known emojis with safe versions
        for emoji, replacement in safe_emojis.items():
            text = text.replace(emoji, replacement)

        # Remove remaining emojis (Unicode ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)

        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

        # Replace fancy quotes/dashes with ASCII
        replacements = {
            '"': '"', '"': '"', ''': "'", ''': "'",
            '—': '-', '–': '-', '…': '...',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _llm_format(self, text: str) -> tuple[str, str]:
        """Use local LLM (OpenAI-compatible or Ollama) to format message for 2-line LCD"""

        prompt = f"""Format this message for a 16x2 character LCD display (16 chars per line, 2 lines).

Message: "{text}"

Requirements:
1. Split into exactly 2 lines
2. Each line MUST be 16 characters or less
3. Use abbreviations when needed (H=Hunger, E=Energy, etc.)
4. Keep most important info on line 1
5. Use colons for labels (H:99 E:99)
6. No special characters except: / : - | < > 🔥 ✓ ⚠
7. Make it readable and informative

Return ONLY the two lines, separated by a newline. No explanation.

Example good output:
🔥Quality:100/100
Excellent V:0

Example bad output:
This is a really long line that exceeds sixteen characters
And this one too

Your formatted output:"""

        result = self._call_local_llm(prompt)
        if not result:
            raise ValueError("LLM returned empty response")

        lines = result.split('\n')

        if len(lines) >= 2:
            line1 = lines[0][:self.width]
            line2 = lines[1][:self.width]
            return (line1, line2)

        raise ValueError("LLM didn't return 2 lines")

    def _call_local_llm(self, prompt: str) -> Optional[str]:
        """
        Call the configured local LLM endpoint.

        Supports:
        - OpenAI-compatible /v1/chat/completions (LM Studio, llamafile, vLLM, etc.)
        - Ollama chat endpoint (/api/chat)
        """

        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"

        payload = self._build_payload(prompt)
        if payload is None:
            raise ValueError("Unsupported LLM endpoint configuration")

        response = requests.post(
            LLM_ENDPOINT,
            headers=headers,
            data=json.dumps(payload),
            timeout=LLM_TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        content = self._extract_content(data)
        return content.strip() if content else None

    def _build_payload(self, prompt: str) -> Optional[dict]:
        """Build request payload based on endpoint style."""

        if LLM_ENDPOINT.endswith("/api/chat"):
            # Ollama style
            return {
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }

        # Treat everything else as OpenAI-compatible
        return {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 100,
        }

    def _extract_content(self, data: dict) -> Optional[str]:
        """Extract assistant text from response payload."""

        if "choices" in data:
            # OpenAI-compatible
            choices = data.get("choices", [])
            if not choices:
                return None

            message = choices[0].get("message")
            if not message:
                return None

            return message.get("content")

        if "message" in data:
            # Ollama response
            message = data.get("message", {})
            return message.get("content")

        return None

    def _fallback_format(self, text: str) -> tuple[str, str]:
        """Fallback formatting without LLM"""

        # If text fits on one line, put it there
        if len(text) <= self.width:
            return (text, "")

        # Try to split at space near middle
        if len(text) <= self.width * 2:
            words = text.split()
            line1_words = []
            line2_words = []
            line1_len = 0

            for word in words:
                if line1_len + len(word) + 1 <= self.width:
                    line1_words.append(word)
                    line1_len += len(word) + 1
                else:
                    line2_words.append(word)

            line1 = ' '.join(line1_words)[:self.width]
            line2 = ' '.join(line2_words)[:self.width]

            return (line1, line2)

        # Text too long, truncate intelligently
        line1 = text[:self.width]
        line2 = text[self.width:self.width*2]

        return (line1, line2)

    def format_stats(self, stats: dict) -> tuple[str, str]:
        """Format stats dictionary for LCD"""

        # Build compact stats string
        parts = []
        if 'hunger' in stats:
            parts.append(f"H:{stats['hunger']}")
        if 'energy' in stats:
            parts.append(f"E:{stats['energy']}")
        if 'happiness' in stats:
            parts.append(f"Hap:{stats['happiness']}")
        if 'cleanliness' in stats:
            parts.append(f"C:{stats['cleanliness']}")

        stats_str = ' '.join(parts)
        mood = stats.get('mood', 'Unknown')

        # Line 1: Ember + key stats
        if len(stats_str) <= 10:
            line1 = f"🔥Ember {stats_str}"[:self.width]
        else:
            # Split stats across lines
            line1 = f"🔥{parts[0]} {parts[1]}"[:self.width] if len(parts) >= 2 else f"🔥Ember"[:self.width]

        # Line 2: Mood or remaining stats
        if 'last_feed' in stats:
            # Show time since last feed
            import time
            minutes = int((time.time() - stats['last_feed']) / 60)
            if minutes < 60:
                line2 = f"{mood} | Fed {minutes}m"[:self.width]
            else:
                hours = minutes // 60
                line2 = f"{mood} | Fed {hours}h"[:self.width]
        else:
            line2 = mood[:self.width]

        return (line1, line2)

    def format_quality_score(self, score: int, violations: int) -> tuple[str, str]:
        """Format quality score for LCD"""

        # Determine status (no emoji to avoid overflow)
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 50:
            status = "Fair"
        else:
            status = "Poor"

        # Format: "Quality:100/100 " (16 chars max)
        line1 = f"Quality:{score}/100"
        line1 = line1[:self.width].ljust(self.width)

        # Format: "Excellent V:0   " (16 chars max)
        line2 = f"{status} V:{violations}"
        line2 = line2[:self.width].ljust(self.width)

        return (line1, line2)

    def format_violations(self, count: int, recent: str = None, severity: str = None) -> tuple[str, str]:
        """Format violation info for LCD"""

        if count == 0:
            # Exactly 16 chars per line
            line1 = "No Violations!  "  # 16 chars
            line2 = "Quality Good    "   # 16 chars
        else:
            # Abbreviate violation type
            v_abbrev = {
                'fake_ui': 'FakeUI',
                'incomplete_work': 'Incompl',
                'mock_data': 'MockDat',
                'hardcoded': 'HardCod',
            }
            v_type = v_abbrev.get(recent, recent[:6] if recent else "???")

            # Format: "!3x FakeUI     " (16 chars)
            line1 = f"!{count}x {v_type}"
            line1 = line1[:self.width].ljust(self.width)

            # Abbreviate severity
            sev_abbrev = {
                'critical': 'CRIT',
                'severe': 'SEV',
                'moderate': 'MOD',
                'minor': 'MIN',
            }
            sev = sev_abbrev.get(severity, severity[:4] if severity else "?")

            # Format: "Severity:CRIT   " (16 chars)
            line2 = f"Severity:{sev}"
            line2 = line2[:self.width].ljust(self.width)

        return (line1, line2)

    def format_system_info(self, cpu: int, mem_used: float, mem_total: float) -> tuple[str, str]:
        """Format system info for LCD"""

        # Format: "CPU:22%         " (16 chars)
        line1 = f"CPU:{cpu}%"
        line1 = line1[:self.width].ljust(self.width)

        # Format: "RAM:13.8/32.0GB " (16 chars)
        line2 = f"RAM:{mem_used}/{mem_total}GB"
        line2 = line2[:self.width].ljust(self.width)

        return (line1, line2)

    def format_learning(self, patterns: int, confidence: int, ratio: int) -> tuple[str, str]:
        """Format learning stats for LCD"""

        # Format: "Learn:5 patterns" (16 chars)
        line1 = f"Learn:{patterns} pat"
        line1 = line1[:self.width].ljust(self.width)

        # Format: "Conf:85% Rat:90%" (16 chars)
        line2 = f"Conf:{confidence}% R:{ratio}%"
        line2 = line2[:self.width].ljust(self.width)

        return (line1, line2)


# CLI for testing
if __name__ == "__main__":
    import sys

    filter = LCDFilter()

    print("=" * 50)
    print("🔥 LCD Filter Test 🔥")
    print("=" * 50)
    print()

    # Test cases
    test_messages = [
        "This is a really long message that needs to be intelligently formatted for the LCD display",
        "🎮 Playing with Ember! Energy decreased but happiness increased!",
        "⚠️ CRITICAL: Multiple production violations detected in code",
        "Stats: H:99 E:95 Happy:88 Clean:92 Mood:Content",
    ]

    for i, msg in enumerate(test_messages, 1):
        print(f"Test {i}: {msg[:50]}...")
        line1, line2 = filter.filter_message(msg, use_llm=True)
        print(f"  Line 1 ({len(line1):2}): |{line1}|")
        print(f"  Line 2 ({len(line2):2}): |{line2}|")
        print()

    # Test specialized formatters
    print("Specialized Formatters:")
    print()

    print("Quality Score:")
    line1, line2 = filter.format_quality_score(100, 0)
    print(f"  Line 1: |{line1}|")
    print(f"  Line 2: |{line2}|")
    print()

    print("Violations:")
    line1, line2 = filter.format_violations(3, "fake_ui", "critical")
    print(f"  Line 1: |{line1}|")
    print(f"  Line 2: |{line2}|")
    print()

    print("System Info:")
    line1, line2 = filter.format_system_info(45, 14.2, 32.0)
    print(f"  Line 1: |{line1}|")
    print(f"  Line 2: |{line2}|")
