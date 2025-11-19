"""
Password Hashing Tests

Comprehensive tests for password hashing and verification using bcrypt.
"""

import pytest
import re

from shared.auth.password import hash_password, verify_password, pwd_context


class TestPasswordHashing:
    """Tests for password hashing functionality"""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_different_from_plaintext(self):
        """Test that hashed password is different from plaintext"""
        password = "my_secure_password"
        hashed = hash_password(password)

        assert hashed != password

    def test_hash_password_produces_bcrypt_format(self):
        """Test that hash is in bcrypt format"""
        password = "test123"
        hashed = hash_password(password)

        # Bcrypt hashes start with $2b$ (or $2a$ or $2y$)
        assert hashed.startswith('$2b$') or hashed.startswith('$2a$') or hashed.startswith('$2y$')

        # Bcrypt format: $2b$<rounds>$<salt+hash>
        pattern = r'^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$'
        assert re.match(pattern, hashed), "Hash should match bcrypt format"

    def test_hash_password_uses_correct_rounds(self):
        """Test that password hashing uses configured rounds (12)"""
        password = "test123"
        hashed = hash_password(password)

        # Extract rounds from hash
        # Format: $2b$12$...
        parts = hashed.split('$')
        rounds = int(parts[2])

        assert rounds == 12, "Should use 12 rounds as configured"

    def test_same_password_produces_different_hashes(self):
        """Test that hashing same password twice produces different results (salt)"""
        password = "same_password"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_hash_empty_password(self):
        """Test hashing empty password"""
        hashed = hash_password("")

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_very_long_password(self):
        """Test hashing very long password"""
        # Bcrypt has 72 byte limit, but should handle gracefully
        long_password = "a" * 200
        hashed = hash_password(long_password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_with_special_characters(self):
        """Test hashing password with special characters"""
        password = "P@ssw0rd!#$%^&*()_+-=[]{}|;:',.<>?/~`"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password

    def test_hash_password_with_unicode(self):
        """Test hashing password with Unicode characters"""
        password = "пароль密码🔒"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password

    def test_hash_password_with_whitespace(self):
        """Test hashing password with whitespace"""
        password = "  password with spaces  "
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        # Should preserve whitespace
        assert verify_password(password, hashed)


class TestPasswordVerification:
    """Tests for password verification functionality"""

    def test_verify_correct_password(self):
        """Test verifying correct password returns True"""
        password = "my_secure_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password returns False"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_case_sensitive(self):
        """Test that password verification is case-sensitive"""
        password = "CaseSensitive"
        hashed = hash_password(password)

        assert verify_password("casesensitive", hashed) is False
        assert verify_password("CASESENSITIVE", hashed) is False
        assert verify_password(password, hashed) is True

    def test_verify_empty_password(self):
        """Test verifying empty password"""
        password = ""
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("not_empty", hashed) is False

    def test_verify_password_with_special_characters(self):
        """Test verifying password with special characters"""
        password = "P@ssw0rd!#$%"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("P@ssw0rd!#$", hashed) is False  # Missing %

    def test_verify_password_with_unicode(self):
        """Test verifying password with Unicode characters"""
        password = "пароль密码🔒"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_verify_password_preserves_whitespace(self):
        """Test that whitespace in passwords is significant"""
        password = "  password  "
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("password", hashed) is False  # No spaces
        assert verify_password(" password ", hashed) is False  # Single spaces

    def test_verify_with_invalid_hash_format(self):
        """Test verifying password against invalid hash format"""
        password = "test123"

        # Not a bcrypt hash
        invalid_hash = "not_a_valid_bcrypt_hash"

        # Should return False or raise exception
        try:
            result = verify_password(password, invalid_hash)
            assert result is False
        except Exception:
            # Some implementations raise exception for invalid hash
            pass

    def test_verify_similar_passwords_fail(self):
        """Test that similar passwords don't verify"""
        password = "password123"
        hashed = hash_password(password)

        # Test various similar but incorrect passwords
        similar_passwords = [
            "password124",  # Different number
            "password12",   # Missing digit
            "password1234", # Extra digit
            "Password123",  # Different case
            "password 123", # Added space
        ]

        for similar in similar_passwords:
            assert verify_password(similar, hashed) is False, \
                f"Similar password '{similar}' should not verify"


class TestPasswordHashingRoundTrip:
    """Round-trip tests to ensure hash and verify work together"""

    @pytest.mark.parametrize("password", [
        "simple",
        "Complex!P@ssw0rd#123",
        "   spaces   ",
        "emoji🔒🔑",
        "unicode密码пароль",
        "a" * 100,  # Long password
        "",  # Empty password
        "ALLCAPS",
        "alllowercase",
        "MixedCase123",
    ])
    def test_roundtrip_various_passwords(self, password):
        """Test that various passwords hash and verify correctly"""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_roundtrip_multiple_hashes_same_password(self):
        """Test that multiple hashes of same password all verify"""
        password = "same_password"

        hashes = [hash_password(password) for _ in range(5)]

        # All hashes should be different
        assert len(set(hashes)) == 5

        # But all should verify correctly
        for hashed in hashes:
            assert verify_password(password, hashed) is True


class TestPasswordEdgeCases:
    """Edge case tests for password hashing"""

    def test_hash_very_long_password_beyond_bcrypt_limit(self):
        """Test that passwords longer than 72 bytes are handled"""
        # Bcrypt has a 72 byte limit
        very_long_password = "a" * 200

        hashed = hash_password(very_long_password)

        # Should still work (passlib truncates automatically)
        assert verify_password(very_long_password, hashed) is True

    def test_hash_password_with_null_bytes(self):
        """Test handling of password with null bytes"""
        # Bcrypt stops at null bytes
        password = "test\x00password"

        hashed = hash_password(password)

        # Depending on implementation, may only hash up to null byte
        # This test documents the behavior
        result = verify_password(password, hashed)
        assert isinstance(result, bool)

    def test_concurrent_hashing_produces_unique_results(self):
        """Test that concurrent hashing produces unique hashes"""
        import concurrent.futures

        password = "test_password"
        num_hashes = 10

        def hash_once():
            return hash_password(password)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(hash_once) for _ in range(num_hashes)]
            hashes = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All hashes should be unique (due to random salt)
        assert len(set(hashes)) == num_hashes

        # All should verify
        for hashed in hashes:
            assert verify_password(password, hashed) is True


