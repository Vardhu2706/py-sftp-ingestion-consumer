#!/usr/bin/env python3
"""
Helper script to convert SSH private key and PGP public key to base64.
This makes it easy to add them as environment variables in Render.
"""
import base64
import sys
from pathlib import Path


def file_to_base64(file_path: Path) -> str:
    """Convert a file to base64 string."""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    return base64.b64encode(content).decode('utf-8')


def main():
    print("=" * 70)
    print("Convert Keys to Base64 for Render Environment Variables")
    print("=" * 70)
    print()
    
    # SSH Private Key
    ssh_key_path = Path("producer_key")
    if not ssh_key_path.exists():
        print(f"⚠️  SSH private key not found at: {ssh_key_path}")
        print("   Run 'python generate_ssh_key.py' first or provide path.")
        ssh_key_path_input = input("   Enter SSH private key path (or press Enter to skip): ").strip()
        if ssh_key_path_input:
            ssh_key_path = Path(ssh_key_path_input)
    
    if ssh_key_path.exists():
        try:
            ssh_base64 = file_to_base64(ssh_key_path)
            print("✅ SSH Private Key (Base64):")
            print("-" * 70)
            print(ssh_base64)
            print("-" * 70)
            print(f"\n   Add this to Render as: SFTP_PRIVATE_KEY_BASE64")
            print()
        except Exception as e:
            print(f"❌ Error reading SSH key: {e}")
    else:
        print("⚠️  Skipping SSH key conversion\n")
    
    # PGP Public Key
    pgp_key_path = Path("consumer_public_key.asc")
    if not pgp_key_path.exists():
        print(f"⚠️  PGP public key not found at: {pgp_key_path}")
        pgp_key_path_input = input("   Enter PGP public key path (or press Enter to skip): ").strip()
        if pgp_key_path_input:
            pgp_key_path = Path(pgp_key_path_input)
    
    if pgp_key_path.exists():
        try:
            pgp_base64 = file_to_base64(pgp_key_path)
            print("✅ PGP Public Key (Base64):")
            print("-" * 70)
            print(pgp_base64)
            print("-" * 70)
            print(f"\n   Add this to Render as: PGP_PUBLIC_KEY_BASE64")
            print()
        except Exception as e:
            print(f"❌ Error reading PGP key: {e}")
    else:
        print("⚠️  Skipping PGP key conversion\n")
    
    print("=" * 70)
    print("📋 Next Steps:")
    print("   1. Copy the base64 strings above")
    print("   2. Add them as environment variables in Render dashboard")
    print("   3. Deploy your service")
    print("=" * 70)


if __name__ == "__main__":
    main()
