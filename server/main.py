import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from server.database import get_db, Base, engine
from server.models import Customer, License, ActivationLog
from server.schemas import (
    ActivationRequest, ActivationResponse,
    ValidationRequest, ValidationResponse,
    HeartbeatRequest, HeartbeatResponse,
    DeactivationRequest, DeactivationResponse
)
from server.config import AOS_SIGNING_SALT
from server.utils import generate_server_license_signature

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AcademyOS Commercial Licensing Server", version="1.1.0")

@app.post("/api/activate", response_model=ActivationResponse)
def activate_license(req: ActivationRequest, db: Session = Depends(get_db)):
    # 1. Fetch license
    lic = db.query(License).filter(License.license_key == req.license_key).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
        
    # 2. Check status and expiry
    if lic.status != "active":
        raise HTTPException(status_code=400, detail=f"License is {lic.status}")
        
    today = datetime.date.today()
    if lic.expiry_date < today:
        lic.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="License has expired")
        
    # 3. Check if this device is already activated for this license
    existing_act = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.device_fingerprint == req.device_fingerprint,
        ActivationLog.is_active == True
    ).first()
    
    if existing_act:
        # Re-generate and return key (idempotent request)
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
        
    # 4. Check device limits
    active_devices_count = db.query(ActivationLog).filter(
        ActivationLog.license_id == lic.id,
        ActivationLog.is_active == True
    ).count()
    
    if active_devices_count >= lic.max_devices:
        raise HTTPException(
            status_code=400,
            detail="Maximum active devices reached for this license. Please deactivate an existing device first."
        )
        
    # 5. Create new activation log
    new_act = ActivationLog(
        license_id=lic.id,
        device_fingerprint=req.device_fingerprint,
        is_active=True
    )
    db.add(new_act)
    db.commit()
    
    # 6. Generate activation key
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
        
    # Update heartbeat
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
