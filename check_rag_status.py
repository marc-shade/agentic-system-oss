#!/usr/bin/env python3
"""
RAG System Status Checker
=========================

Quick health check for RAG Code Generator system.
Run this anytime to verify RAG is operational.
"""

import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))


def print_status(name: str, status: bool, details: str = ""):
    """Print status with color."""
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name}")
    if details:
        print(f"   {details}")


async def check_rag_status():
    """Check RAG system status."""
    print("=" * 60)
    print("RAG CODE GENERATOR - SYSTEM STATUS")
    print("=" * 60)
    print()

    all_good = True

    # Check 1: Dependencies
    print("1. Dependencies:")
    try:
        import qdrant_client
        print_status("qdrant-client", True, "Vector database client available")
    except ImportError:
        print_status("qdrant-client", False, "NOT INSTALLED - run: pip install qdrant-client")
        all_good = False

    try:
        import sentence_transformers
        print_status("sentence-transformers", True, "Embedding model support available")
    except ImportError:
        print_status("sentence-transformers", False, "NOT INSTALLED - run: pip install sentence-transformers")
        all_good = False

    print()

    # Check 2: Services
    print("2. Services:")

    # Qdrant
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:6333/collections", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    collections = [c['name'] for c in data['result']['collections']]
                    has_rag = 'code_modifications' in collections
                    if has_rag:
                        print_status("Qdrant", True, f"Running on port 6333, collection ready")
                    else:
                        print_status("Qdrant", True, f"Running but collection not initialized")
                else:
                    print_status("Qdrant", False, f"HTTP {resp.status}")
                    all_good = False
    except Exception as e:
        print_status("Qdrant", False, f"Not accessible: {e}")
        print("   Start with: cd scripts && ./start-qdrant.sh")
        all_good = False

    # Ollama
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]
                    has_model = 'gpt-oss:20b' in models
                    if has_model:
                        print_status("Ollama", True, f"{len(models)} models, gpt-oss:20b ready")
                    else:
                        print_status("Ollama", True, f"{len(models)} models but gpt-oss:20b not found")
                        print("   Consider: ollama pull gpt-oss:20b")
                else:
                    print_status("Ollama", False, f"HTTP {resp.status}")
                    all_good = False
    except Exception as e:
        print_status("Ollama", False, f"Not accessible: {e}")
        print("   Start with: ollama serve")
        all_good = False

    print()

    # Check 3: RAG System
    print("3. RAG System:")
    try:
        from rag_code_generator import RAGCodeGenerator
        print_status("Import", True, "RAGCodeGenerator module available")

        # Try to initialize
        rag = RAGCodeGenerator()
        print_status("Initialize", True, "RAG system initialized successfully")

        # Get statistics
        stats = await rag.get_statistics()
        total = stats.get('total_modifications', 0)
        avg_gain = stats.get('avg_performance_gain', 0)

        if total > 0:
            print_status("Data", True, f"{total} patterns stored, avg gain: {avg_gain:.1f}%")
        else:
            print_status("Data", True, "No patterns yet (system ready to learn)")
            print("   Patterns will accumulate as autonomous loop runs")

    except Exception as e:
        print_status("RAG System", False, f"Error: {e}")
        all_good = False

    print()

    # Check 4: Integration
    print("4. Integration:")
    try:
        from autonomous_recursive_agi_loop import AutonomousRecursiveAGILoop
        print_status("Autonomous Loop", True, "Imports successfully with RAG")
    except Exception as e:
        print_status("Autonomous Loop", False, f"Import failed: {e}")
        all_good = False

    print()
    print("=" * 60)

    if all_good:
        print("STATUS: ✅ ALL SYSTEMS OPERATIONAL")
        print()
        print("RAG is ready to use!")
        print("- Run autonomous loop: python3 autonomous_recursive_agi_loop.py")
        print("- View patterns: python3 check_rag_status.py")
        print("- Test system: python3 test_rag_integration.py")
    else:
        print("STATUS: ⚠️  SOME ISSUES DETECTED")
        print()
        print("Fix the issues above and run this script again.")

    print("=" * 60)

    return all_good


if __name__ == "__main__":
    result = asyncio.run(check_rag_status())
    sys.exit(0 if result else 1)
