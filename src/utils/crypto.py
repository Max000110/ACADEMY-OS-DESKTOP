import os
import sys
import hmac
import hashlib
import json
import logging

# Load secret salt from environment variable for release hardening.
# Never hardcode production signing keys in repository code or documentation.
AOS_SIGNING_SALT = os.environ.get("AOS_SIGNING_SALT")
if not AOS_SIGNING_SALT:
    is_testing = 'unittest' in sys.modules or any('unittest' in arg or 'pytest' in arg for arg in sys.argv)
    if not is_testing:
        raise RuntimeError("CRITICAL ERROR: AOS_SIGNING_SALT environment variable is missing or empty. Application startup blocked.")
    else:
        SECRET_SALT = b"dev_fallback_salt_do_not_use_in_production"
else:
    SECRET_SALT = AOS_SIGNING_SALT.encode('utf-8')

def generate_signature(license_key: str, expiry_date: str, device_fingerprint: str) -> str:
    """Generate a HMAC-SHA256 signature for the given licensing inputs."""
    payload = f"{license_key.strip()}:{expiry_date.strip()}:{device_fingerprint.strip()}"
    return hmac.new(SECRET_SALT, payload.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_license_payload(license_key: str, expiry_date: str, device_fingerprint: str, signature: str) -> bool:
    """Verify that the license payload matches the signature (preventing tampered files)."""
    expected_sig = generate_signature(license_key, expiry_date, device_fingerprint)
    return hmac.compare_digest(expected_sig, signature)
