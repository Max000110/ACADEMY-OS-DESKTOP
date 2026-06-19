import os
import sys
import time
import subprocess
import urllib.request
import json
import datetime

# Setup sys path
sys.path.append("/home/ubuntu/academyos")

from server.database import SessionLocal, Base, engine
from server.models import Customer, License, ActivationLog
from src.engines.license import activate_license, check_license_status, get_device_fingerprint

def main():
    print("=== ACADEMYOS COMMERCIAL LICENSING E2E INTEGRATION TEST ===")
    
    # 1. Start uvicorn server
    server_process = subprocess.Popen(
        ["venv/bin/python", "-m", "uvicorn", "server.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd="/home/ubuntu/academyos",
        env={**os.environ, "PYTHONPATH": "."}
    )
    
    # Wait for server to start
    print("Waiting for licensing server to start...")
    time.sleep(3)
    
    db = SessionLocal()
    try:
        # Create test customer and license
        print("Inserting test customer and license into database...")
        customer = Customer(name="E2E Test Customer", email="e2e@test.com", company="E2E Corp")
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        license_key = "AOS-LIC-E2E-TEST"
        lic = License(
            license_key=license_key,
            customer_id=customer.id,
            max_devices=3,
            expiry_date=datetime.date.today() + datetime.timedelta(days=365),
            status="active"
        )
        db.add(lic)
        db.commit()
        db.refresh(lic)
        
        # 2. Simulate client online activation
        print("Simulating client online activation request...")
        fp = get_device_fingerprint()
        payload = {
            "license_key": license_key,
            "device_fingerprint": fp
        }
        
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/activate",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
        print(f"Server response: {res_data}")
        activation_key = res_data["activation_key"]
        
        # 3. Apply activation locally and check status
        print("Applying activation key locally...")
        assert activate_license(activation_key) is True
        
        print("Checking client license status...")
        status = check_license_status()
        print(f"Licensing status: {status}")
        assert status["activated"] is True
        
        print("E2E VALIDATION SUCCESSFUL!")
        
        # Clean up database records
        print("Cleaning up database records...")
        db.delete(lic)
        db.delete(customer)
        db.commit()
        
    except Exception as e:
        print(f"E2E VALIDATION FAILED: {e}")
        # Clean up if possible
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
        # Clean up local license file
        license_path = os.path.join(os.path.expanduser("~/.academyos"), "license.json")
        if os.path.exists(license_path):
            os.remove(license_path)
            
        # Kill server
        print("Terminating licensing server...")
        server_process.terminate()
        server_process.wait()
        print("Server stopped.")

if __name__ == "__main__":
    main()
