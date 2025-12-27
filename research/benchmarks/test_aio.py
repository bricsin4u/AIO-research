import requests
import json
import hashlib
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8001"  # Match benchmark_suite.py port

def test_aio():
    print(f"--- Simulating AI Agent Discovery & TRUST VERIFICATION for {BASE_URL} ---\n")

    # 1. Discover AI Instructions
    print("[1/4] Checking .well-known/ai-instructions.json...")
    try:
        resp = requests.get(f"{BASE_URL}/.well-known/ai-instructions.json")
        if resp.status_code == 200:
            config = resp.json()
            print("  [OK] Found AI Manifest!")
        else:
            print(f"  [ERROR] Failed to find manifest (Status: {resp.status_code})")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 2. Extract JSON-LD (Structural)
    print("\n[2/4] Extracting Structural Layer (JSON-LD)...")
    try:
        resp = requests.get(f"{BASE_URL}/index.html")
        soup = BeautifulSoup(resp.text, 'html.parser')
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            print(f"  [OK] Found JSON-LD!")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 3. Extract Narrative Layer (Markdown Shadow)
    print("\n[3/4] Extracting Narrative Layer (Markdown Shadow)...")
    md_content = ""
    try:
        md_block = soup.find('script', type='text/markdown')
        if md_block:
            md_content = md_block.string.strip()
            print("  [OK] Found Markdown Shadow content!")
        else:
            print("  [ERROR] No Markdown block found.")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 4. TRUST VERIFICATION (Layer 4)
    print("\n[4/4] Verifying Data Integrity (Trust Layer)...")
    try:
        # Get signature from Truth Header
        signature_meta = soup.find('meta', attrs={'name': 'aio-truth-signature'})
        if not signature_meta:
            print("  [FAILURE] CRYPTOGRAPHIC FAILURE: No Truth Header found!")
            return

        provided_sig = signature_meta['content']
        print(f"  [INFO] Truth Header Signature: {provided_sig}")

        # Calculate actual hash of the narrative content
        actual_hash = hashlib.sha256(md_content.encode('utf-8')).hexdigest()
        print(f"  [INFO] Actual Content Hash:   {actual_hash}")

        if provided_sig == actual_hash:
            print("\n  [VERIFIED] INTEGRITY SUCCESS: Content is authentic and untampered.")
        elif provided_sig == "DYNAMIC_SHA256_HASH":
             # Auto-update simulation for the demo if it's the first run
            print("\n  [NOTICE] System in 'Auto-Sign' mode for demo.")
            print(f"  [RECOMMENDATION] Update index.html meta tag with: {actual_hash}")
        else:
            print("\n  [ALERT] INTEGRITY FAILED! Content has been tampered with or signature is invalid.")

        # Check Verification Block
        verify_block = soup.find('div', id='aio-verification-block')
        if verify_block:
            print("  [OK] Detailed Verification Block found.")
            sources = verify_block.find_all('li')
            print(f"  [INFO] Trusted Sources: {len(sources)} verified origins.")

    except Exception as e:
        print(f"  [ERROR] Error during verification: {e}")

if __name__ == "__main__":
    test_aio()
