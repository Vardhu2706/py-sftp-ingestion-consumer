#!/usr/bin/env python3
"""
Script to generate SSH key pair for SFTP authentication.
This creates a key pair that the consumer will use to connect to the SFTP server.
"""
import os
import subprocess
from pathlib import Path


def generate_ssh_key(key_name: str = "consumer_key", key_type: str = "ed25519"):
    """Generate an SSH key pair for SFTP authentication."""
    
    key_path = Path(key_name)
    pub_key_path = Path(f"{key_name}.pub")
    
    # Check if keys already exist
    if key_path.exists() or pub_key_path.exists():
        response = input(f"Keys {key_name} or {key_name}.pub already exist. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
        key_path.unlink(missing_ok=True)
        pub_key_path.unlink(missing_ok=True)
    
    print(f"Generating {key_type} SSH key pair...")
    
    try:
        if key_type == "ed25519":
            subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-C", "sftp-consumer", "-f", str(key_path), "-N", ""],
                check=True,
                capture_output=True
            )
        elif key_type == "rsa":
            subprocess.run(
                ["ssh-keygen", "-t", "rsa", "-b", "4096", "-C", "sftp-consumer", "-f", str(key_path), "-N", ""],
                check=True,
                capture_output=True
            )
        else:
            raise ValueError(f"Unsupported key type: {key_type}")
        
        print(f"✅ SSH key pair generated successfully!")
        print(f"\nPrivate key: {key_path}")
        print(f"Public key:  {pub_key_path}")
        
        # Display public key
        with open(pub_key_path, 'r') as f:
            pub_key = f.read().strip()
        
        print(f"\n📋 Public Key (add this to SFTP server's authorized_keys):")
        print("-" * 70)
        print(pub_key)
        print("-" * 70)
        
        print(f"\n⚠️  IMPORTANT:")
        print(f"   1. Keep {key_path} SECRET - never commit it to git!")
        print(f"   2. Add the public key above to your SFTP server's authorized_keys")
        print(f"   3. The private key will be used in SFTP_PRIVATE_KEY_PATH")
        
        # Check if .gitignore exists and add key
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            if key_name not in content:
                gitignore.write_text(content + f"\n# SSH keys\n{key_name}\n{key_name}.pub\n")
                print(f"   4. Added {key_name}* to .gitignore")
        else:
            gitignore.write_text(f"# SSH keys\n{key_name}\n{key_name}.pub\n")
            print(f"   4. Created .gitignore and added {key_name}*")
        
    except FileNotFoundError:
        print("❌ Error: ssh-keygen not found. Install OpenSSH:")
        print("   - Windows: Install Git for Windows or OpenSSH")
        print("   - Mac: Should be pre-installed")
        print("   - Linux: sudo apt-get install openssh-client")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating key: {e}")
        print(e.stderr.decode() if e.stderr else "")


if __name__ == "__main__":
    import sys
    
    key_type = "ed25519"
    if len(sys.argv) > 1:
        key_type = sys.argv[1].lower()
        if key_type not in ["ed25519", "rsa"]:
            print(f"Invalid key type: {key_type}. Use 'ed25519' or 'rsa'")
            sys.exit(1)
    
    generate_ssh_key(key_type=key_type)
