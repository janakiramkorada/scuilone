from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserOut


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    email: str
    exists: bool
    is_active: bool = False
    message: str


class UserRegisterRequest(BaseModel):
    company_id: str = Field(..., description="ID of the company/tenant selected in Step 1")
    name: str = Field(..., min_length=2, max_length=255, description="Full Name")
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6, description="Account password")
    designation: Optional[str] = None
    department: Optional[str] = None
    employee_id: Optional[str] = None
    location: Optional[str] = None


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification OTP")
    type: str = Field("email", description="Verification type: 'email', 'mfa', or 'reset'")


class ResendOTPRequest(BaseModel):
    email: EmailStr
    type: str = Field("email", description="Verification type: 'email', 'mfa', or 'reset'")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyMFARequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    temp_token: str = Field(..., description="Temporary challenge token returned from initial login")


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional[UserOut] = None
    requires_mfa: bool = False
    temp_token: Optional[str] = None
    message: str = "Success"


class MessageResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
