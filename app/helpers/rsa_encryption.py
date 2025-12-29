import logging
import json
import base64
import os
from typing import Optional, Dict, Any, Union
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RSAEncryptionHelper:
    """Helper class for hybrid encryption (AES-256 + RSA) of API responses.
    
    Uses AES-256 for data encryption and RSA for encrypting the AES key.
    This allows encryption of data of any size efficiently.
    """
    
    def __init__(
        self,
        private_key_path: Optional[str] = None,
        public_key_path: Optional[str] = None,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        public_key: Optional[rsa.RSAPublicKey] = None
    ):
        """
        Initialize RSA encryption helper.
        
        Args:
            private_key_path: Path to private key PEM file (optional)
            public_key_path: Path to public key PEM file (optional)
            private_key: RSA private key object (optional)
            public_key: RSA public key object (optional)
            
        Note: If no keys are provided, new keys will be generated.
        """
        self.backend = default_backend()
        self.private_key = private_key
        self.public_key = public_key
        
        # Try to load keys from paths if provided
        if private_key_path:
            self.private_key = self._load_private_key(private_key_path)
        
        if public_key_path:
            self.public_key = self._load_public_key(public_key_path)
        
        # If private key is loaded, derive public key from it
        if self.private_key and not self.public_key:
            self.public_key = self.private_key.public_key()
        
        # If public key is loaded, check if we need to load private key
        if self.public_key and not self.private_key:
            if private_key_path and Path(private_key_path).exists():
                self.private_key = self._load_private_key(private_key_path)
        
        # Generate new keys if none are provided
        if not self.private_key and not self.public_key:
            logger.warning("No RSA keys provided. Generating new key pair.")
            self.private_key, self.public_key = self.generate_key_pair()
            logger.info("New RSA key pair generated. Save these keys for future use.")
    
    def generate_key_pair(
        self,
        key_size: int = 2048
    ) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """
        Generate a new RSA key pair.
        
        Args:
            key_size: Key size in bits (default: 2048, recommended: 2048 or 4096)
            
        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=self.backend
        )
        public_key = private_key.public_key()
        
        logger.info(f"Generated RSA key pair with key size {key_size} bits")
        return private_key, public_key
    
    def _load_private_key(self, key_path: str) -> Optional[rsa.RSAPrivateKey]:
        """Load private key from PEM file."""
        try:
            with open(key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=self.backend
                )
            logger.info(f"Loaded private key from {key_path}")
            return private_key
        except Exception as e:
            logger.error(f"Failed to load private key from {key_path}: {e}")
            return None
    
    def _load_public_key(self, key_path: str) -> Optional[rsa.RSAPublicKey]:
        """Load public key from PEM file."""
        try:
            with open(key_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=self.backend
                )
            logger.info(f"Loaded public key from {key_path}")
            return public_key
        except Exception as e:
            logger.error(f"Failed to load public key from {key_path}: {e}")
            return None
    
    def save_private_key(
        self,
        key_path: str,
        private_key: Optional[rsa.RSAPrivateKey] = None
    ) -> bool:
        """
        Save private key to PEM file.
        
        Args:
            key_path: Path to save the key
            private_key: Private key to save (uses self.private_key if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key_to_save = private_key or self.private_key
            if not key_to_save:
                logger.error("No private key available to save")
                return False
            
            pem = key_to_save.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            with open(key_path, 'wb') as f:
                f.write(pem)
            
            logger.info(f"Saved private key to {key_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save private key to {key_path}: {e}")
            return False
    
    def save_public_key(
        self,
        key_path: str,
        public_key: Optional[rsa.RSAPublicKey] = None
    ) -> bool:
        """
        Save public key to PEM file.
        
        Args:
            key_path: Path to save the key
            public_key: Public key to save (uses self.public_key if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key_to_save = public_key or self.public_key
            if not key_to_save:
                logger.error("No public key available to save")
                return False
            
            pem = key_to_save.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            with open(key_path, 'wb') as f:
                f.write(pem)
            
            logger.info(f"Saved public key to {key_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save public key to {key_path}: {e}")
            return False
    
    def get_public_key_pem(self) -> Optional[str]:
        """
        Get public key as PEM string.
        
        Returns:
            Public key as PEM string, or None if not available
        """
        if not self.public_key:
            logger.error("No public key available")
            return None
        
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')
    
    def encrypt(
        self,
        data: Union[str, bytes, Dict[str, Any]],
        public_key: Optional[rsa.RSAPublicKey] = None
    ) -> str:
        """
        Encrypt data using hybrid encryption (AES-256 + RSA).
        
        The data is encrypted with AES-256, and the AES key is encrypted with RSA.
        This allows encryption of data of any size.
        
        Args:
            data: Data to encrypt (string, bytes, or dict)
            public_key: Public key to use (uses self.public_key if not provided)
            
        Returns:
            JSON string containing encrypted_key (RSA-encrypted AES key), 
            encrypted_data (AES-encrypted data), and iv (initialization vector),
            all base64-encoded
        """
        if not public_key and not self.public_key:
            raise ValueError("No public key available for encryption")
        
        rsa_key_to_use = public_key or self.public_key
        
        # Convert data to bytes
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode('utf-8')
        elif isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Generate a random AES-256 key (32 bytes = 256 bits)
        aes_key = os.urandom(32)
        
        # Generate a random IV (16 bytes for AES)
        iv = os.urandom(16)
        
        # Encrypt data with AES-256 in CBC mode
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CBC(iv),
            backend=self.backend
        )
        encryptor = cipher.encryptor()
        
        # Pad data to be multiple of block size (16 bytes for AES)
        pad_length = 16 - (len(data_bytes) % 16)
        padded_data = data_bytes + bytes([pad_length] * pad_length)
        
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encrypt AES key with RSA
        encrypted_aes_key = rsa_key_to_use.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Create result dictionary
        result = {
            "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8')
        }
        
        # Return as JSON string
        return json.dumps(result)
    
    def decrypt(
        self,
        encrypted_data: str,
        private_key: Optional[rsa.RSAPrivateKey] = None
    ) -> bytes:
        """
        Decrypt data using hybrid decryption (AES-256 + RSA).
        
        First decrypts the AES key with RSA, then decrypts the data with AES-256.
        
        Args:
            encrypted_data: JSON string containing encrypted_key, encrypted_data, and iv
            private_key: Private key to use (uses self.private_key if not provided)
            
        Returns:
            Decrypted data as bytes
        """
        if not private_key and not self.private_key:
            raise ValueError("No private key available for decryption")
        
        rsa_key_to_use = private_key or self.private_key
        
        try:
            # Parse the encrypted data JSON
            encrypted_dict = json.loads(encrypted_data)
            
            encrypted_key_b64 = encrypted_dict.get("encrypted_key")
            encrypted_data_b64 = encrypted_dict.get("encrypted_data")
            iv_b64 = encrypted_dict.get("iv")
            
            if not all([encrypted_key_b64, encrypted_data_b64, iv_b64]):
                raise ValueError("Missing required fields in encrypted data")
            
            # Decode base64 values
            encrypted_aes_key = base64.b64decode(encrypted_key_b64)
            encrypted_data_bytes = base64.b64decode(encrypted_data_b64)
            iv = base64.b64decode(iv_b64)
            
            # Decrypt AES key with RSA
            aes_key = rsa_key_to_use.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt data with AES-256
            cipher = Cipher(
                algorithms.AES(aes_key),
                modes.CBC(iv),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            
            padded_decrypted = decryptor.update(encrypted_data_bytes) + decryptor.finalize()
            
            # Remove padding
            pad_length = padded_decrypted[-1]
            decrypted = padded_decrypted[:-pad_length]
            
            return decrypted
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse encrypted data JSON: {e}")
            raise ValueError(f"Invalid encrypted data format: {e}")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def decrypt_json(
        self,
        encrypted_data: str,
        private_key: Optional[rsa.RSAPrivateKey] = None
    ) -> Dict[str, Any]:
        """
        Decrypt and parse JSON data.
        
        Args:
            encrypted_data: JSON string containing encrypted_key, encrypted_data, and iv
            private_key: Private key to use (uses self.private_key if not provided)
            
        Returns:
            Decrypted JSON data as dictionary
        """
        decrypted_bytes = self.decrypt(encrypted_data, private_key)
        return json.loads(decrypted_bytes.decode('utf-8'))
    
    def decrypt_string(
        self,
        encrypted_data: str,
        private_key: Optional[rsa.RSAPrivateKey] = None
    ) -> str:
        """
        Decrypt data to string.
        
        Args:
            encrypted_data: JSON string containing encrypted_key, encrypted_data, and iv
            private_key: Private key to use (uses self.private_key if not provided)
            
        Returns:
            Decrypted data as string
        """
        decrypted_bytes = self.decrypt(encrypted_data, private_key)
        return decrypted_bytes.decode('utf-8')
    
    def encrypt_api_response(
        self,
        response_data: Dict[str, Any],
        public_key: Optional[rsa.RSAPublicKey] = None
    ) -> Dict[str, Any]:
        """
        Encrypt API response data using hybrid encryption (AES-256 + RSA).
        
        Args:
            response_data: API response dictionary to encrypt
            public_key: Public key to use (uses self.public_key if not provided)
            
        Returns:
            Dictionary with encrypted data
        """
        try:
            encrypted = self.encrypt(response_data, public_key)
            return {
                "encrypted": True,
                "data": encrypted,
                "algorithm": "AES256-RSA-OAEP-SHA256"
            }
        except ValueError as e:
            logger.error(f"Failed to encrypt API response: {e}")
            return {
                "encrypted": False,
                "error": str(e),
                "data": response_data  # Return unencrypted as fallback
            }
    
    def decrypt_api_response(
        self,
        encrypted_response: Dict[str, Any],
        private_key: Optional[rsa.RSAPrivateKey] = None
    ) -> Dict[str, Any]:
        """
        Decrypt API response data.
        
        Args:
            encrypted_response: Encrypted response dictionary
            private_key: Private key to use (uses self.private_key if not provided)
            
        Returns:
            Decrypted API response dictionary
        """
        if not encrypted_response.get("encrypted"):
            return encrypted_response.get("data", encrypted_response)
        
        try:
            encrypted_data = encrypted_response.get("data")
            if not encrypted_data:
                raise ValueError("No encrypted data found in response")
            
            return self.decrypt_json(encrypted_data, private_key)
        except Exception as e:
            logger.error(f"Failed to decrypt API response: {e}")
            raise ValueError(f"Failed to decrypt API response: {e}")


# Global instance - can be initialized with keys from settings or environment
def _initialize_rsa_helper() -> RSAEncryptionHelper:
    """Initialize RSA helper from settings or environment."""
    private_key_path = getattr(settings, 'RSA_PRIVATE_KEY_PATH', None)
    public_key_path = getattr(settings, 'RSA_PUBLIC_KEY_PATH', None)
    
    return RSAEncryptionHelper(
        private_key_path=private_key_path,
        public_key_path=public_key_path
    )


# Global RSA encryption helper instance
rsa_encryption_helper = _initialize_rsa_helper()
