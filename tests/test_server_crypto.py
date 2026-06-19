import hmac
import hashlib
import pytest
from server.utils import generate_server_license_signature
from server.auth import hash_password, verify_password, create_access_token, verify_access_token

def test_signature_matching():
    salt = b"test_salt"
    key = "AOS-KEY-2026-12-31"
    expiry = "2026-12-31"
    fp = "test_fingerprint_64_chars"
    
    sig = generate_server_license_signature(key, expiry, fp, salt)
    
    # Client expected format:
    payload = f"{key}:{expiry}:{fp}"
    expected = hmac.new(salt, payload.encode('utf-8'), hashlib.sha256).hexdigest()
    assert sig == expected

def test_password_auth():
    password = "supersecretpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_tokens():
    data = {"sub": "admin_user"}
    token = create_access_token(data, expires_delta=60)
    assert token is not None
    
    decoded = verify_access_token(token)
    assert decoded is not None
    assert decoded.get("sub") == "admin_user"

    # Test invalid token
    assert verify_access_token("invalid_token_string") is None
