import hmac
import hashlib

def generate_server_license_signature(license_key: str, expiry_date: str, device_fingerprint: str, salt: bytes) -> str:
    """
    Generate a HMAC-SHA256 signature matching the client application format.
    The client verification expects: HMAC_SHA256(salt, "license_key:expiry_date:device_fingerprint")
    """
    payload = f"{license_key.strip()}:{expiry_date.strip()}:{device_fingerprint.strip()}"
    return hmac.new(salt, payload.encode('utf-8'), hashlib.sha256).hexdigest()
