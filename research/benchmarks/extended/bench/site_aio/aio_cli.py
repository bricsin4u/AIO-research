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


def cmd_generate():
    """Deprecated: AIO files are now generated automatically during signing."""
    print("\n⚠️  DEPRECATED: Use 'python aio_cli.py sign' to generate and sign .aio files.")
    cmd_sign()


def cmd_sign():
    """Sign all HTML files in current directory (Generates .aio files)."""
    print("\n📝 PROCESSING AND SIGNING HTML FILES\n")
    
    if not signer.PRIVATE_KEY_FILE.exists():
        print("❌ No signing keys found!")
        print("   Run: python aio_cli.py setup")
        return
    
    html_files = glob.glob("*.html")
    
    if not html_files:
        print("No HTML files found in current directory.")
        return
    
    signed = 0
    
    for html_file in html_files:
        try:
            # New workflow: Process (Gen + Sign)
            signer.process_aio(html_file)
            signed += 1
        except Exception as e:
            print(f"  ❌ {html_file} - error: {e}")
    
    print(f"\n✅ Done! Processed: {signed}")


def cmd_verify():
    """Verify all HTML files (checks companion .aio files)."""
    print("\n🔍 VERIFYING SIBLING .AIO FILES\n")
    
    html_files = glob.glob("*.html")
    
    if not html_files:
        print("No HTML files found.")
        return
    
    verified = 0
    failed = 0
    missing = 0
    
    for html_file in html_files:
        try:
            # Checks for [file].aio existence inside verify_content
            result = signer.verify_content(html_file)
            if result:
                verified += 1
            elif result is False:
                failed += 1
        except Exception as e:
            print(f"  ❌ {html_file} - error: {e}")
            failed += 1
    
    print(f"\n📊 Results: ✅ Verified: {verified}, ❌ Failed: {failed}")


def cmd_watch():
    """Watch for file changes and auto-process."""
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
                        signer.process_aio(filepath)
                        print(f"   ✅ Auto-processed!")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
            
            file_times = current_files
            
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching.")


def cmd_status():
    """Show current status."""
    print("\n📊 AIO STATUS (v2.0 Separate Architecture)\n")
    
    # Check keys
    if signer.PRIVATE_KEY_FILE.exists():
        print("🔑 Signing keys: ✅ Found")
    else:
        print("🔑 Signing keys: ❌ Not found (run 'setup')")
    
    # Check HTML files
    html_files = glob.glob("*.html")
    print(f"\n📄 HTML files: {len(html_files)} found")
    
    for html_file in html_files:
        aio_path = Path(html_file).with_suffix('.aio')
        has_aio = "✅" if aio_path.exists() else "❌"
        
        # Check Link Tag presence
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            has_link = "✅" if 'application/vnd.aio+json' in content else "❌"
        except:
            has_link = "?"
            
        print(f"   {html_file}: .aio File {has_aio} | HTML Link {has_link}")


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