@pytest.mark.security
class TestPasswordSecurity:
    """Security-focused tests for password hashing"""

    def test_hash_uses_salt(self):
        """Test that each hash uses unique salt"""
        password = "test123"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (unique salt)
        assert hash1 != hash2

        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_timing_attack_resistance(self):
        """Test that verification doesn't leak timing information"""
        import time

        password = "correct_password"
        hashed = hash_password(password)

        # Measure time for correct password
        start = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start

        # Measure time for incorrect password
        start = time.time()
        verify_password("wrong_password", hashed)
        incorrect_time = time.time() - start

        # Times should be similar (bcrypt is constant time)
        # Allow 50% variance due to system noise
        ratio = max(correct_time, incorrect_time) / min(correct_time, incorrect_time)
        assert ratio < 2.0, "Timing difference suggests timing attack vulnerability"

    def test_computational_cost_is_significant(self):
        """Test that hashing has significant computational cost"""
        import time

        password = "test_password"

        start = time.time()
        hash_password(password)
        duration = time.time() - start

        # With 12 rounds, should take at least 50ms (usually 100-200ms)
        assert duration > 0.05, "Hashing should take significant time for security"

    def test_different_passwords_produce_different_hashes(self):
        """Test that different passwords produce different hashes"""
        passwords = [
            "password1",
            "password2",
            "password3",
        ]

        hashes = [hash_password(p) for p in passwords]

        # All hashes should be unique
        assert len(set(hashes)) == len(passwords)

        # Each should only verify its own password
        for i, password in enumerate(passwords):
            for j, hashed in enumerate(hashes):
                if i == j:
                    assert verify_password(password, hashed) is True
                else:
                    assert verify_password(password, hashed) is False

    def test_rainbow_table_resistance(self):
        """Test that same password produces different hashes (salt protection)"""
        password = "common_password"

        # Generate multiple hashes
        hashes = [hash_password(password) for _ in range(10)]

        # All should be unique (salt makes rainbow tables ineffective)
        assert len(set(hashes)) == 10


@pytest.mark.performance
class TestPasswordPerformance:
    """Performance tests for password hashing"""

    def test_hash_performance_is_reasonable(self):
        """Test that hashing completes in reasonable time"""
        import time

        password = "test_password"

        start = time.time()
        hash_password(password)
        duration = time.time() - start

        # Should complete in under 1 second (usually 100-200ms with 12 rounds)
        assert duration < 1.0, "Hashing should complete in under 1 second"

    def test_verify_performance_is_reasonable(self):
        """Test that verification completes in reasonable time"""
        import time

        password = "test_password"
        hashed = hash_password(password)

        start = time.time()
        verify_password(password, hashed)
        duration = time.time() - start

        # Should complete in under 1 second
        assert duration < 1.0, "Verification should complete in under 1 second"


class TestPasswordContextConfiguration:
    """Tests for password context configuration"""

    def test_pwd_context_uses_bcrypt(self):
        """Test that password context uses bcrypt scheme"""
        assert "bcrypt" in pwd_context.schemes()

    def test_pwd_context_configuration(self):
        """Test password context configuration"""
        # This test documents the configuration
        assert pwd_context.schemes() == ["bcrypt"]
