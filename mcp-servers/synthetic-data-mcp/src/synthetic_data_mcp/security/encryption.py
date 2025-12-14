"""
Advanced data encryption system for enterprise security.

Implements multiple encryption layers, key management, and cryptographic
operations for data protection at rest and in transit.
"""

import os
import json
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hmac
from cryptography.x509 import load_pem_x509_certificate
import nacl.secret
import nacl.utils
from loguru import logger
import boto3
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from google.cloud import kms
import hvac  # HashiCorp Vault


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    RSA_4096 = "rsa-4096"
    FERNET = "fernet"
    NACL_SECRETBOX = "nacl-secretbox"


class KeyManagementSystem(Enum):
    """Key management system providers."""
    LOCAL = "local"
    AWS_KMS = "aws-kms"
    AZURE_KEY_VAULT = "azure-key-vault"
    GCP_KMS = "gcp-kms"
    HASHICORP_VAULT = "hashicorp-vault"


@dataclass
class EncryptionKey:
    """Encryption key metadata."""
    id: str
    algorithm: EncryptionAlgorithm
    key_material: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    rotation_schedule: Optional[str]
    purpose: str  # data-encryption, key-encryption, signing
    metadata: Dict[str, Any]


@dataclass
class EncryptedData:
    """Encrypted data container."""
    ciphertext: bytes
    algorithm: EncryptionAlgorithm
    key_id: str
    nonce: Optional[bytes]
    tag: Optional[bytes]
    aad: Optional[bytes]  # Additional authenticated data
    timestamp: datetime
    metadata: Dict[str, Any]


class DataEncryptionKeyManager:
    """Manages data encryption keys (DEK)."""
    
    def __init__(self, kms_provider: KeyManagementSystem = KeyManagementSystem.LOCAL):
        self.kms_provider = kms_provider
        self.keys: Dict[str, EncryptionKey] = {}
        self.master_key = self._initialize_master_key()
        self._initialize_kms_client()
    
    def _initialize_master_key(self) -> bytes:
        """Initialize or load master encryption key (KEK)."""
        key_path = Path("/etc/synthetic-data/master.key")
        
        if key_path.exists():
            with open(key_path, "rb") as f:
                return f.read()
        else:
            # Generate new master key
            master_key = Fernet.generate_key()
            
            # Store securely (in production, use HSM or cloud KMS)
            os.makedirs(key_path.parent, exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(master_key)
            
            os.chmod(key_path, 0o600)  # Restrict permissions
            return master_key
    
    def _initialize_kms_client(self):
        """Initialize KMS client based on provider."""
        if self.kms_provider == KeyManagementSystem.AWS_KMS:
            self.kms_client = boto3.client('kms')
        elif self.kms_provider == KeyManagementSystem.AZURE_KEY_VAULT:
            credential = DefaultAzureCredential()
            self.kms_client = SecretClient(
                vault_url="https://your-vault.vault.azure.net/",
                credential=credential
            )
        elif self.kms_provider == KeyManagementSystem.GCP_KMS:
            self.kms_client = kms.KeyManagementServiceClient()
        elif self.kms_provider == KeyManagementSystem.HASHICORP_VAULT:
            self.kms_client = hvac.Client(url='http://localhost:8200')
    
    async def generate_data_key(
        self,
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        purpose: str = "data-encryption"
    ) -> EncryptionKey:
        """Generate a new data encryption key."""
        key_id = secrets.token_urlsafe(16)
        
        # Generate key material based on algorithm
        if algorithm in [EncryptionAlgorithm.AES_256_GCM, EncryptionAlgorithm.AES_256_CBC]:
            key_material = os.urandom(32)  # 256 bits
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            key_material = os.urandom(32)
        elif algorithm == EncryptionAlgorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            key_material = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        elif algorithm == EncryptionAlgorithm.FERNET:
            key_material = Fernet.generate_key()
        elif algorithm == EncryptionAlgorithm.NACL_SECRETBOX:
            key_material = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Encrypt DEK with KEK (key wrapping)
        wrapped_key = await self._wrap_key(key_material)
        
        # Create key metadata
        key = EncryptionKey(
            id=key_id,
            algorithm=algorithm,
            key_material=wrapped_key,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=90),  # 90-day rotation
            rotation_schedule="90d",
            purpose=purpose,
            metadata={"wrapped": True}
        )
        
        self.keys[key_id] = key
        logger.info(f"Generated new DEK: {key_id} for {purpose}")
        
        return key
    
    async def _wrap_key(self, key_material: bytes) -> bytes:
        """Wrap (encrypt) a data key with the master key."""
        if self.kms_provider == KeyManagementSystem.LOCAL:
            f = Fernet(self.master_key)
            return f.encrypt(key_material)
        elif self.kms_provider == KeyManagementSystem.AWS_KMS:
            response = self.kms_client.encrypt(
                KeyId='alias/synthetic-data-kek',
                Plaintext=key_material
            )
            return response['CiphertextBlob']
        # Additional KMS providers implementation
        return key_material
    
    async def _unwrap_key(self, wrapped_key: bytes) -> bytes:
        """Unwrap (decrypt) a data key with the master key."""
        if self.kms_provider == KeyManagementSystem.LOCAL:
            f = Fernet(self.master_key)
            return f.decrypt(wrapped_key)
        elif self.kms_provider == KeyManagementSystem.AWS_KMS:
            response = self.kms_client.decrypt(CiphertextBlob=wrapped_key)
            return response['Plaintext']
        # Additional KMS providers implementation
        return wrapped_key
    
    async def rotate_key(self, key_id: str) -> EncryptionKey:
        """Rotate an encryption key."""
        old_key = self.keys.get(key_id)
        if not old_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Generate new key with same parameters
        new_key = await self.generate_data_key(
            algorithm=old_key.algorithm,
            purpose=old_key.purpose
        )
        
        # Mark old key as rotated
        old_key.metadata["rotated"] = True
        old_key.metadata["rotated_to"] = new_key.id
        old_key.metadata["rotation_date"] = datetime.utcnow().isoformat()
        
        logger.info(f"Rotated key {key_id} to {new_key.id}")
        
        return new_key


