import os
import datetime
from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from server.database import get_db, Base, engine, SessionLocal
from server.models import Customer, License, ActivationLog, AdminUser
from server.schemas import (
    ActivationRequest, ActivationResponse,
    ValidationRequest, ValidationResponse,
    HeartbeatRequest, HeartbeatResponse,
    DeactivationRequest, DeactivationResponse
)
from server.config import AOS_SIGNING_SALT, ACCESS_TOKEN_EXPIRE_MINUTES
from server.utils import generate_server_license_signature
from server.auth import hash_password, verify_password, create_access_token, verify_access_token

# Initialize database tables and add default admin user
Base.metadata.create_all(bind=engine)
db_init = SessionLocal()
try:
    if db_init.query(AdminUser).count() == 0:
        admin_user = os.environ.get("ADMIN_USERNAME", "admin")
        admin_pass = os.environ.get("ADMIN_PASSWORD", "admin")
        db_init.add(AdminUser(
            username=admin_user,
            hashed_password=hash_password(admin_pass)
        ))
        db_init.commit()
finally:
    db_init.close()

app = FastAPI(title="AcademyOS Commercial Licensing Server", version="1.1.0")
templates = Jinja2Templates(directory="server/templates")

# Helper to verify auth from cookies
def get_current_admin(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = verify_access_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    if not username:
        return None
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    return user

# ==================== ADMIN VIEWS ====================

@app.get("/admin/login", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/admin/login")
def post_login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return RedirectResponse(url="/admin/login?error=1", status_code=302)
        
    # Generate token
    token = create_access_token({"sub": username})
    
    # Redirect to admin dashboard and set cookie
    red = RedirectResponse(url="/admin", status_code=302)
    red.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    return red

@app.get("/admin/logout")
def logout():
    red = RedirectResponse(url="/admin/login", status_code=302)
    red.delete_cookie(key="access_token")
    return red

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    # Query stats
    customers_count = db.query(Customer).count()
    active_licenses = db.query(License).filter(License.status == "active").count()
    activations_count = db.query(ActivationLog).filter(ActivationLog.is_active == True).count()
    
    # Query data lists
    customers_list = db.query(Customer).all()
    licenses_list = db.query(License).all()
    activations_list = db.query(ActivationLog).order_by(ActivationLog.activated_at.desc()).all()
    
    # Compute active counts on licenses
    for lic in licenses_list:
        lic.active_count = db.query(ActivationLog).filter(
            ActivationLog.license_id == lic.id,
            ActivationLog.is_active == True
        ).count()
        
    stats = {
        "customers": customers_count,
        "active_licenses": active_licenses,
        "activations": activations_count
    }
    
    return templates.TemplateResponse(request=request, name="index.html", context={
        "stats": stats,
        "customers_list": customers_list,
        "licenses_list": licenses_list,
        "activations_list": activations_list
    })

# ==================== ADMIN POST OPERATIONS ====================

@app.post("/admin/customers/create")
def admin_create_customer(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(None),
    db: Session = Depends(get_db)
):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    # Check duplicate email
    existing = db.query(Customer).filter(Customer.email == email).first()
    if not existing:
        cust = Customer(name=name, email=email, company=company)
        db.add(cust)
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/licenses/create")
def admin_create_license(
    request: Request,
    customer_id: int = Form(...),
    license_key: str = Form(...),
    max_devices: int = Form(...),
    expiry_date: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    # Parse date
    exp_date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").date()
    
    # Check duplicate key
    existing = db.query(License).filter(License.license_key == license_key).first()
    if not existing:
        lic = License(
            license_key=license_key,
            customer_id=customer_id,
            max_devices=max_devices,
            expiry_date=exp_date,
            status="active"
        )
        db.add(lic)
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/licenses/{id}/suspend")
def admin_suspend_license(request: Request, id: int, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    lic = db.query(License).filter(License.id == id).first()
    if lic:
        lic.status = "suspended"
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/licenses/{id}/reactivate")
def admin_reactivate_license(request: Request, id: int, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    lic = db.query(License).filter(License.id == id).first()
    if lic:
        lic.status = "active"
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/licenses/{id}/renew")
def admin_renew_license(
    request: Request,
    id: int,
    new_expiry: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    lic = db.query(License).filter(License.id == id).first()
    if lic:
        exp_date = datetime.datetime.strptime(new_expiry, "%Y-%m-%d").date()
        lic.expiry_date = exp_date
        lic.status = "active"
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/activations/{id}/revoke")
def admin_revoke_activation(request: Request, id: int, db: Session = Depends(get_db)):
    admin = get_current_admin(request, db)
    if not admin:
        return RedirectResponse(url="/admin/login", status_code=302)
        
    act = db.query(ActivationLog).filter(ActivationLog.id == id).first()
    if act:
        act.is_active = False
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)

# ==================== CLIENT API ENDPOINTS ====================

@app.post("/api/activate", response_model=ActivationResponse)
def activate_license(req: ActivationRequest, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    if lic.status != "active":
        raise HTTPException(status_code=400, detail=f"License is {lic.status}")
        
    today = datetime.date.today()
    if lic.expiry_date < today:
        lic.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="License has expired")
        
    existing_act = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.device_fingerprint == req.device_fingerprint,
        ActivationLog.is_active == True
    ).first()
    
    if existing_act:
        existing_act.last_heartbeat = datetime.datetime.utcnow()
        db.commit()
        
        expiry_str = lic.expiry_date.strftime("%Y-%m-%d")
        license_base = f"AOS-KEY-{expiry_str}"
        sig = generate_server_license_signature(license_base, expiry_str, req.device_fingerprint, AOS_SIGNING_SALT.encode('utf-8'))
        activation_key = f"{license_base}-{sig}"
        
        return ActivationResponse(
            status="success",
            activation_key=activation_key,
            expiry_date=expiry_str
        )
        
    active_devices_count = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.is_active == True
    ).count()
    
    if active_devices_count >= lic.max_devices:
        raise HTTPException(
            status_code=400,
            detail="Maximum active devices reached for this license. Please deactivate an existing device first."
        )
        
    new_act = ActivationLog(
        license_id=lic.id,
        device_fingerprint=req.device_fingerprint,
        is_active=True
    )
    db.add(new_act)
    db.commit()
    
    expiry_str = lic.expiry_date.strftime("%Y-%m-%d")
    license_base = f"AOS-KEY-{expiry_str}"
    sig = generate_server_license_signature(license_base, expiry_str, req.device_fingerprint, AOS_SIGNING_SALT.encode('utf-8'))
    activation_key = f"{license_base}-{sig}"
    
    return ActivationResponse(
        status="success",
        activation_key=activation_key,
        expiry_date=expiry_str
    )

@app.post("/api/validate", response_model=ValidationResponse)
def validate_license(req: ValidationRequest, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(status_code=403, detail="Invalid license")
        
    if lic.status != "active":
        raise HTTPException(status_code=403, detail=f"License is {lic.status}")
        
    today = datetime.date.today()
    if lic.expiry_date < today:
        lic.status = "expired"
        db.commit()
        raise HTTPException(status_code=403, detail="License has expired")
        
    act = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.device_fingerprint == req.device_fingerprint,
        ActivationLog.is_active == True
    ).first()
    
    if not act:
        raise HTTPException(status_code=403, detail="Device not activated for this license")
        
    act.last_heartbeat = datetime.datetime.utcnow()
    db.commit()
    
    return ValidationResponse(
        status="active",
        expiry_date=lic.expiry_date.strftime("%Y-%m-%d")
    )

@app.post("/api/heartbeat", response_model=HeartbeatResponse)
def heartbeat(req: HeartbeatRequest, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(status_code=403, detail="Invalid license")
        
    act = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.device_fingerprint == req.device_fingerprint,
        ActivationLog.is_active == True
    ).first()
    
    if not act:
        raise HTTPException(status_code=403, detail="Activation not found or inactive")
        
    act.last_heartbeat = datetime.datetime.utcnow()
    db.commit()
    
    return HeartbeatResponse(status="ok")

@app.post("/api/deactivate", response_model=DeactivationResponse)
def deactivate_license(req: DeactivationRequest, db: Session = Depends(get_db)):
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    act = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.device_fingerprint == req.device_fingerprint,
        ActivationLog.is_active == True
    ).first()
    
    if not act:
        raise HTTPException(status_code=400, detail="No active activation found for this device and license")
        
    act.is_active = False
    db.commit()
    
    return DeactivationResponse(status="deactivated")
