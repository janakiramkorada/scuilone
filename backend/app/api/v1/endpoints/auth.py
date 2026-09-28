from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    CheckEmailRequest,
    CheckEmailResponse,
    UserRegisterRequest,
    VerifyOTPRequest,
    ResendOTPRequest,
    LoginRequest,
    VerifyMFARequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    MessageResponse
)
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to retrieve currently authenticated user from Bearer JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid format."
        )

    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("token_type") != "access" or payload.get("mfa_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials."
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    return user


@router.post("/check-email", response_model=CheckEmailResponse)
def check_email(req: CheckEmailRequest, db: Session = Depends(get_db)):
    """Check if an email is already in use before user submits registration."""
    return AuthService.check_email(db, req)


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user associated with a company.
    Creates an inactive/pending user and dispatches a 6-digit OTP code to their email.
    """
    return AuthService.register_user(db, req)


@router.post("/verify-otp", response_model=MessageResponse)
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify 6-digit OTP code and activate the user's account."""
    return AuthService.verify_otp(db, req)


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(req: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend a new 6-digit OTP code if expired or lost."""
    return AuthService.resend_otp(db, req)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email & password.
    Returns access & refresh JWT tokens, or prompts for MFA verification.
    """
    return AuthService.login(db, req)


@router.post("/verify-mfa", response_model=TokenResponse)
def verify_mfa(req: VerifyMFARequest, db: Session = Depends(get_db)):
    """Verify MFA OTP code after initial password authentication."""
    return AuthService.verify_mfa(db, req)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset code to registered email."""
    return AuthService.forgot_password(db, req)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using 6-digit OTP code."""
    return AuthService.reset_password(db, req)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get profile information for the currently signed-in user."""
    role_name = current_user.role.name if current_user.role else "User"
    company_name = current_user.company.name if current_user.company else None

    return UserOut(
        id=current_user.id,
        company_id=current_user.company_id,
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        role_id=current_user.role_id,
        status=current_user.status,
        designation=current_user.designation,
        department=current_user.department,
        employee_id=current_user.employee_id,
        location=current_user.location,
        mfa_enabled=current_user.mfa_enabled,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        company_name=company_name,
        role_name=role_name
    )
