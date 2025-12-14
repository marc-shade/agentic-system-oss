#!/usr/bin/env python3
"""Quick test to verify basic functionality."""

import asyncio
from synthetic_data_mcp.core.generator import SyntheticDataGenerator

async def main():
    print("Testing synthetic data generation...")
    
    # Initialize generator
    generator = SyntheticDataGenerator()
    print("✓ Generator initialized")
    
    # Generate small healthcare dataset
    print("\nGenerating 5 healthcare records...")
    result = await generator.generate_dataset(
        domain="healthcare",
        dataset_type="healthcare",
        record_count=5,
        privacy_level="medium"
    )
    
    print(f"✓ Status: {result['status']}")
    print(f"✓ Records generated: {result['metadata']['total_records']}")
    
    # Check that we have data
    if result['dataset']:
        print(f"✓ Dataset contains data")
        print(f"  Sample fields: {list(result['dataset'][0].keys())[:5]}")
    
    print("\n✅ Basic test passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)