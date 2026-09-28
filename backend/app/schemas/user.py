from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None
    location: Optional[str] = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: Optional[str] = None
    role_id: Optional[str] = None
    status: str
    mfa_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    # Extra populated fields
    company_name: Optional[str] = None
    role_name: Optional[str] = None
