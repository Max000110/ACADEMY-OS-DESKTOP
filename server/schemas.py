from pydantic import BaseModel
from typing import Optional

class LicenseBase(BaseModel):
    license_key: str
    device_fingerprint: str

class ActivationRequest(LicenseBase):
    pass

class ActivationResponse(BaseModel):
    status: str
    activation_key: str
    expiry_date: str

class ValidationRequest(LicenseBase):
    pass

class ValidationResponse(BaseModel):
    status: str
    expiry_date: str

class HeartbeatRequest(LicenseBase):
    pass

class HeartbeatResponse(BaseModel):
    status: str

class DeactivationRequest(LicenseBase):
    pass

class DeactivationResponse(BaseModel):
    status: str
