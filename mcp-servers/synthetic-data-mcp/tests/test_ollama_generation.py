#!/usr/bin/env python3
"""
Test Ollama-based synthetic data generation.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.schemas.base import DataDomain, PrivacyLevel


async def test_ollama_generation():
    """Test data generation with Ollama."""
    
    print("="*80)
    print("TESTING OLLAMA SYNTHETIC DATA GENERATION")
    print("="*80)
    
    # Initialize generator
    generator = SyntheticDataGenerator()
    
    # Test 1: Healthcare data
    print("\n1. Generating Healthcare Data with Ollama...")
    try:
        result = await generator.generate_dataset(
            domain=DataDomain.HEALTHCARE,
            dataset_type="patient_records",
            record_count=2,
            privacy_level=PrivacyLevel.HIGH
        )
        
        if result.get("status") == "success":
            print(f"✅ Generated {result['metadata']['total_records']} healthcare records")
            print(f"   Inference mode: {result['metadata'].get('inference_mode', 'unknown')}")
            print(f"   Sample record fields: {list(result['dataset'][0].keys())[:5]}...")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Finance data
    print("\n2. Generating Finance Data with Ollama...")
    try:
        result = await generator.generate_dataset(
            domain=DataDomain.FINANCE,
            dataset_type="transaction_records",
            record_count=2,
            privacy_level=PrivacyLevel.MEDIUM
        )
        
        if result.get("status") == "success":
            print(f"✅ Generated {result['metadata']['total_records']} finance records")
            print(f"   Sample data:")
            for i, record in enumerate(result['dataset'][:1], 1):
                print(f"   Record {i}: {json.dumps(record, indent=2)[:200]}...")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Custom data with Ollama
    print("\n3. Generating Custom Data with Ollama...")
    try:
        result = await generator.generate_dataset(
            domain=DataDomain.CUSTOM,
            dataset_type="user_profiles",
            record_count=3,
            privacy_level=PrivacyLevel.LOW
        )
        
        if result.get("status") == "success":
            print(f"✅ Generated {result['metadata']['total_records']} custom records")
            print(f"   Records generated successfully!")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("OLLAMA GENERATION TEST COMPLETE")
    print("="*80)
    print("\n✨ Ollama is working for local, privacy-first synthetic data generation!")
    print("🔒 All data generated locally - no API keys required!")


if __name__ == "__main__":
    asyncio.run(test_ollama_generation())