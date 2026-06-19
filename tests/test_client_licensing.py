import os
import json
import datetime
import pytest
from src.engines.license import check_license_status, activate_license, get_device_fingerprint
from src.utils.config import APP_DIR, load_settings, save_settings
from src.utils.crypto import generate_signature

def test_client_license_status_when_not_activated():
    # Ensure license file does not exist during this test
    license_path = os.path.join(APP_DIR, "license.json")
    if os.path.exists(license_path):
        os.remove(license_path)
        
    status = check_license_status()
    assert status["activated"] is False
    assert status["error"] == "Not Activated"

def test_client_license_status_offline_activation():
    fp = get_device_fingerprint()
    expiry = (datetime.date.today() + datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    # Generate signature using the secret salt
    sig = generate_signature(f"AOS-KEY-{expiry}", expiry, fp)
    activation_key = f"AOS-KEY-{expiry}-{sig}"
    
    # Activate
    success = activate_license(activation_key)
    assert success is True
    
    # Verify status
    status = check_license_status()
    assert status["activated"] is True
    assert status["expiry_date"] == expiry
    assert status["days_remaining"] >= 364
    assert status["error"] is None

    # Clean up license file after test
    license_path = os.path.join(APP_DIR, "license.json")
    if os.path.exists(license_path):
        os.remove(license_path)
