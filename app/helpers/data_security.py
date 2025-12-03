"""
Data masking and encryption helper for AI inputs.
Protects sensitive information before sending to AI models.
"""

import re
import logging
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class MaskedData:
    """Container for masked data and mapping."""
    masked_text: str
    token_map: Dict[str, str]
    patterns_found: List[str]


class DataSecurityHelper:
    """Helper class for data masking and encryption."""
    
    # Regex patterns for sensitive data
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',
        'url': r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)',
        'date_of_birth': r'\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b',
        'passport': r'\b[A-Z]{1,2}[0-9]{6,9}\b',
        'address': r'\b\d+\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir)\b',
    }
    
    def __init__(self):
        """Initialize data security helper."""
        self._cipher = self._initialize_cipher()
        self.masking_enabled = settings.DATA_MASKING_ENABLED
        self.encryption_enabled = settings.DATA_ENCRYPTION_ENABLED
    
    def _initialize_cipher(self) -> Fernet:
        """Initialize Fernet cipher with key from settings."""
        try:
            # Use encryption key from settings or generate one
            key = settings.ENCRYPTION_KEY.encode() if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY else Fernet.generate_key()
            
            # Derive a proper Fernet key if needed
            if len(key) != 44:  # Fernet key must be 32 bytes base64-encoded (44 chars)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'izh_ai_salt_2025',  # In production, use a secure random salt
                    iterations=100000,
                )
                derived_key = base64.urlsafe_b64encode(kdf.derive(key))
                return Fernet(derived_key)
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize cipher: {e}")
            # Generate a temporary key for this session
            return Fernet(Fernet.generate_key())
    
    def mask_sensitive_data(
        self, 
        text: str,
        patterns: Optional[List[str]] = None,
        preserve_format: bool = True
    ) -> MaskedData:
        """
        Mask sensitive data in text.
        
        Args:
            text: Text to mask
            patterns: List of pattern names to mask (defaults to all)
            preserve_format: Whether to preserve the format of masked data
            
        Returns:
            MaskedData object with masked text and token mapping
        """
        if not self.masking_enabled:
            return MaskedData(
                masked_text=text,
                token_map={},
                patterns_found=[]
            )
        
        masked_text = text
        token_map = {}
        patterns_found = []
        
        # Use all patterns if none specified
        patterns_to_use = patterns or list(self.PATTERNS.keys())
        
        for pattern_name in patterns_to_use:
            if pattern_name not in self.PATTERNS:
                continue
                
            pattern = self.PATTERNS[pattern_name]
            matches = re.finditer(pattern, masked_text)
            
            for match in matches:
                original_value = match.group(0)
                
                # Generate a unique token
                token = self._generate_token(original_value, pattern_name)
                
                # Create masked replacement
                if preserve_format:
                    replacement = self._create_format_preserving_mask(original_value, pattern_name)
                else:
                    replacement = f"[{pattern_name.upper()}_{token}]"
                
                # Store mapping
                token_map[replacement] = original_value
                patterns_found.append(pattern_name)
                
                # Replace in text
                masked_text = masked_text.replace(original_value, replacement, 1)
        
        logger.info(f"Masked {len(token_map)} sensitive data items")
        
        return MaskedData(
            masked_text=masked_text,
            token_map=token_map,
            patterns_found=list(set(patterns_found))
        )
    
    def unmask_data(self, text: str, token_map: Dict[str, str]) -> str:
        """
        Restore original data from masked text.
        
        Args:
            text: Masked text
            token_map: Token to original value mapping
            
        Returns:
            Unmasked text
        """
        unmasked_text = text
        
        for token, original_value in token_map.items():
            unmasked_text = unmasked_text.replace(token, original_value)
        
        return unmasked_text
    
    def encrypt_text(self, text: str) -> str:
        """
        Encrypt text using Fernet encryption.
        
        Args:
            text: Text to encrypt
            
        Returns:
            Encrypted text (base64 encoded)
        """
        if not self.encryption_enabled:
            return text
            
        try:
            encrypted = self._cipher.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return text
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted text.
        
        Args:
            encrypted_text: Encrypted text (base64 encoded)
            
        Returns:
            Decrypted text
        """
        if not self.encryption_enabled:
            return encrypted_text
            
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self._cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_text
    
    def hash_pii(self, text: str, algorithm: str = 'sha256') -> str:
        """
        Create a one-way hash of PII for logging/analytics.
        
        Args:
            text: Text to hash
            algorithm: Hash algorithm (sha256, sha512, md5)
            
        Returns:
            Hexadecimal hash string
        """
        hash_func = getattr(hashlib, algorithm, hashlib.sha256)
        return hash_func(text.encode()).hexdigest()
    
    def _generate_token(self, value: str, pattern_name: str) -> str:
        """Generate a unique token for a masked value."""
        # Use first 8 chars of SHA256 hash for uniqueness
        hash_val = hashlib.sha256(f"{value}{pattern_name}".encode()).hexdigest()[:8]
        return hash_val.upper()
    
    def _create_format_preserving_mask(self, value: str, pattern_name: str) -> str:
        """
        Create a format-preserving mask for the value.
        
        Args:
            value: Original value
            pattern_name: Type of pattern
            
        Returns:
            Masked value preserving format
        """
        if pattern_name == 'email':
            # Mask email: john.doe@example.com -> j***@e***.com
            parts = value.split('@')
            if len(parts) == 2:
                local = parts[0][0] + '***' if len(parts[0]) > 1 else '***'
                domain_parts = parts[1].split('.')
                domain = domain_parts[0][0] + '***' if len(domain_parts[0]) > 1 else '***'
                tld = '.' + '.'.join(domain_parts[1:]) if len(domain_parts) > 1 else ''
                return f"{local}@{domain}{tld}"
        
        elif pattern_name == 'phone':
            # Mask phone: (123) 456-7890 -> (***) ***-7890
            return re.sub(r'\d', '*', value[:-4]) + value[-4:]
        
        elif pattern_name == 'ssn':
            # Mask SSN: 123-45-6789 -> ***-**-6789
            return '***-**-' + value[-4:]
        
        elif pattern_name == 'credit_card':
            # Mask credit card: 1234 5678 9012 3456 -> **** **** **** 3456
            clean = re.sub(r'[-\s]', '', value)
            masked = '*' * (len(clean) - 4) + clean[-4:]
            # Restore original formatting
            if '-' in value:
                return '-'.join([masked[i:i+4] for i in range(0, len(masked), 4)])
            elif ' ' in value:
                return ' '.join([masked[i:i+4] for i in range(0, len(masked), 4)])
            return masked
        
        elif pattern_name == 'ip_address':
            # Mask IP: 192.168.1.1 -> ***.***.***.1
            parts = value.split('.')
            return '.'.join(['***'] * (len(parts) - 1) + [parts[-1]])
        
        else:
            # Generic masking - show first and last char
            if len(value) <= 2:
                return '*' * len(value)
            return value[0] + '*' * (len(value) - 2) + value[-1]
    
    def redact_for_logging(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive fields from data for safe logging.
        
        Args:
            data: Dictionary to redact
            
        Returns:
            Redacted dictionary
        """
        sensitive_keys = {
            'password', 'api_key', 'secret', 'token', 'auth',
            'credit_card', 'ssn', 'passport', 'private_key'
        }
        
        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive terms
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                redacted[key] = '[REDACTED]'
            elif isinstance(value, dict):
                redacted[key] = self.redact_for_logging(value)
            elif isinstance(value, str):
                # Quick check for patterns in values
                masked_data = self.mask_sensitive_data(value, preserve_format=False)
                if masked_data.patterns_found:
                    redacted[key] = masked_data.masked_text
                else:
                    redacted[key] = value
            else:
                redacted[key] = value
        
        return redacted
    
    def sanitize_for_ai(
        self, 
        text: str,
        mask_pii: bool = True,
        encrypt_result: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitize text before sending to AI model.
        
        Args:
            text: Text to sanitize
            mask_pii: Whether to mask PII
            encrypt_result: Whether to encrypt the result
            
        Returns:
            Tuple of (sanitized_text, metadata)
        """
        metadata = {
            'original_length': len(text),
            'masked': False,
            'encrypted': False,
            'patterns_found': []
        }
        
        sanitized_text = text
        
        # Mask PII if enabled
        if mask_pii and self.masking_enabled:
            masked_data = self.mask_sensitive_data(text)
            sanitized_text = masked_data.masked_text
            metadata['masked'] = len(masked_data.token_map) > 0
            metadata['patterns_found'] = masked_data.patterns_found
            metadata['token_map'] = masked_data.token_map
        
        # Encrypt if requested
        if encrypt_result and self.encryption_enabled:
            sanitized_text = self.encrypt_text(sanitized_text)
            metadata['encrypted'] = True
        
        metadata['sanitized_length'] = len(sanitized_text)
        
        return sanitized_text, metadata


# Global instance
data_security_helper = DataSecurityHelper()
