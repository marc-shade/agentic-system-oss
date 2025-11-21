#!/usr/bin/env python3
"""
Test script for YouTube transcript MCP pagination features.
"""

import json
from server import get_transcript, get_transcript_summary, get_transcript_languages

def test_pagination_features():
    """Test the new pagination and limiting features."""
    test_video = "https://youtu.be/Auuk1y4DRgk"  # Marcus Aurelius video
    
    print("🧪 Testing YouTube Transcript MCP Pagination Features")
    print("=" * 60)
    
    # Test 1: Get available languages
    print("\n1. Testing get_transcript_languages...")
    languages = get_transcript_languages(test_video)
    print(f"   Languages available: {languages['success']}")
    if languages['success']:
        print(f"   Found {len(languages['languages'])} language options")
    
    # Test 2: Get first 1000 characters
    print("\n2. Testing max_length parameter (1000 chars)...")
    result = get_transcript(test_video, max_length=1000)
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Character count: {result['character_count']}")
        print(f"   Total length: {result['total_length']}")
        print(f"   Has more: {result['has_more']}")
        if result.get('next_offset'):
            print(f"   Next offset: {result['next_offset']}")
    
    # Test 3: Get second page using offset
    print("\n3. Testing pagination with offset...")
    if result['success'] and result.get('next_offset'):
        result2 = get_transcript(test_video, max_length=1000, offset=result['next_offset'])
        print(f"   Success: {result2['success']}")
        if result2['success']:
            print(f"   Character count: {result2['character_count']}")
            print(f"   Offset: {result2['offset']}")
            print(f"   Has more: {result2['has_more']}")
    
    # Test 4: Test page_size parameter
    print("\n4. Testing page_size parameter (800 chars per page)...")
    result3 = get_transcript(test_video, page_size=800)
    print(f"   Success: {result3['success']}")
    if result3['success']:
        print(f"   Character count: {result3['character_count']}")
        print(f"   Current page: {result3.get('current_page', 'N/A')}")
        print(f"   Total pages: {result3.get('total_pages', 'N/A')}")
        print(f"   Page size: {result3.get('page_size', 'N/A')}")
    
    # Test 5: Test summary function
    print("\n5. Testing get_transcript_summary...")
    summary = get_transcript_summary(test_video, summary_length=2000)
    print(f"   Success: {summary['success']}")
    if summary['success']:
        print(f"   Summary length: {summary['character_count']}")
        print(f"   Original length: {summary.get('total_length', 'N/A')}")
        print(f"   Compression ratio: {summary.get('compression_ratio', 'N/A')}")
        print(f"   Is summary: {summary.get('is_summary', False)}")
        print(f"   Summary type: {summary.get('summary_type', 'N/A')}")
    
    print("\n" + "=" * 60)
    print("✅ Pagination testing complete!")
    
    return result, summary

if __name__ == "__main__":
    test_pagination_features()