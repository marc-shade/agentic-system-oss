#!/usr/bin/env python3
"""
Simple test for finance generation.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from synthetic_data_mcp.core.generator import SyntheticDataGenerator
from synthetic_data_mcp.schemas.base import DataDomain, PrivacyLevel, ComplianceFramework
from synthetic_data_mcp.compliance.validator import ComplianceValidator


async def main():
    """Test finance generation."""
    
    print("Testing finance generation...")
    
    generator = SyntheticDataGenerator()
    compliance_validator = ComplianceValidator()
    
    try:
        # Generate transaction records
        dataset = await generator.generate_dataset(
            domain=DataDomain.FINANCE,
            dataset_type="transaction_records",
            record_count=5,
            privacy_level=PrivacyLevel.HIGH
        )
        
        print(f"Generation result status: {dataset.get('status')}")
        
        if dataset.get("status") == "success":
            actual_data = dataset["dataset"]
            print(f"Generated {len(actual_data)} records")
            
            # Validate compliance
            compliance_results = await compliance_validator.validate_dataset(
                dataset=actual_data,
                frameworks=[ComplianceFramework.PCI_DSS],
                domain=DataDomain.FINANCE
            )
            
            print(f"Compliance results: {compliance_results}")
            passed = compliance_results.get(ComplianceFramework.PCI_DSS.value, {}).get("passed", False)
            print(f"PCI DSS Compliance: {'PASSED' if passed else 'FAILED'}")
            
        else:
            print(f"Generation failed: {dataset.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())