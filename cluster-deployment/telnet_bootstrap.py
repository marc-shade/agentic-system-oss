#!/usr/bin/env python3
"""
Telnet Bootstrap Client for macpro51
Establishes telnet connection and executes bootstrap commands
"""

import telnetlib
import time
import sys

def telnet_bootstrap(host, username, password, commands):
    """Connect via telnet and execute commands"""

    print(f"Connecting to {host} via telnet...")

    try:
        # Connect to telnet
        tn = telnetlib.Telnet(host, 23, timeout=10)

        # Wait for login prompt
        tn.read_until(b"login: ", timeout=5)
        tn.write(username.encode('ascii') + b"\n")
        print(f"Sent username: {username}")

        # Wait for password prompt
        tn.read_until(b"Password: ", timeout=5)
        tn.write(password.encode('ascii') + b"\n")
        print("Sent password")

        # Wait for shell prompt (could be $, #, or >)
        time.sleep(2)
        response = tn.read_very_eager().decode('ascii', errors='ignore')
        print(f"Login response:\n{response}")

        if "Login incorrect" in response or "Authentication failed" in response:
            print("❌ Authentication failed!")
            return False

        print("✅ Authenticated successfully!")

        # Execute commands
        for i, cmd in enumerate(commands, 1):
            print(f"\n[{i}/{len(commands)}] Executing: {cmd}")
            tn.write(cmd.encode('ascii') + b"\n")
            time.sleep(1)
            output = tn.read_very_eager().decode('ascii', errors='ignore')
            print(f"Output:\n{output}")

        # Close connection
        tn.write(b"exit\n")
        tn.close()

        print("\n✅ Bootstrap completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 telnet_bootstrap.py <host> <username> <password>")
        sys.exit(1)

    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3] if len(sys.argv) > 3 else input("Password: ")

    # Bootstrap commands
    commands = [
        "hostname",
        "whoami",
        "pwd",
        # Setup SSH key
        "mkdir -p ~/.ssh",
        "chmod 700 ~/.ssh",
        # The key will be added via separate command
        # Start command listener
        "cd /mnt/ssdraid0/agentic-system/cluster-deployment || cd /Volumes/SSDRAID0/agentic-system/cluster-deployment",
        "nohup python3 node_command_listener.py macpro51 9999 > /tmp/node_listener.log 2>&1 &",
        "echo 'Command listener started on port 9999'",
        # Verify it's running
        "sleep 2",
        "ps aux | grep node_command_listener | grep -v grep",
        "echo 'Bootstrap complete!'"
    ]

    success = telnet_bootstrap(host, username, password, commands)
    sys.exit(0 if success else 1)
