import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.database import Base, get_db
from server.models import Customer, License, ActivationLog, AdminUser
from server.main import app
from server.auth import hash_password, create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_admin.db"
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
    
    # Create the test admin user
    db.add(AdminUser(username="admin", hashed_password=hash_password("admin")))
    db.commit()
    
    yield
    Base.metadata.drop_all(bind=engine)

def test_admin_dashboard_requires_login():
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert "/admin/login" in response.headers.get("location")

def test_admin_login_page_renders():
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type")
    assert "login" in response.text.lower()

def test_admin_login_success():
    response = client.post("/admin/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    assert response.status_code in [302, 307]
    assert response.headers.get("location") == "/admin"
    assert "access_token" in response.cookies

def test_admin_crud_operations():
    # Log in and set cookie
    token = create_access_token({"sub": "admin"})
    client.cookies.set("access_token", token)

    # 1. Create Customer
    response = client.post("/admin/customers/create", data={
        "name": "Acme Customer",
        "email": "acme@test.com",
        "company": "Acme Corp"
    }, follow_redirects=False)
    assert response.status_code in [302, 307]
    
    db = TestingSessionLocal()
    customer = db.query(Customer).filter(Customer.email == "acme@test.com").first()
    assert customer is not None
    assert customer.name == "Acme Customer"

    # 2. Create License
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    response = client.post("/admin/licenses/create", data={
        "customer_id": customer.id,
        "license_key": "AOS-LIC-ACME",
        "max_devices": 2,
        "expiry_date": tomorrow
    }, follow_redirects=False)
    assert response.status_code in [302, 307]

    license_obj = db.query(License).filter(License.license_key == "AOS-LIC-ACME").first()
    assert license_obj is not None
    assert license_obj.max_devices == 2
    assert license_obj.status == "active"

    # 3. Suspend License
    response = client.post(f"/admin/licenses/{license_obj.id}/suspend", follow_redirects=False)
    assert response.status_code in [302, 307]
    db.refresh(license_obj)
    assert license_obj.status == "suspended"

    # 4. Reactivate License
    response = client.post(f"/admin/licenses/{license_obj.id}/reactivate", follow_redirects=False)
    assert response.status_code in [302, 307]
    db.refresh(license_obj)
    assert license_obj.status == "active"

    # 5. Renew License
    next_week = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    response = client.post(f"/admin/licenses/{license_obj.id}/renew", data={"new_expiry": next_week}, follow_redirects=False)
    assert response.status_code in [302, 307]
    db.refresh(license_obj)
    assert license_obj.expiry_date.strftime("%Y-%m-%d") == next_week

    # 6. Activate a device on the server
    # We call the client API first
    act_response = client.post("/api/activate", json={
        "license_key": "AOS-LIC-ACME",
        "device_fingerprint": "acme_device_1"
    })
    assert act_response.status_code == 200
    
    act_log = db.query(ActivationLog).filter(
        ActivationLog.license_id == license_obj.id,
        ActivationLog.device_fingerprint == "acme_device_1"
    ).first()
    assert act_log is not None
    assert act_log.is_active is True

    # 7. Revoke device activation via admin POST
    response = client.post(f"/admin/activations/{act_log.id}/revoke", follow_redirects=False)
    assert response.status_code in [302, 307]
    db.refresh(act_log)
    assert act_log.is_active is False
