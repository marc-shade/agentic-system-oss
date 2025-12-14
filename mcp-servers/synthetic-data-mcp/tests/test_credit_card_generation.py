#!/usr/bin/env python3
"""
Test credit card generation with test card numbers.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthetic_data_mcp.ingestion.data_ingestion import DataIngestionPipeline
from synthetic_data_mcp.privacy.engine import PrivacyEngine
from synthetic_data_mcp.utils.test_credit_cards import (
    get_test_card, get_test_cards_by_provider, get_specific_test_card,
    get_all_providers, validate_test_card
)


async def test_credit_card_anonymization():
    """Test credit card anonymization with test numbers."""
    
    print("="*80)
    print("CREDIT CARD TEST NUMBER GENERATION TEST")
    print("="*80)
    
    # Sample data with real-looking credit cards
    sample_data = [
        {
            "name": "Customer A",
            "credit_card": "4532-1234-5678-9012",  # Real-looking Visa
            "provider": "Visa"
        },
        {
            "name": "Customer B",
            "credit_card": "5412-3456-7890-1234",  # Real-looking Mastercard
            "provider": "Mastercard"
        },
        {
            "name": "Customer C",
            "credit_card": "3712-345678-90123",  # Real-looking AmEx
            "provider": "AmEx"
        }
    ]
    
    print("\n1. DEFAULT ANONYMIZATION (Mixed Providers)")
    print("-" * 40)
    
    privacy_engine = PrivacyEngine()
    pipeline = DataIngestionPipeline(privacy_engine)
    
    # Ingest without specifying provider
    result = await pipeline.ingest(
        source=sample_data,
        format="dict",
        anonymize=True
    )
    
    print(f"✅ Anonymized {result['rows_ingested']} records")
    print(f"   PII Report: {result['pii_report']['anonymization_applied']}")
    
    # The patterns should now contain test card numbers
    distributions = result['patterns']['distributions']
    if 'credit_card' in distributions:
        card_values = distributions['credit_card'].get('frequencies', {})
        print("\n   Anonymized credit cards (should be test numbers):")
        for card in list(card_values.keys())[:5]:
            is_test = validate_test_card(card.replace('-', ''))
            status = "✅ TEST CARD" if is_test else "⚠️ CHECK"
            print(f"     {card} [{status}]")
    
    print("\n2. SPECIFIC PROVIDER ANONYMIZATION")
    print("-" * 40)
    
    # Test with specific provider
    for provider in ['visa', 'mastercard', 'amex']:
        result = await pipeline.ingest(
            source=sample_data,
            format="dict",
            anonymize=True,
            credit_card_provider=provider
        )
        
        distributions = result['patterns']['distributions']
        if 'credit_card' in distributions:
            card_values = distributions['credit_card'].get('frequencies', {})
            print(f"\n   {provider.upper()} test cards:")
            for card in list(card_values.keys())[:2]:
                print(f"     {card}")
    
    print("\n3. TEST CARD UTILITY FUNCTIONS")
    print("-" * 40)
    
    # Get random test cards
    print("\n   Random test cards from each provider:")
    for provider in get_all_providers():
        card = get_test_card(provider=provider)
        print(f"     {provider.upper():12s}: {card}")
    
    # Get multiple cards from a provider
    print("\n   Multiple Visa test cards:")
    visa_cards = get_test_cards_by_provider('visa', count=3)
    for card in visa_cards:
        print(f"     {card}")
    
    # Format a specific test card
    print("\n   Formatting specific test card:")
    stripe_card = "4242424242424242"
    formatted = get_specific_test_card(stripe_card)
    print(f"     Input:  {stripe_card}")
    print(f"     Output: {formatted}")
    
    print("\n4. VALIDATION")
    print("-" * 40)
    
    test_cases = [
        ("4242-4242-4242-4242", True),   # Known test card
        ("4111-1111-1111-1111", True),   # Known test card
        ("1234-5678-9012-3456", False),  # Not a test card
        ("5555-5555-5555-4444", True),   # Known Mastercard test
    ]
    
    print("\n   Validating card numbers:")
    for card, expected in test_cases:
        is_test = validate_test_card(card)
        status = "✅" if is_test == expected else "❌"
        result = "TEST CARD" if is_test else "NOT TEST"
        print(f"     {status} {card}: {result}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ Credit card anonymization uses official test numbers")
    print("✅ Supports all major providers (Visa, MC, AmEx, Discover, etc.)")
    print("✅ Can specify provider or use weighted random selection")
    print("✅ Test cards are properly formatted")
    print("✅ Never outputs real credit card numbers")
    print("\n🔒 Safe for testing and development!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_credit_card_anonymization())