import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.database import Base, get_db
from server.models import Customer, License, ActivationLog
from server.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test data
    customer = Customer(name="Test Customer", email="test@customer.com")
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Active license with 1 max device
    license_obj = License(
        license_key="AOS-LIC-ACTIVE-1",
        customer_id=customer.id,
        max_devices=1,
        expiry_date=datetime.date.today() + datetime.timedelta(days=30),
        status="active"
    )
    db.add(license_obj)
    db.commit()
    
    yield
    
    Base.metadata.drop_all(bind=engine)

def test_activate_license_not_found():
    response = client.post("/api/activate", json={
        "license_key": "AOS-LIC-NOT-EXIST",
        "device_fingerprint": "client_fp_1"
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "License not found"

def test_activate_license_success():
    response = client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "activation_key" in data
    assert data["expiry_date"] == (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    assert data["activation_key"].startswith("AOS-KEY-")

def test_activate_max_devices_limit():
    # Activate first device
    response1 = client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    assert response1.status_code == 200
    
    # Try to activate second device on max_devices=1 license
    response2 = client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_2"
    })
    assert response2.status_code == 400
    assert "maximum active devices" in response2.json()["detail"].lower()

def test_validate_license():
    # Activate first
    client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    
    # Validate registered device
    response = client.post("/api/validate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "active"
    
    # Validate unregistered device
    response_unreg = client.post("/api/validate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_2"
    })
    assert response_unreg.status_code == 403

def test_deactivate_license():
    # Activate
    client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    
    # Deactivate
    response = client.post("/api/deactivate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "deactivated"
    
    # Try validate again
    response_val = client.post("/api/validate", json={
        "license_key": "AOS-LIC-ACTIVE-1",
        "device_fingerprint": "client_fp_1"
    })
    assert response_val.status_code == 403
