#!/usr/bin/env python3
"""
Direct test script for YouTube transcript functionality
Tests both youtube-transcript-api and yt-dlp methods
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from server import YouTubeTranscriptServer

def test_direct_usage():
    """Test the YouTube transcript server directly (not via MCP)."""
    
    print("🎬 YouTube Transcript Direct Usage Test")
    print("=" * 50)
    
    # Initialize server
    server = YouTubeTranscriptServer()
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=RGWXVbkrYKM"
    
    print(f"📹 Testing with URL: {test_url}")
    print()
    
    # Test the get_transcript method directly
    result = server.get_transcript({
        "url": test_url,
        "lang": "en"
    })
    
    print("📊 Results:")
    print("-" * 30)
    
    if result.get("success"):
        print(f"✅ Status: Success")
        print(f"🔍 Method: {result.get('method', 'unknown')}")
        print(f"🆔 Video ID: {result.get('video_id', 'unknown')}")
        print(f"🗣️ Language: {result.get('language', 'unknown')}")
        
        transcript = result.get('transcript', '')
        if transcript:
            print(f"📝 Transcript length: {len(transcript)} characters")
            print(f"🔢 Segments: {result.get('segments', result.get('length', 'unknown'))}")
            print()
            print("📄 First 500 characters of transcript:")
            print("-" * 40)
            print(transcript[:500] + ("..." if len(transcript) > 500 else ""))
            print("-" * 40)
            
            # Save full transcript to file
            output_file = Path(__file__).parent / f"test_transcript_{result.get('video_id', 'unknown')}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"💾 Full transcript saved to: {output_file}")
        else:
            print("⚠️ No transcript content returned")
    else:
        print(f"❌ Status: Failed")
        print(f"🚨 Error: {result.get('error', 'unknown error')}")
        if 'output' in result:
            print(f"📤 Output: {result['output']}")
    
    print()
    print("=" * 50)
    return result

def test_multiple_methods():
    """Test different transcript extraction methods individually."""
    
    print("🔬 Testing Individual Methods")
    print("=" * 50)
    
    server = YouTubeTranscriptServer()
    video_id = "RGWXVbkrYKM"
    
    print(f"🆔 Video ID: {video_id}")
    print()
    
    # Test youtube-transcript-api method
    print("📚 Testing youtube-transcript-api method...")
    api_result = server.get_transcript_via_api(video_id, "en")
    print(f"   Result: {'✅ Success' if api_result.get('success') else '❌ Failed'}")
    if not api_result.get('success'):
        print(f"   Error: {api_result.get('error')}")
    print()
    
    # Test yt-dlp method  
    print("🔧 Testing yt-dlp method...")
    ytdlp_result = server.get_transcript_via_ytdlp(video_id, "en")
    print(f"   Result: {'✅ Success' if ytdlp_result.get('success') else '❌ Failed'}")
    if not ytdlp_result.get('success'):
        print(f"   Error: {ytdlp_result.get('error')}")
    print()
    
    # Test script method
    print("📜 Testing script method...")
    script_result = server.get_transcript_via_script(video_id, "en")
    print(f"   Result: {'✅ Success' if script_result.get('success') else '❌ Failed'}")
    if not script_result.get('success'):
        print(f"   Error: {script_result.get('error')}")
    
    print("=" * 50)
    return {
        'api': api_result,
        'ytdlp': ytdlp_result,
        'script': script_result
    }

if __name__ == "__main__":
    print("🚀 Starting YouTube Transcript Tests")
    print()
    
    # Run direct usage test
    direct_result = test_direct_usage()
    print()
    
    # Run individual method tests
    method_results = test_multiple_methods()
    
    print()
    print("📋 Summary:")
    print("-" * 30)
    print(f"Direct usage: {'✅ Success' if direct_result.get('success') else '❌ Failed'}")
    print(f"API method: {'✅ Success' if method_results['api'].get('success') else '❌ Failed'}")
    print(f"yt-dlp method: {'✅ Success' if method_results['ytdlp'].get('success') else '❌ Failed'}")
    print(f"Script method: {'✅ Success' if method_results['script'].get('success') else '❌ Failed'}")
    
    print()
    print("🏁 Test complete!")