"""
Tests for data security helper.
"""
import pytest
from app.helpers.data_security import DataSecurityHelper, MaskedData


@pytest.fixture
def security_helper():
    """Create a DataSecurityHelper instance for testing."""
    return DataSecurityHelper()


class TestDataMasking:
    """Test data masking functionality."""
    
    def test_mask_email(self, security_helper):
        """Test email masking."""
        text = "Contact me at john.doe@example.com for more info"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "@" in result.masked_text
        assert "john.doe@example.com" not in result.masked_text
        assert "email" in result.patterns_found
        assert len(result.token_map) == 1
    
    def test_mask_phone(self, security_helper):
        """Test phone number masking."""
        text = "Call me at (555) 123-4567"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "4567" in result.masked_text  # Last 4 digits preserved
        assert "(555) 123" not in result.masked_text
        assert "phone" in result.patterns_found
    
    def test_mask_ssn(self, security_helper):
        """Test SSN masking."""
        text = "My SSN is 123-45-6789"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "6789" in result.masked_text  # Last 4 digits preserved
        assert "123-45" not in result.masked_text
        assert "ssn" in result.patterns_found
    
    def test_mask_credit_card(self, security_helper):
        """Test credit card masking."""
        text = "Card: 1234 5678 9012 3456"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "3456" in result.masked_text  # Last 4 digits preserved
        assert "1234 5678" not in result.masked_text
        assert "credit_card" in result.patterns_found
    
    def test_mask_ip_address(self, security_helper):
        """Test IP address masking."""
        text = "Server IP: 192.168.1.100"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "100" in result.masked_text  # Last octet preserved
        assert "192.168.1" not in result.masked_text
        assert "ip_address" in result.patterns_found
    
    def test_mask_multiple_patterns(self, security_helper):
        """Test masking multiple patterns in same text."""
        text = "Contact john@example.com or call 555-123-4567"
        result = security_helper.mask_sensitive_data(text)
        
        assert result.masked_text != text
        assert "john@example.com" not in result.masked_text
        assert "555-123-4567" not in result.masked_text
        assert len(result.patterns_found) >= 2
        assert len(result.token_map) >= 2
    
    def test_unmask_data(self, security_helper):
        """Test unmasking data."""
        original_text = "Email me at john.doe@example.com"
        masked_result = security_helper.mask_sensitive_data(original_text)
        
        unmasked = security_helper.unmask_data(
            masked_result.masked_text,
            masked_result.token_map
        )
        
        assert "john.doe@example.com" in unmasked
    
    def test_no_masking_when_disabled(self):
        """Test that masking is skipped when disabled."""
        helper = DataSecurityHelper()
        helper.masking_enabled = False
        
        text = "Contact john@example.com"
        result = helper.mask_sensitive_data(text)
        
        assert result.masked_text == text
        assert len(result.token_map) == 0
        assert len(result.patterns_found) == 0
    
    def test_specific_patterns_only(self, security_helper):
        """Test masking only specific patterns."""
        text = "Email: john@example.com, Phone: 555-1234, IP: 192.168.1.1"
        result = security_helper.mask_sensitive_data(text, patterns=['email'])
        
        assert "john@example.com" not in result.masked_text
        assert "555-1234" in result.masked_text  # Phone not masked
        assert "192.168.1.1" in result.masked_text  # IP not masked
        assert result.patterns_found == ['email']


class TestEncryption:
    """Test encryption functionality."""
    
    def test_encrypt_decrypt(self, security_helper):
        """Test encryption and decryption."""
        original = "This is sensitive data"
        encrypted = security_helper.encrypt_text(original)
        
        assert encrypted != original
        
        decrypted = security_helper.decrypt_text(encrypted)
        assert decrypted == original
    
    def test_encryption_when_disabled(self):
        """Test that encryption is skipped when disabled."""
        helper = DataSecurityHelper()
        helper.encryption_enabled = False
        
        text = "Secret data"
        encrypted = helper.encrypt_text(text)
        
        assert encrypted == text  # No encryption occurred


class TestHashing:
    """Test hashing functionality."""
    
    def test_hash_pii_sha256(self, security_helper):
        """Test SHA256 hashing."""
        text = "john.doe@example.com"
        hash_result = security_helper.hash_pii(text, algorithm='sha256')
        
        assert len(hash_result) == 64  # SHA256 produces 64 hex chars
        assert hash_result != text
        
        # Same input should produce same hash
        hash_result2 = security_helper.hash_pii(text, algorithm='sha256')
        assert hash_result == hash_result2
    
    def test_hash_pii_md5(self, security_helper):
        """Test MD5 hashing."""
        text = "sensitive@data.com"
        hash_result = security_helper.hash_pii(text, algorithm='md5')
        
        assert len(hash_result) == 32  # MD5 produces 32 hex chars
        assert hash_result != text


class TestRedaction:
    """Test redaction for logging."""
    
    def test_redact_sensitive_keys(self, security_helper):
        """Test redaction of sensitive dictionary keys."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk-1234567890",
            "email": "john@example.com"
        }
        
        redacted = security_helper.redact_for_logging(data)
        
        assert redacted["username"] == "john"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
    
    def test_redact_nested_dict(self, security_helper):
        """Test redaction in nested dictionaries."""
        data = {
            "user": {
                "name": "John",
                "password": "secret"
            },
            "settings": {
                "theme": "dark"
            }
        }
        
        redacted = security_helper.redact_for_logging(data)
        
        assert redacted["user"]["name"] == "John"
        assert redacted["user"]["password"] == "[REDACTED]"
        assert redacted["settings"]["theme"] == "dark"
    
    def test_redact_pii_in_values(self, security_helper):
        """Test redaction of PII patterns in string values."""
        data = {
            "message": "Contact me at john@example.com",
            "note": "Just a regular note"
        }
        
        redacted = security_helper.redact_for_logging(data)
        
        # Email should be masked in the message
        assert "john@example.com" not in redacted["message"]
        assert redacted["note"] == "Just a regular note"


class TestSanitization:
    """Test sanitization for AI inputs."""
    
    def test_sanitize_with_masking(self, security_helper):
        """Test sanitization with PII masking."""
        text = "My email is john@example.com and phone is 555-1234"
        sanitized, metadata = security_helper.sanitize_for_ai(text, mask_pii=True)
        
        assert sanitized != text
        assert "john@example.com" not in sanitized
        assert metadata['masked'] is True
        assert metadata['original_length'] > 0
        assert len(metadata['patterns_found']) > 0
    
    def test_sanitize_without_masking(self, security_helper):
        """Test sanitization without masking."""
        text = "Regular text without PII"
        sanitized, metadata = security_helper.sanitize_for_ai(text, mask_pii=False)
        
        assert sanitized == text
        assert metadata['masked'] is False
    
    def test_sanitize_with_encryption(self, security_helper):
        """Test sanitization with encryption."""
        security_helper.encryption_enabled = True
        text = "Sensitive information"
        sanitized, metadata = security_helper.sanitize_for_ai(
            text, 
            mask_pii=False, 
            encrypt_result=True
        )
        
        assert sanitized != text
        assert metadata['encrypted'] is True
        assert metadata['sanitized_length'] > 0
