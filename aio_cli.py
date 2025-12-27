#!/usr/bin/env python3
"""
AIO CLI - Simple command-line tool for content creators

This is the user-friendly interface for AIO signing.
No technical knowledge required.

Usage:
    python aio_cli.py setup          # First-time setup (creates keys)
    python aio_cli.py generate       # Generate Markdown Shadow
    python aio_cli.py sign           # Sign all HTML files
    python aio_cli.py watch          # Auto-sign when files change
    python aio_cli.py verify         # Verify all signatures
    python aio_cli.py status         # Show current status
"""

import os
import sys
import time
import glob
from pathlib import Path

# Import our signing module
try:
    import aio_signing as signer
except ImportError:
    print("Error: aio_signing.py not found in current directory")
    sys.exit(1)


def print_banner():
    print("""
    ╔═══════════════════════════════════════╗
    ║     AIO Content Signing Tool          ║
    ║     Protect your content integrity    ║
    ╚═══════════════════════════════════════╝
    """)


def cmd_setup():
    """First-time setup wizard."""
    print("\n🔧 SETUP WIZARD\n")
    print("This will create your signing keys.")
    print("Your PRIVATE key must be kept secret - never share it!\n")
    
    if signer.PRIVATE_KEY_FILE.exists():
        print("⚠️  Keys already exist!")
        response = input("Do you want to create NEW keys? (yes/no): ")
        if response.lower() != 'yes':
            print("Setup cancelled. Your existing keys are unchanged.")
            return
    
    signer.generate_keypair()
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("  1. Run: python aio_cli.py sign")
    print("  2. Or:  python aio_cli.py watch (to auto-sign on save)")


def cmd_sign():
    """Sign all HTML files in current directory."""
    print("\n📝 SIGNING ALL HTML FILES\n")
    
    if not signer.PRIVATE_KEY_FILE.exists():
        print("❌ No signing keys found!")
        print("   Run: python aio_cli.py setup")
        return
    
    html_files = glob.glob("*.html")
    
    if not html_files:
        print("No HTML files found in current directory.")
        return
    
    signed = 0
    skipped = 0
    
    for html_file in html_files:
        try:
            content, _ = signer.extract_markdown_content(html_file)
            if content:
                signer.sign_content(html_file)
                signed += 1
            else:
                print(f"  ⏭️  {html_file} - no markdown shadow, skipped")
                skipped += 1
        except Exception as e:
            print(f"  ❌ {html_file} - error: {e}")
    
    print(f"\n✅ Done! Signed: {signed}, Skipped: {skipped}")


def cmd_verify():
    """Verify all HTML files."""
    print("\n🔍 VERIFYING ALL SIGNATURES\n")
    
    html_files = glob.glob("*.html")
    
    if not html_files:
        print("No HTML files found.")
        return
    
    verified = 0
    failed = 0
    no_sig = 0
    
    for html_file in html_files:
        try:
            result = signer.verify_content(html_file)
            if result:
                verified += 1
            elif result is False:
                failed += 1
            else:
                no_sig += 1
        except Exception as e:
            print(f"  ❌ {html_file} - error: {e}")
            failed += 1
    
    print(f"\n📊 Results: ✅ Verified: {verified}, ❌ Failed: {failed}, ⏭️ No signature: {no_sig}")


def cmd_watch():
    """Watch for file changes and auto-sign."""
    print("\n👀 WATCHING FOR CHANGES\n")
    print("Press Ctrl+C to stop.\n")
    
    if not signer.PRIVATE_KEY_FILE.exists():
        print("❌ No signing keys found!")
        print("   Run: python aio_cli.py setup")
        return
    
    # Track file modification times
    file_times = {}
    
    def get_html_files():
        return {f: os.path.getmtime(f) for f in glob.glob("*.html")}
    
    file_times = get_html_files()
    print(f"Watching {len(file_times)} HTML files...")
    
    try:
        while True:
            time.sleep(1)
            current_files = get_html_files()
            
            for filepath, mtime in current_files.items():
                if filepath not in file_times or file_times[filepath] < mtime:
                    print(f"\n📄 Change detected: {filepath}")
                    try:
                        content, _ = signer.extract_markdown_content(filepath)
                        if content:
                            signer.sign_content(filepath)
                            print(f"   ✅ Auto-signed!")
                        else:
                            print(f"   ⏭️ No markdown shadow")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
            
            file_times = current_files
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching.")


def cmd_status():
    """Show current status."""
    print("\n📊 AIO STATUS\n")
    
    # Check keys
    if signer.PRIVATE_KEY_FILE.exists():
        print("🔑 Signing keys: ✅ Found")
        
        # Show public key
        try:
            pub_key = signer.load_public_key()
            import base64
            from cryptography.hazmat.primitives import serialization
            pub_b64 = base64.b64encode(pub_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )).decode('ascii')
            print(f"   Public key: {pub_b64[:20]}...")
        except:
            pass
    else:
        print("🔑 Signing keys: ❌ Not found (run 'setup')")
    
    # Check HTML files
    html_files = glob.glob("*.html")
    print(f"\n📄 HTML files: {len(html_files)} found")
    
    for html_file in html_files:
        try:
            content, soup = signer.extract_markdown_content(html_file)
            sig_meta = soup.find('meta', attrs={'name': 'aio-truth-signature'})
            
            has_shadow = "✅" if content else "❌"
            has_sig = "✅" if sig_meta and sig_meta.get('content', '') not in ['', 'UNSIGNED'] else "❌"
            
            print(f"   {html_file}: Shadow {has_shadow} | Signature {has_sig}")
        except Exception as e:
            print(f"   {html_file}: ❌ Error reading")


def print_help():
    print("""
📖 AVAILABLE COMMANDS:

    setup     First-time setup - creates your signing keys
    sign      Sign all HTML files in current folder
    watch     Auto-sign files when you save them
    verify    Check if all signatures are valid
    status    Show current setup status
    help      Show this help message

💡 QUICK START:
    1. python aio_cli.py setup
    2. python aio_cli.py sign
    
🔄 FOR CONTINUOUS WORK:
    python aio_cli.py watch
    (then just edit and save your HTML files)
    """)


def main():
    print_banner()
    
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'setup': cmd_setup,
        'generate': cmd_generate,
        'sign': cmd_sign,
        'verify': cmd_verify,
        'watch': cmd_watch,
        'status': cmd_status,
        'help': print_help,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"❌ Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    main()
