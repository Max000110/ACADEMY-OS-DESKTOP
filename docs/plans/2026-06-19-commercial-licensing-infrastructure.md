# Commercial Licensing Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a production-grade, functional, and secure commercial licensing backend server, admin panel, activation API, and desktop application integration for AcademyOS v1.1.0, preserving offline compatibility and repository security.

**Architecture:** A centralized FastAPI backend running on a private OCI server backed by PostgreSQL, managing license life-cycle (issue, renew, suspend, revoke) and exposing endpoints for PySide6 client activation and validation. Hardware fingerprint matching is computed symmetrically using a shared HMAC-SHA256 secret salt.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL (prod) / SQLite (dev/test), PySide6, Python-Jose (JWT), Passlib (bcrypt), python-dotenv.

---

### Task 1: Server Project Setup & Database Models

**Files:**
- Create: `server/database.py`
- Create: `server/models.py`
- Create: `server/config.py`
- Create: `server/requirements.txt`
- Test: `tests/test_server_db.py`

**Step 1: Write the failing test**
Create `tests/test_server_db.py` to assert that models can be initialized in a test database and have required fields.
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server.database import Base
from server.models import Customer, License, ActivationLog, AdminUser

def test_database_models():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Assert tables created
    assert engine.has_table("customers")
    assert engine.has_table("licenses")
    assert engine.has_table("activation_logs")
    assert engine.has_table("admin_users")
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_server_db.py`
Expected: FAIL (ModuleNotFound)

**Step 3: Write minimal implementation**
- Create `server/requirements.txt` containing dependencies.
- Create `server/config.py` to load config from env.
- Create `server/database.py` to initialize SQLAlchemy.
- Create `server/models.py` with SQLAlchemy models matching customer details, license status, audit logs, and admin credentials.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_server_db.py`
Expected: PASS

**Step 5: Commit**
```bash
git add server/ tests/test_server_db.py
git commit -m "feat(server): setup database configuration and models"
```

---

### Task 2: Authentication & License Verification Core

**Files:**
- Create: `server/auth.py`
- Create: `server/utils.py`
- Test: `tests/test_server_crypto.py`

**Step 1: Write the failing test**
Create `tests/test_server_crypto.py` verifying HMAC-SHA256 key generation matches client verification payload exactly.
```python
import hmac
import hashlib
from server.utils import generate_server_license_signature

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
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_server_crypto.py`
Expected: FAIL

**Step 3: Write minimal implementation**
- Create `server/auth.py` with password hashing (bcrypt) and JWT encode/decode functions for admin login.
- Create `server/utils.py` containing signature generator.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_server_crypto.py`
Expected: PASS

**Step 5: Commit**
```bash
git add server/auth.py server/utils.py tests/test_server_crypto.py
git commit -m "feat(server): implement cryptographic utils and auth helpers"
```

---

### Task 3: Activation API & Endpoints Implementation

**Files:**
- Create: `server/main.py`
- Create: `server/schemas.py`
- Test: `tests/test_api_endpoints.py`

**Step 1: Write the failing test**
Create `tests/test_api_endpoints.py` verifying that POST requests to `/activate` return valid JSON containing the signed activation key and bind the hardware fingerprint.
```python
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_activate_license_endpoint():
    response = client.post("/api/activate", json={
        "license_key": "AOS-LIC-TEST",
        "device_fingerprint": "client_hw_fingerprint_hash"
    })
    # Verify behavior on non-existent license
    assert response.status_code == 404
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_api_endpoints.py`
Expected: FAIL

**Step 3: Write minimal implementation**
- Implement Pydantic schemas in `server/schemas.py`.
- Define FastAPI routes in `server/main.py`:
  - `POST /api/activate` (first-time bind, returns signed offline key matching the format `AOS-KEY-YYYY-MM-DD-sig`)
  - `POST /api/validate` (checks active status)
  - `POST /api/heartbeat` (logs device check-in)
  - `POST /api/deactivate` (unbinds device)

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_api_endpoints.py`
Expected: PASS

