"""
Test credit card numbers for synthetic data generation.
These are officially documented test card numbers that will never work in production.
"""

import random
from typing import Optional, List

# Official test card numbers from various providers
# Source: Stripe, PayPal, and provider documentation
TEST_CARDS = {
    'visa': [
        '4242424242424242',  # Stripe test card (most common)
        '4111111111111111',  # Common test card
        '4012888888881881',  # Visa test
        '4000056655665556',  # Visa debit
        '4917610000000000',  # Visa corporate
        '4484070000000000',  # Visa purchasing
    ],
    'mastercard': [
        '5555555555554444',  # Mastercard test
        '5200828282828210',  # Mastercard debit
        '5105105105105100',  # Mastercard prepaid
        '2223003122003222',  # Mastercard 2-series
        '5425233430109903',  # Mastercard credit
        '2222420000001113',  # Mastercard corporate
    ],
    'amex': [
        '378282246310005',   # AmEx test
        '371449635398431',   # AmEx test
        '378734493671000',   # AmEx corporate
        '340000000000009',   # AmEx test
    ],
    'discover': [
        '6011111111111117',  # Discover test
        '6011000990139424',  # Discover test
        '6011501234567890',  # Discover test
        '6011601160116611',  # Discover rewards
    ],
    'diners': [
        '30569309025904',    # Diners Club
        '36006666666666',    # Diners test (14 digits)
        '38520000023237',    # Diners Club
    ],
    'jcb': [
        '3530111333300000',  # JCB test
        '3566002020360505',  # JCB test
        '3566111111111113',  # JCB test
    ],
    'unionpay': [
        '6200000000000005',  # UnionPay test
        '6250947000000016',  # UnionPay debit
        '6282000000000000',  # UnionPay credit
    ],
    'maestro': [
        '6759649826438453',  # Maestro UK
        '6799990100000000019',  # Maestro test
        '5018000000000009',  # Maestro
    ]
}

# Provider distribution weights (based on market share)
PROVIDER_WEIGHTS = {
    'visa': 0.40,
    'mastercard': 0.30,
    'amex': 0.10,
    'discover': 0.08,
    'diners': 0.03,
    'jcb': 0.03,
    'unionpay': 0.04,
    'maestro': 0.02
}


def get_test_card(provider: Optional[str] = None, formatted: bool = True) -> str:
    """
    Get a test credit card number.
    
    Args:
        provider: Optional specific provider (visa, mastercard, etc.)
                 If not specified, uses weighted random selection
        formatted: Whether to format with dashes (default True)
    
    Returns:
        Test credit card number
    """
    if provider:
        # Normalize provider name
        provider = provider.lower()
        if provider in TEST_CARDS:
            card = random.choice(TEST_CARDS[provider])
        else:
            # If invalid provider, default to Visa
            card = random.choice(TEST_CARDS['visa'])
    else:
        # Select provider based on weights
        selected_provider = random.choices(
            list(PROVIDER_WEIGHTS.keys()),
            weights=list(PROVIDER_WEIGHTS.values())
        )[0]
        card = random.choice(TEST_CARDS[selected_provider])
    
    if formatted:
        return format_card_number(card)
    return card


def format_card_number(card: str) -> str:
    """
    Format a credit card number with dashes.
    
    Args:
        card: Credit card number without formatting
    
    Returns:
        Formatted card number (e.g., 4242-4242-4242-4242)
    """
    # Remove any existing formatting
    card = card.replace('-', '').replace(' ', '')
    
    # Format based on length
    if len(card) == 15:  # AmEx format: 4-6-5
        return f"{card[:4]}-{card[4:10]}-{card[10:]}"
    elif len(card) == 14:  # Diners format: 4-6-4
        return f"{card[:4]}-{card[4:10]}-{card[10:]}"
    elif len(card) == 16:  # Standard format: 4-4-4-4
        return f"{card[:4]}-{card[4:8]}-{card[8:12]}-{card[12:]}"
    elif len(card) == 19:  # Some Maestro cards
        return f"{card[:4]}-{card[4:8]}-{card[8:12]}-{card[12:16]}-{card[16:]}"
    else:
        # Return as-is if unusual length
        return card


def get_test_cards_by_provider(provider: str, count: int = 1, formatted: bool = True) -> List[str]:
    """
    Get multiple test cards from a specific provider.
    
    Args:
        provider: Provider name (visa, mastercard, etc.)
        count: Number of cards to return
        formatted: Whether to format with dashes
    
    Returns:
        List of test credit card numbers
    """
    provider = provider.lower()
    if provider not in TEST_CARDS:
        raise ValueError(f"Unknown provider: {provider}. Valid options: {', '.join(TEST_CARDS.keys())}")
    
    cards = []
    available_cards = TEST_CARDS[provider].copy()
    
    for _ in range(min(count, len(available_cards))):
        if available_cards:
            card = random.choice(available_cards)
            available_cards.remove(card)  # Avoid duplicates
            if formatted:
                card = format_card_number(card)
            cards.append(card)
    
    # If we need more cards than available, repeat with randomization
    while len(cards) < count:
        card = random.choice(TEST_CARDS[provider])
        if formatted:
            card = format_card_number(card)
        cards.append(card)
    
    return cards


def get_specific_test_card(card_number: str, formatted: bool = True) -> str:
    """
    Format a specific test card number provided by the user.
    
    Args:
        card_number: The test card number to use
        formatted: Whether to format with dashes
    
    Returns:
        Formatted test card number
    """
    # Clean the input
    card_number = card_number.replace('-', '').replace(' ', '')
    
    # Validate it's a known test card
    is_test_card = False
    for provider_cards in TEST_CARDS.values():
        if card_number in provider_cards:
            is_test_card = True
            break
    
    if not is_test_card:
        # Log warning but still allow it (user might know a test card we don't)
        import logging
        logging.warning(f"Card {card_number[:4]}...{card_number[-4:]} not in known test cards list")
    
    if formatted:
        return format_card_number(card_number)
    return card_number


def get_all_providers() -> List[str]:
    """Get list of all supported credit card providers."""
    return list(TEST_CARDS.keys())


def validate_test_card(card_number: str) -> bool:
    """
    Check if a card number is a known test card.
    
    Args:
        card_number: Card number to check
    
    Returns:
        True if it's a known test card
    """
    # Clean the input
    card_number = card_number.replace('-', '').replace(' ', '')
    
    for provider_cards in TEST_CARDS.values():
        if card_number in provider_cards:
            return True
    return False