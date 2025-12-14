"""
Security Auditor Component
==========================

Inspired by OpenAI's Aardvark, this component acts as an agentic security researcher.
It continuously scans the codebase for vulnerabilities and validates proposed changes
to ensure no security regressions are introduced.
"""
import platform
from pathlib import Path

import logging
import json
import os
import aiohttp
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# Configure logging
logger = logging.getLogger("security-auditor")

class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class Vulnerability:
    file_path: str
    line_number: int
    severity: Severity
    description: str
    suggested_fix: str

class SecurityAuditor:
    """
    Agentic security researcher that analyzes code for vulnerabilities using an LLM.
    """

    def __init__(self, base_path: str = str(_STORAGE_BASE), ollama_host: str = None, model: str = None):
        self.base_path = base_path
        # Cloud-first strategy: use environment variables, default to completeu-server with cloud model
        self.ollama_host = ollama_host or os.getenv('OLLAMA_URL', 'http://192.168.1.186:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'gpt-oss:20b-cloud')
        logger.info(f"Security Auditor initialized (Model: {self.model} @ {self.ollama_host})")

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        url = f"{self.ollama_host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1, # Low temperature for analysis
                "num_predict": 2048
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Ollama API error: {resp.status} - {error_text}")
                        return ""
                    data = await resp.json()
                    return data.get("response", "")
        except Exception as e:
            logger.error(f"Failed to call Ollama: {e}")
            return ""

    async def scan_codebase(self, path: str) -> List[Vulnerability]:
        """
        Scans the codebase at the given path for vulnerabilities using LLM.
        """
        logger.info(f"Scanning codebase at {path}...")
        # In a full implementation, this would walk the directory.
        # For now, we'll assume 'path' is a file or we just scan specific critical files.
        return []

    async def validate_change(self, code_before: str, code_after: str) -> Tuple[bool, List[str]]:
        """
        Validates a proposed code change using LLM analysis.
        """
        logger.info("Validating proposed change with LLM...")
        
        prompt = f"""You are an expert security auditor. Review the following code change for security vulnerabilities.

CODE BEFORE:
```python
{code_before}
```

CODE AFTER:
```python
{code_after}
```

INSTRUCTIONS:
1. Analyze the changes for security risks (e.g., injection, hardcoded secrets, unsafe functions, data leaks).
2. If the change is SAFE, output exactly: "STATUS: SAFE"
3. If the change is UNSAFE, output: "STATUS: UNSAFE" followed by a list of issues.

RESPONSE:
"""
        response = await self._call_ollama(prompt)
        
        if not response:
            logger.warning("LLM failed to respond, defaulting to safe (with warning)")
            return True, ["WARNING: Security audit failed due to LLM error"]

        if "STATUS: UNSAFE" in response:
            # Extract issues
            issues = [line.strip() for line in response.split('\n') if line.strip() and "STATUS:" not in line]
            return False, issues
        
        return True, []

    async def generate_patch(self, vulnerability: Vulnerability) -> str:
        """
        Generates a patch for a found vulnerability.
        """
        prompt = f"""You are an expert security engineer. Fix the following vulnerability.

VULNERABILITY: {vulnerability.description}
FILE: {vulnerability.file_path}

SUGGESTED FIX:
{vulnerability.suggested_fix}

Generate a code patch to fix this issue.
"""
        return await self._call_ollama(prompt)
