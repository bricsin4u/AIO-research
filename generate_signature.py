"""
AIO Truth Signature Generator

This script generates SHA-256 hashes for the Markdown Shadow content
in your HTML files. Run this whenever you update content to keep
the truth signatures in sync.

Usage:
    python generate_signature.py index.html
    python generate_signature.py --all
"""

import hashlib
import sys
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def extract_markdown_content(html_path):
    """Extract the markdown shadow content from an HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    md_block = soup.find('script', type='text/markdown')
    if not md_block or not md_block.string:
        return None
    
    return md_block.string.strip()

def generate_hash(content):
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def update_html_signature(html_path, new_hash):
    """Update the aio-truth-signature meta tag in the HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the signature meta tag
    pattern = r'(<meta\s+name=["\']aio-truth-signature["\']\s+content=["\'])[^"\']*(["\'])'
    replacement = rf'\g<1>{new_hash}\g<2>'
    
    new_content, count = re.subn(pattern, replacement, content)
    
    if count == 0:
        print(f"  Warning: No aio-truth-signature meta tag found in {html_path}")
        return False
    
    # Also update the last-verified timestamp
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    timestamp_pattern = r'(<meta\s+name=["\']aio-last-verified["\']\s+content=["\'])[^"\']*(["\'])'
    new_content = re.sub(timestamp_pattern, rf'\g<1>{timestamp}\g<2>', new_content)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def process_file(html_path):
    """Process a single HTML file."""
    print(f"\nProcessing: {html_path}")
    
    content = extract_markdown_content(html_path)
    if content is None:
        print(f"  Skipped: No markdown shadow found")
        return
    
    new_hash = generate_hash(content)
    print(f"  Content hash: {new_hash}")
    
    if update_html_signature(html_path, new_hash):
        print(f"  Updated signature in file")
    
    return new_hash

def find_aio_html_files():
    """Find all HTML files that might contain AIO content."""
    html_files = []
    for f in os.listdir('.'):
        if f.endswith('.html'):
            html_files.append(f)
    return html_files

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_signature.py <file.html> [file2.html ...]")
        print("       python generate_signature.py --all")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        files = find_aio_html_files()
        print(f"Found {len(files)} HTML files")
    else:
        files = sys.argv[1:]
    
    results = {}
    for html_file in files:
        if not os.path.exists(html_file):
            print(f"Error: {html_file} not found")
            continue
        
        hash_result = process_file(html_file)
        if hash_result:
            results[html_file] = hash_result
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for file, hash_val in results.items():
        print(f"{file}: {hash_val[:16]}...")

if __name__ == "__main__":
    main()
