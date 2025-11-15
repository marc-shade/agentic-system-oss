#!/usr/bin/env python3
"""
Simple Ollama Embedding Test
Directly tests Ollama API with mxbai-embed-large model
"""

import requests
import json
import time


def test_ollama_embedding():
    """Test Ollama embedding API directly"""
    print("=" * 70)
    print("OLLAMA EMBEDDING TEST (Direct API)")
    print("=" * 70)
    print()

    # Test configuration
    api_url = "http://localhost:11434/api/embeddings"
    model = "mxbai-embed-large"
    test_text = "This is a test of the Ollama embedding model with mxbai-embed-large"

    print(f"API URL: {api_url}")
    print(f"Model: {model}")
    print(f"Test text: '{test_text}'")
    print()

    try:
        # Generate embedding
        print("Generating embedding...")
        start_time = time.time()

        response = requests.post(
            api_url,
            json={
                "model": model,
                "prompt": test_text
            },
            timeout=30
        )

        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding', [])

            print(f"✅ Embedding generated successfully!")
            print(f"   Model: {model}")
            print(f"   Dimensions: {len(embedding)}")
            print(f"   Latency: {latency_ms:.2f}ms")
            print(f"   First 5 values: {embedding[:5]}")
            print(f"   Status Code: {response.status_code}")
            print()

            # Verify embedding quality
            if len(embedding) > 0 and all(isinstance(x, (int, float)) for x in embedding[:10]):
                print("✅ Embedding quality check passed")
                print()
                return True
            else:
                print("❌ Embedding quality check failed - invalid values")
                return False

        else:
            print(f"❌ API request failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is Ollama running?")
        print("   Try: ollama serve")
        return False

    except requests.exceptions.Timeout:
        print("❌ Request timed out (>30 seconds)")
        return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ollama_embedding()

    print()
    print("=" * 70)
    if success:
        print("✅ OLLAMA EMBEDDING TEST PASSED")
        print()
        print("The mxbai-embed-large model is working correctly!")
        print("Ollama embeddings are ready to use with the migration system.")
    else:
        print("❌ OLLAMA EMBEDDING TEST FAILED")
        print()
        print("Troubleshooting:")
        print("1. Verify Ollama is running: ollama list")
        print("2. Check model is installed: ollama list | grep mxbai")
        print("3. Try pulling model: ollama pull mxbai-embed-large")
        print("4. Check Ollama logs for errors")
    print("=" * 70)

    exit(0 if success else 1)
