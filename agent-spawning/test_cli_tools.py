#!/usr/bin/env python3
"""Test CLI tools independently"""

import subprocess
import sys

def test_claude_cli():
    """Test Claude Code CLI"""
    print("\n=== Testing Claude CLI ===")
    try:
        cmd = ["claude", "--print", "Say hello in JSON format"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_codex_cli():
    """Test Codex CLI"""
    print("\n=== Testing Codex CLI ===")
    try:
        # Try with quoted prompt
        cmd = ["codex", "exec", "Say hello in JSON format"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_gemini_cli():
    """Test Gemini CLI"""
    print("\n=== Testing Gemini CLI ===")
    try:
        cmd = ["gemini", "Say hello in JSON format"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_ollama_cli():
    """Test Ollama CLI"""
    print("\n=== Testing Ollama CLI ===")
    try:
        cmd = ["ollama", "run", "llama2", "Say hello"]
        result = subprocess.run(cmd, input="Say hello\n", capture_output=True, text=True, timeout=15)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing all CLI tools...")

    claude_ok = test_claude_cli()
    codex_ok = test_codex_cli()
    gemini_ok = test_gemini_cli()
    ollama_ok = test_ollama_cli()

    print("\n=== Test Results ===")
    print(f"Claude CLI: {'✅' if claude_ok else '❌'}")
    print(f"Codex CLI: {'✅' if codex_ok else '❌'}")
    print(f"Gemini CLI: {'✅' if gemini_ok else '❌'}")
    print(f"Ollama CLI: {'✅' if ollama_ok else '❌'}")