class AdvancedEncryptionService:
    """Advanced encryption service with multiple algorithms."""
    
    def __init__(self, key_manager: DataEncryptionKeyManager):
        self.key_manager = key_manager
        self.backend = default_backend()
    
    async def encrypt(
        self,
        data: Union[str, bytes, Dict],
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """Encrypt data with specified algorithm."""
        # Convert data to bytes
        if isinstance(data, str):
            plaintext = data.encode('utf-8')
        elif isinstance(data, dict):
            plaintext = json.dumps(data).encode('utf-8')
        else:
            plaintext = data
        
        # Get or generate encryption key
        if key_id:
            key = self.key_manager.keys.get(key_id)
            if not key:
                raise ValueError(f"Key {key_id} not found")
        else:
            key = await self.key_manager.generate_data_key(algorithm)
            key_id = key.id
        
        # Unwrap the key
        key_material = await self.key_manager._unwrap_key(key.key_material)
        
        # Perform encryption based on algorithm
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            encrypted = await self._encrypt_aes_gcm(plaintext, key_material)
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            encrypted = await self._encrypt_aes_cbc(plaintext, key_material)
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            encrypted = await self._encrypt_chacha20(plaintext, key_material)
        elif algorithm == EncryptionAlgorithm.FERNET:
            encrypted = await self._encrypt_fernet(plaintext, key_material)
        elif algorithm == EncryptionAlgorithm.NACL_SECRETBOX:
            encrypted = await self._encrypt_nacl(plaintext, key_material)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        encrypted["key_id"] = key_id
        encrypted["algorithm"] = algorithm
        encrypted["timestamp"] = datetime.utcnow()
        
        return EncryptedData(**encrypted)
    
    async def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data."""
        # Get encryption key
        key = self.key_manager.keys.get(encrypted_data.key_id)
        if not key:
            raise ValueError(f"Key {encrypted_data.key_id} not found")
        
        # Unwrap the key
        key_material = await self.key_manager._unwrap_key(key.key_material)
        
        # Perform decryption based on algorithm
        if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM:
            plaintext = await self._decrypt_aes_gcm(encrypted_data, key_material)
        elif encrypted_data.algorithm == EncryptionAlgorithm.AES_256_CBC:
            plaintext = await self._decrypt_aes_cbc(encrypted_data, key_material)
        elif encrypted_data.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            plaintext = await self._decrypt_chacha20(encrypted_data, key_material)
        elif encrypted_data.algorithm == EncryptionAlgorithm.FERNET:
            plaintext = await self._decrypt_fernet(encrypted_data, key_material)
        elif encrypted_data.algorithm == EncryptionAlgorithm.NACL_SECRETBOX:
            plaintext = await self._decrypt_nacl(encrypted_data, key_material)
        else:
            raise ValueError(f"Unsupported algorithm: {encrypted_data.algorithm}")
        
        return plaintext
    
    async def _encrypt_aes_gcm(self, plaintext: bytes, key: bytes) -> Dict[str, Any]:
        """Encrypt using AES-256-GCM."""
        # Generate nonce
        nonce = os.urandom(12)  # 96 bits for GCM
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()
        
        # Add associated data for authentication
        aad = b"synthetic-data-platform"
        encryptor.authenticate_additional_data(aad)
        
        # Encrypt
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        return {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "tag": encryptor.tag,
            "aad": aad,
            "metadata": {"mode": "GCM", "key_size": 256}
        }
    
    async def _decrypt_aes_gcm(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt using AES-256-GCM."""
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(encrypted.nonce, encrypted.tag),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()
        
        # Authenticate additional data
        if encrypted.aad:
            decryptor.authenticate_additional_data(encrypted.aad)
        
        # Decrypt
        plaintext = decryptor.update(encrypted.ciphertext) + decryptor.finalize()
        
        return plaintext
    
    async def _encrypt_aes_cbc(self, plaintext: bytes, key: bytes) -> Dict[str, Any]:
        """Encrypt using AES-256-CBC with HMAC."""
        # Pad plaintext to block size
        from cryptography.hazmat.primitives import padding as crypto_padding
        padder = crypto_padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # Generate IV
        iv = os.urandom(16)  # 128 bits
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Generate HMAC for authentication
        h = hmac.HMAC(key, hashes.SHA256(), backend=self.backend)
        h.update(ciphertext)
        tag = h.finalize()
        
        return {
            "ciphertext": ciphertext,
            "nonce": iv,
            "tag": tag,
            "metadata": {"mode": "CBC", "padding": "PKCS7"}
        }
    
    async def _decrypt_aes_cbc(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt using AES-256-CBC."""
        # Verify HMAC
        h = hmac.HMAC(key, hashes.SHA256(), backend=self.backend)
        h.update(encrypted.ciphertext)
        h.verify(encrypted.tag)
        
        # Decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(encrypted.nonce),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(encrypted.ciphertext) + decryptor.finalize()
        
        # Remove padding
        from cryptography.hazmat.primitives import padding as crypto_padding
        unpadder = crypto_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        return plaintext
    
    async def _encrypt_chacha20(self, plaintext: bytes, key: bytes) -> Dict[str, Any]:
        """Encrypt using ChaCha20-Poly1305."""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        chacha = ChaCha20Poly1305(key)
        nonce = os.urandom(12)
        aad = b"synthetic-data"
        
        ciphertext = chacha.encrypt(nonce, plaintext, aad)
        
        return {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "aad": aad,
            "metadata": {"algorithm": "ChaCha20-Poly1305"}
        }
    
    async def _decrypt_chacha20(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt using ChaCha20-Poly1305."""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        
        chacha = ChaCha20Poly1305(key)
        plaintext = chacha.decrypt(encrypted.nonce, encrypted.ciphertext, encrypted.aad)
        
        return plaintext
    
    async def _encrypt_fernet(self, plaintext: bytes, key: bytes) -> Dict[str, Any]:
        """Encrypt using Fernet (symmetric encryption)."""
        f = Fernet(key)
        ciphertext = f.encrypt(plaintext)
        
        return {
            "ciphertext": ciphertext,
            "metadata": {"algorithm": "Fernet"}
        }
    
    async def _decrypt_fernet(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt using Fernet."""
        f = Fernet(key)
        plaintext = f.decrypt(encrypted.ciphertext)
        
        return plaintext
    
    async def _encrypt_nacl(self, plaintext: bytes, key: bytes) -> Dict[str, Any]:
        """Encrypt using NaCl SecretBox."""
        box = nacl.secret.SecretBox(key)
        encrypted = box.encrypt(plaintext)
        
        # NaCl combines nonce and ciphertext
        nonce = encrypted[:nacl.secret.SecretBox.NONCE_SIZE]
        ciphertext = encrypted[nacl.secret.SecretBox.NONCE_SIZE:]
        
        return {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "metadata": {"algorithm": "NaCl-SecretBox"}
        }
    
    async def _decrypt_nacl(self, encrypted: EncryptedData, key: bytes) -> bytes:
        """Decrypt using NaCl SecretBox."""
        box = nacl.secret.SecretBox(key)
        
        # Reconstruct the encrypted message
        encrypted_message = encrypted.nonce + encrypted.ciphertext
        plaintext = box.decrypt(encrypted_message)
        
        return plaintext


class FieldLevelEncryption:
    """Field-level encryption for fine-grained data protection."""
    
    def __init__(self, encryption_service: AdvancedEncryptionService):
        self.encryption_service = encryption_service
        self.field_keys: Dict[str, str] = {}  # Field name to key ID mapping
    
    async def encrypt_fields(
        self,
        data: Dict[str, Any],
        sensitive_fields: List[str],
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM
    ) -> Dict[str, Any]:
        """Encrypt specific fields in a dictionary."""
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in data:
                # Get or create field-specific key
                if field not in self.field_keys:
                    key = await self.encryption_service.key_manager.generate_data_key(
                        algorithm=algorithm,
                        purpose=f"field-{field}"
                    )
                    self.field_keys[field] = key.id
                
                # Encrypt field value
                encrypted = await self.encryption_service.encrypt(
                    data[field],
                    algorithm=algorithm,
                    key_id=self.field_keys[field]
                )
                
                # Store encrypted value with metadata
                encrypted_data[field] = {
                    "_encrypted": True,
                    "ciphertext": base64.b64encode(encrypted.ciphertext).decode(),
                    "key_id": encrypted.key_id,
                    "algorithm": encrypted.algorithm.value,
                    "nonce": base64.b64encode(encrypted.nonce).decode() if encrypted.nonce else None,
                    "tag": base64.b64encode(encrypted.tag).decode() if encrypted.tag else None
                }
        
        return encrypted_data
    
    async def decrypt_fields(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt encrypted fields in a dictionary."""
        decrypted_data = {}
        
        for field, value in encrypted_data.items():
            if isinstance(value, dict) and value.get("_encrypted"):
                # Reconstruct EncryptedData object
                encrypted = EncryptedData(
                    ciphertext=base64.b64decode(value["ciphertext"]),
                    algorithm=EncryptionAlgorithm(value["algorithm"]),
                    key_id=value["key_id"],
                    nonce=base64.b64decode(value["nonce"]) if value.get("nonce") else None,
                    tag=base64.b64decode(value["tag"]) if value.get("tag") else None,
                    aad=None,
                    timestamp=datetime.utcnow(),
                    metadata={}
                )
                
                # Decrypt
                plaintext = await self.encryption_service.decrypt(encrypted)
                
                # Try to parse as JSON
                try:
                    decrypted_data[field] = json.loads(plaintext.decode())
                except:
                    decrypted_data[field] = plaintext.decode()
            else:
                decrypted_data[field] = value
        
        return decrypted_data


class TransparentDataEncryption:
    """Transparent data encryption for databases."""
    
    def __init__(self, encryption_service: AdvancedEncryptionService):
        self.encryption_service = encryption_service
        self.table_keys: Dict[str, str] = {}  # Table to key mapping
    
    async def encrypt_row(
        self,
        table_name: str,
        row_data: Dict[str, Any],
        encrypt_columns: List[str]
    ) -> Dict[str, Any]:
        """Encrypt specific columns in a database row."""
        # Get or create table encryption key
        if table_name not in self.table_keys:
            key = await self.encryption_service.key_manager.generate_data_key(
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                purpose=f"table-{table_name}"
            )
            self.table_keys[table_name] = key.id
        
        encrypted_row = row_data.copy()
        
        for column in encrypt_columns:
            if column in row_data:
                encrypted = await self.encryption_service.encrypt(
                    row_data[column],
                    key_id=self.table_keys[table_name]
                )
                
                # Store as binary in database
                encrypted_row[column] = encrypted.ciphertext
                encrypted_row[f"{column}_metadata"] = {
                    "encrypted": True,
                    "key_id": encrypted.key_id,
                    "algorithm": encrypted.algorithm.value,
                    "nonce": base64.b64encode(encrypted.nonce).decode() if encrypted.nonce else None
                }
        
        return encrypted_row
    
    async def decrypt_row(
        self,
        table_name: str,
        encrypted_row: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decrypt encrypted columns in a database row."""
        decrypted_row = {}
        
        for column, value in encrypted_row.items():
            if column.endswith("_metadata"):
                continue
            
            metadata_column = f"{column}_metadata"
            if metadata_column in encrypted_row and encrypted_row[metadata_column].get("encrypted"):
                metadata = encrypted_row[metadata_column]
                
                # Reconstruct EncryptedData
                encrypted = EncryptedData(
                    ciphertext=value,
                    algorithm=EncryptionAlgorithm(metadata["algorithm"]),
                    key_id=metadata["key_id"],
                    nonce=base64.b64decode(metadata["nonce"]) if metadata.get("nonce") else None,
                    tag=None,
                    aad=None,
                    timestamp=datetime.utcnow(),
                    metadata={}
                )
                
                # Decrypt
                plaintext = await self.encryption_service.decrypt(encrypted)
                
                # Parse value
                try:
                    decrypted_row[column] = json.loads(plaintext.decode())
                except:
                    decrypted_row[column] = plaintext.decode()
            else:
                decrypted_row[column] = value
        
        return decrypted_row


# Global encryption service instance
key_manager = DataEncryptionKeyManager(KeyManagementSystem.LOCAL)
encryption_service = AdvancedEncryptionService(key_manager)
field_encryption = FieldLevelEncryption(encryption_service)
tde = TransparentDataEncryption(encryption_service)