**Step 5: Commit**
```bash
git add server/main.py server/schemas.py tests/test_api_endpoints.py
git commit -m "feat(server): implement activation API endpoints"
```

---

### Task 4: Admin Panel Interface & Operations

**Files:**
- Create: `server/templates/index.html`
- Create: `server/templates/login.html`
- Modify: `server/main.py`
- Test: `tests/test_admin_views.py`

**Step 1: Write the failing test**
Add testing in `tests/test_admin_views.py` verifying HTML template render and routing authentication redirects.
```python
from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_admin_dashboard_requires_login():
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in [302, 307] # Redirects to login
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_admin_views.py`
Expected: FAIL

**Step 3: Write minimal implementation**
- Build HTML files with modern responsive styles (using CSS/Tailwind) under `server/templates/`.
- Add Jinja2 Template rendering for:
  - Secure `/admin/login` page.
  - Interactive `/admin` dashboard containing metrics, customer tables, license lists, and action buttons for revoke/renew.
- Wire API handlers in `server/main.py` for admin forms.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_admin_views.py`
Expected: PASS

**Step 5: Commit**
```bash
git add server/templates/ server/main.py tests/test_admin_views.py
git commit -m "feat(server): build admin dashboard and web panel interface"
```

---

### Task 5: Client Application Integration & Online Activation UI

**Files:**
- Modify: `src/ui/dialogs.py`
- Modify: `src/ui/settings_tab.py`
- Test: `tests/test_client_licensing.py`

**Step 1: Write the failing test**
Add testing in `tests/test_client_licensing.py` verifying that online validation fallback does not break existing local checks.
```python
from src.engines.license import check_license_status

def test_fallback_offline_works():
    status = check_license_status()
    # Offline checks must proceed seamlessly
    assert "activated" in status
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_client_licensing.py`
Expected: FAIL

**Step 3: Write minimal implementation**
- Modify `src/ui/dialogs.py` (ActivationDialog):
  - Add "Online Activation" fields (License Key).
  - On submit, perform HTTP post to `/api/activate`. If successful, call `activate_license()` locally with the signed key returned by the server.
  - Fall back to standard manual offline input if network is unreachable or raw key format matches offline format.
- Modify `src/ui/settings_tab.py`:
  - Show active licensing information and add a "Refresh Activation" button to synchronize online.
- Check backend connectivity asynchronously to avoid UI freezing.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_client_licensing.py`
Expected: PASS

**Step 5: Commit**
```bash
git add src/ui/dialogs.py src/ui/settings_tab.py tests/test_client_licensing.py
git commit -m "feat(client): integrate online activation UI with offline fallback"
```

---

### Task 6: Repository Security Verification Scans

**Files:**
- Create: `server/security_scanner.sh`
- Test: Local run verification

**Step 1: Write failing checks in scanner script**
Write `server/security_scanner.sh` to fail if any IP, private domain pattern, raw API token, or key exists in code or git history.
```bash
#!/bin/bash
set -e
# Verify no PAT tokens (ghp_)
if git diff | grep -E "ghp_[A-Za-z0-9_]{36}" >/dev/null 2>&1; then
    echo "ERROR: Exposed GitHub Token detected in diff!" >&2
    exit 1
fi
```

**Step 2: Run scanner to check it behaves correctly**
Expected: Exit 0 if clean, Exit 1 if secrets found.

**Step 3: Add other rules**
Include search checks for IP formats, SQL database passwords in config files, and release artifacts files.

**Step 4: Make script executable**
Run: `chmod +x server/security_scanner.sh`

**Step 5: Commit**
```bash
git add server/security_scanner.sh
git commit -m "security: add pre-push repository protection script"
```

---

### Task 7: End-to-End Validation & Local Server Verification

**Step 1: Start local server**
`python3 -m uvicorn server.main:app --host 127.0.0.1 --port 8000 &`

**Step 2: Initialize admin user and create test license**
Access SQLite admin DB, insert client license for current device fingerprint.

**Step 3: Perform Activation in UI**
Run client app, activate online via the backend, and confirm signature validates successfully.

**Step 4: Clean up server process**
`kill $(lsof -t -i:8000)`

