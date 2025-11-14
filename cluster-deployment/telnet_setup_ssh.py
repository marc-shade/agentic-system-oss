#!/usr/bin/env python3
"""
Setup SSH key via telnet for passwordless access
"""

import telnetlib
import time
import sys

def setup_ssh_key(host, username, password, public_key):
    """Connect via telnet and add SSH public key"""

    print(f"Connecting to {host} via telnet...")

    try:
        tn = telnetlib.Telnet(host, 23, timeout=10)

        # Login
        tn.read_until(b"login: ", timeout=5)
        tn.write(username.encode('ascii') + b"\n")

        tn.read_until(b"Password: ", timeout=5)
        tn.write(password.encode('ascii') + b"\n")

        time.sleep(2)
        response = tn.read_very_eager().decode('ascii', errors='ignore')

        if "Login incorrect" in response or "Authentication failed" in response:
            print("❌ Authentication failed!")
            return False

        print("✅ Authenticated successfully!")

        # Commands to find mount and setup SSH
        commands = [
            # Find the SSDRAID0 mount
            "mount | grep -i ssdraid || df -h | grep -i ssd",
            "ls -la /mnt/ 2>/dev/null || echo 'No /mnt/'",
            "ls -la /media/ 2>/dev/null || echo 'No /media/'",

            # Setup SSH directory
            "mkdir -p ~/.ssh",
            "chmod 700 ~/.ssh",
            "touch ~/.ssh/authorized_keys",
            "chmod 600 ~/.ssh/authorized_keys",

            # Add the public key
            f"echo '{public_key}' >> ~/.ssh/authorized_keys",

            # Verify it was added
            "tail -1 ~/.ssh/authorized_keys",

            # Show current directory structure
            "ls -la ~/ | grep ssh",

            "echo 'SSH key setup complete!'"
        ]

        for cmd in commands:
            print(f"\nExecuting: {cmd[:60]}...")
            tn.write(cmd.encode('ascii') + b"\n")
            time.sleep(1)
            output = tn.read_very_eager().decode('ascii', errors='ignore')

            # Clean up the output
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith('[marc@'):
                    print(f"  {line}")

        tn.write(b"exit\n")
        tn.close()

        print("\n✅ SSH key setup completed!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 telnet_setup_ssh.py <host> <username> <password> <public_key>")
        sys.exit(1)

    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    public_key = sys.argv[4]

    success = setup_ssh_key(host, username, password, public_key)
    sys.exit(0 if success else 1)
