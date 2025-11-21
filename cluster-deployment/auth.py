#!/usr/bin/env python3
"""
Cryptographic Authentication for GitMQ Messages
================================================

Provides message signing and verification using Ed25519 signatures.
Every message exchanged between nodes must be signed by the sender.

Security Properties:
- Ed25519: Fast, secure, 256-bit key strength
- JSON Canonicalization: Prevents signature bypass via object reordering
- Public Key Distribution: Via ~/.ssh/cluster-keys/
- Revocation Support: Remove public key to invalidate node

Key Storage:
- Private keys: ~/.ssh/cluster-keys/{node-id}.priv (chmod 600)
- Public keys: ~/.ssh/cluster-keys/{node-id}.pub (shared)

Usage:
    auth = MessageAuthenticator(node_id="macpro51")

    # Sign outgoing message
    payload = {"task_id": "abc", "type": "build"}
    signed = auth.sign_payload(payload)

    # Verify incoming message
    is_valid = auth.verify_payload(signed)
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


class MessageAuthenticator:
    """
    Cryptographic message authentication for GitMQ cluster.

    Uses Ed25519 signatures to ensure message authenticity and integrity.
    """

    def __init__(self, node_id: str):
        """
        Initialize authenticator for a specific node.

        Args:
            node_id: Unique identifier for this node (e.g., "macpro51")
        """
        self.node_id = node_id
        self.keys_dir = Path.home() / ".ssh" / "cluster-keys"
        self.keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Load or generate this node's keypair
        self.private_key, self.public_key = self._load_or_generate_keypair()

        # Load all trusted public keys
        self.public_keys = self._load_all_public_keys()

        logger.info(f"Message authenticator initialized for {node_id}")
        logger.info(f"Trusted nodes: {list(self.public_keys.keys())}")

    def _load_or_generate_keypair(self) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Load existing keypair or generate new one."""
        private_key_path = self.keys_dir / f"{self.node_id}.priv"
        public_key_path = self.keys_dir / f"{self.node_id}.pub"

        if private_key_path.exists() and public_key_path.exists():
            # Load existing keypair
            with open(private_key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )

            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())

            logger.info(f"Loaded existing keypair for {self.node_id}")
        else:
            # Generate new keypair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            # Save private key (restricted permissions)
            with open(private_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            private_key_path.chmod(0o600)

            # Save public key (shareable)
            with open(public_key_path, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

            logger.info(f"Generated new keypair for {self.node_id}")
            logger.info(f"Public key: {public_key_path}")
            logger.warning(f"Share {public_key_path} with other nodes to enable verification")

        return private_key, public_key

    def _load_all_public_keys(self) -> Dict[str, ed25519.Ed25519PublicKey]:
        """Load all public keys from trusted nodes."""
        public_keys = {}

        for pub_file in self.keys_dir.glob("*.pub"):
            node_id = pub_file.stem

            try:
                with open(pub_file, "rb") as f:
                    public_key = serialization.load_pem_public_key(f.read())
                    public_keys[node_id] = public_key
                    logger.debug(f"Loaded public key for {node_id}")
            except Exception as e:
                logger.warning(f"Failed to load public key for {node_id}: {e}")

        return public_keys

    def sign_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a payload with this node's private key.

        Args:
            payload: Dictionary to sign (will be modified in-place)

        Returns:
            Modified payload with '_signature' and '_signed_by' fields
        """
        # Create canonical JSON (sorted keys for consistent serialization)
        payload_canonical = json.dumps(payload, sort_keys=True).encode('utf-8')

        # Sign the canonical representation
        signature = self.private_key.sign(payload_canonical)

        # Add signature metadata to payload
        payload['_signature'] = base64.b64encode(signature).decode('ascii')
        payload['_signed_by'] = self.node_id

        return payload

    def verify_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Verify a signed payload from another node.

        Args:
            payload: Signed payload to verify

        Returns:
            True if signature is valid, False otherwise
        """
        # Extract signature metadata
        if '_signature' not in payload or '_signed_by' not in payload:
            logger.error("Payload missing signature metadata")
            return False

        signature_b64 = payload.pop('_signature')
        signed_by = payload.pop('_signed_by')

        try:
            # Decode signature
            signature = base64.b64decode(signature_b64)

            # Get public key for signing node
            public_key = self.public_keys.get(signed_by)
            if not public_key:
                logger.error(f"No public key found for node: {signed_by}")
                logger.warning(f"To trust {signed_by}, copy their .pub file to {self.keys_dir}")
                return False

            # Create canonical JSON (sorted keys)
            payload_canonical = json.dumps(payload, sort_keys=True).encode('utf-8')

            # Verify signature
            public_key.verify(signature, payload_canonical)

            logger.debug(f"Valid signature from {signed_by}")
            return True

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
        finally:
            # Restore signature metadata (don't modify caller's dict)
            payload['_signature'] = signature_b64
            payload['_signed_by'] = signed_by

    def export_public_key(self, output_path: Optional[Path] = None) -> Path:
        """
        Export this node's public key for sharing with other nodes.

        Args:
            output_path: Where to save the key (default: keys_dir/{node_id}.pub)

        Returns:
            Path to exported public key
        """
        if output_path is None:
            output_path = self.keys_dir / f"{self.node_id}.pub"

        with open(output_path, "wb") as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

        logger.info(f"Public key exported to {output_path}")
        return output_path

    def import_public_key(self, node_id: str, key_path: Path) -> bool:
        """
        Import a public key from another node.

        Args:
            node_id: ID of the node whose key is being imported
            key_path: Path to their .pub file

        Returns:
            True if imported successfully
        """
        try:
            # Copy to trusted keys directory
            dest_path = self.keys_dir / f"{node_id}.pub"

            with open(key_path, "rb") as src:
                public_key_pem = src.read()

            # Validate it's a valid public key
            serialization.load_pem_public_key(public_key_pem)

            # Save to trusted directory
            with open(dest_path, "wb") as dest:
                dest.write(public_key_pem)

            # Reload all public keys
            self.public_keys = self._load_all_public_keys()

            logger.info(f"Imported public key for {node_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to import public key for {node_id}: {e}")
            return False


def share_public_keys_across_cluster():
    """
    Helper script to share public keys across all cluster nodes.

    Run this after generating keys on each node to establish trust.

    Assumes cluster nodes can access ~/.ssh/cluster-keys/ via shared filesystem
    or manual file transfer.
    """
    print("Public Key Sharing Instructions")
    print("=" * 50)
    print()
    print("1. On each node, generate keys:")
    print("   auth = MessageAuthenticator(node_id='your-node')")
    print()
    print("2. Copy public keys to all nodes:")
    print(f"   Source: ~/.ssh/cluster-keys/*.pub")
    print(f"   Destination: ~/.ssh/cluster-keys/ (on each node)")
    print()
    print("3. Verify trust:")
    print("   auth.public_keys should show all nodes")
    print()
    print("Security: Private keys (.priv) must NEVER be shared")
    print("=" * 50)


if __name__ == "__main__":
    # Demo usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python auth.py <node-id>")
        sys.exit(1)

    node_id = sys.argv[1]

    # Initialize authenticator
    auth = MessageAuthenticator(node_id=node_id)

    # Demo: Sign a message
    message = {
        "task_id": "demo-123",
        "type": "health_check",
        "timestamp": "2025-11-16T10:00:00Z"
    }

    print(f"\nOriginal message:")
    print(json.dumps(message, indent=2))

    signed = auth.sign_payload(message.copy())
    print(f"\nSigned message:")
    print(json.dumps(signed, indent=2))

    # Demo: Verify the message
    is_valid = auth.verify_payload(signed)
    print(f"\nSignature valid: {is_valid}")

    # Show trusted nodes
    print(f"\nTrusted nodes: {list(auth.public_keys.keys())}")

    # Show sharing instructions
    print()
    share_public_keys_across_cluster()
