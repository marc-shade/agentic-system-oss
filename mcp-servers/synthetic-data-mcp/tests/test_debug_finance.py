#!/usr/bin/env python3
"""
Debug finance generation issue.
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.schemas.base import DataDomain, PrivacyLevel


async def test_finance_debug():
    """Debug finance data generation with Ollama."""
    
    print("="*80)
    print("DEBUGGING FINANCE DATA GENERATION")
    print("="*80)
    
    # Initialize generator
    generator = SyntheticDataGenerator()
    
    # Test Finance data with detailed error catching
    print("\nGenerating Finance Data with Ollama...")
    try:
        result = await generator.generate_dataset(
            domain=DataDomain.FINANCE,
            dataset_type="transaction_records",
            record_count=1,
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
        print("\nFull traceback:")
        traceback.print_exc()
        
        # Try to get more info about the error
        print("\n\nAttempting to generate finance data with faker fallback...")
        try:
            # Try with Faker directly
            from faker import Faker
            faker = Faker()
            sample = {
                "transaction_id": str(faker.uuid4()),
                "amount": round(faker.random.uniform(10, 10000), 2),
                "timestamp": faker.date_time_this_year().isoformat()
            }
            print(f"✅ Faker can generate basic finance data: {sample}")
        except Exception as e2:
            print(f"❌ Even Faker failed: {e2}")


if __name__ == "__main__":
    asyncio.run(test_finance_debug())