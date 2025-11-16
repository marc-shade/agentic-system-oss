#!/usr/bin/env python3
"""
Test Ollama Cloud integration for enhanced-memory-mcp
"""

import os
import json
from ollama import Client

def test_ollama_extraction():
    """Test LLM-powered extraction using Ollama Cloud"""

    # Check API key
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("❌ OLLAMA_API_KEY not set")
        return False

    print("✅ OLLAMA_API_KEY is set")

    try:
        # Create Ollama client
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': f'Bearer {api_key}'}
        )
        print("✅ Ollama Client created")

        # Test extraction
        conversation_text = """Marc: I prefer using Ollama Cloud for LLM features instead of Anthropic.
Assistant: I've updated the enhanced-memory system to use Ollama Cloud API.
Marc: Great! Use the gpt-oss:120b model for better accuracy.
Assistant: The system now uses gpt-oss:120b for extraction and multi-query search."""

        system_prompt = """You are a memory extraction specialist. Extract key facts, preferences, and entities from conversations.

Focus on:
- User preferences and requirements
- Technical facts and specifications
- Relationships and connections
- Important decisions or conclusions
- Patterns of behavior

Return ONLY valid JSON (no markdown, no explanation):
{
    "entities": [
        {
            "name": "descriptive-name-with-dashes",
            "entityType": "preference|fact|requirement|decision|person|system|pattern",
            "observations": ["specific fact 1", "specific fact 2", ...],
            "confidence": 0.0-1.0,
            "relationships": ["related-entity-1", "related-entity-2"]
        }
    ]
}"""

        user_content = f"{system_prompt}\n\nExtract facts from this conversation:\n\n{conversation_text}"
        messages = [{"role": "user", "content": user_content}]

        print("\n🔄 Calling Ollama Cloud API...")
        response = client.chat(
            model="gpt-oss:120b",
            messages=messages,
            stream=False,
            options={
                "temperature": 0.3,
                "num_predict": 2000
            }
        )

        response_text = response['message']['content']
        print("✅ Received response from Ollama Cloud")

        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        facts = json.loads(response_text.strip())

        print(f"\n✅ Successfully extracted {len(facts.get('entities', []))} entities:")
        for entity in facts.get('entities', []):
            print(f"  - {entity.get('name')} ({entity.get('entityType')})")
            print(f"    Observations: {len(entity.get('observations', []))}")
            print(f"    Confidence: {entity.get('confidence', 0)}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ollama_perspectives():
    """Test multi-query perspective generation using Ollama Cloud"""

    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        print("❌ OLLAMA_API_KEY not set")
        return False

    try:
        client = Client(
            host="https://ollama.com",
            headers={'Authorization': f'Bearer {api_key}'}
        )

        query = "voice communication system"
        perspective_count = 3

        perspective_prompt = f"""Generate {perspective_count - 1} alternative phrasings of this search query. Each should capture the same intent but use different wording.

Original query: {query}

Return only a JSON array of strings:
["alternative 1", "alternative 2", ...]"""

        messages = [{"role": "user", "content": perspective_prompt}]

        print("\n🔄 Generating query perspectives...")
        response = client.chat(
            model="gpt-oss:120b",
            messages=messages,
            stream=False,
            options={
                "temperature": 0.7,
                "num_predict": 500
            }
        )

        response_text = response['message']['content'].strip()
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        alternatives = json.loads(response_text)

        print(f"✅ Generated {len(alternatives)} query perspectives:")
        print(f"  Original: {query}")
        for alt in alternatives:
            print(f"  Alternative: {alt}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Ollama Cloud Integration")
    print("=" * 60)

    print("\n--- Test 1: LLM Extraction ---")
    extraction_ok = test_ollama_extraction()

    print("\n--- Test 2: Query Perspectives ---")
    perspectives_ok = test_ollama_perspectives()

    print("\n" + "=" * 60)
    if extraction_ok and perspectives_ok:
        print("✅ ALL TESTS PASSED - Ollama Cloud integration working!")
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
    print("=" * 60)
