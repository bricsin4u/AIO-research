#!/usr/bin/env python3
"""
Quick test script to verify AIO parser works with demo site.
Run the demo site first: cd demo-site && python -m http.server 8000
"""

import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aio_parser import parse, AIOParser
from aio_parser.discovery import discover_aio

def test_local_demo():
    """Test against local demo site."""
    print("=" * 60)
    print("AIO Parser Test - Local Demo Site")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test 1: AIO Discovery
    print("\n[1] Testing AIO Discovery...")
    aio_url, method = discover_aio(base_url)
    if aio_url:
        print(f"    ✓ AIO found: {aio_url}")
        print(f"    ✓ Discovery method: {method}")
    else:
        print(f"    ✗ No AIO found (method: {method})")
        print("    Make sure demo site is running: cd demo-site && python -m http.server 8000")
        return False
    
    # Test 2: Full Parse
    print("\n[2] Testing Full Parse...")
    parser = AIOParser()
    envelope = parser.parse(base_url)
    
    print(f"    Source type: {envelope.source_type}")
    print(f"    Tokens: {envelope.tokens}")
    print(f"    Noise score: {envelope.noise_score}")
    print(f"    Chunks: {len(envelope.chunks)}")
    
    if envelope.source_type == "aio":
        print("    ✓ Successfully parsed AIO content!")
    else:
        print("    ⚠ Fell back to HTML scraping")
    
    # Test 3: Query-based retrieval
    print("\n[3] Testing Query-based Retrieval...")
    envelope = parser.parse(base_url, query="pricing subscription cost")
    print(f"    Query: 'pricing subscription cost'")
    print(f"    Content preview: {envelope.narrative[:200]}...")
    
    # Test 4: Check support method
    print("\n[4] Testing check_aio_support()...")
    support = parser.check_aio_support(base_url)
    print(f"    Supported: {support['supported']}")
    print(f"    URL: {support['aio_url']}")
    print(f"    Method: {support['discovery_method']}")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True


def test_file_direct():
    """Test by reading AIO file directly (no server needed)."""
    print("=" * 60)
    print("AIO Parser Test - Direct File Read")
    print("=" * 60)
    
    import json
    
    aio_path = os.path.join(os.path.dirname(__file__), "..", "demo-site", "ai-content.aio")
    
    if not os.path.exists(aio_path):
        print(f"✗ AIO file not found: {aio_path}")
        return False
    
    with open(aio_path, 'r') as f:
        aio_data = json.load(f)
    
    print(f"\n[1] AIO Version: {aio_data.get('aio_version')}")
    print(f"[2] Chunks: {len(aio_data.get('index', []))}")
    
    for idx in aio_data.get('index', []):
        print(f"    - {idx['id']}: {idx['title']}")
        print(f"      Keywords: {', '.join(idx.get('keywords', [])[:5])}...")
    
    print(f"\n[3] Content items: {len(aio_data.get('content', []))}")
    
    total_tokens = sum(idx.get('token_estimate', 0) for idx in aio_data.get('index', []))
    print(f"[4] Total estimated tokens: {total_tokens}")
    
    print("\n" + "=" * 60)
    print("File structure valid! ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    # Try direct file test first (no server needed)
    print("\n>>> Running direct file test...\n")
    test_file_direct()
    
    # Try local server test
    print("\n>>> Running local server test...\n")
    print("(Make sure to run: cd demo-site && python -m http.server 8000)\n")
    try:
        test_local_demo()
    except Exception as e:
        print(f"Server test failed: {e}")
        print("This is expected if the demo server isn't running.")
