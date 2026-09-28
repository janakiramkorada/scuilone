from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp
)
from app.models.company import Company
from app.models.user import User
from app.models.role import Role
from app.models.otp import OTPVerification
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
from app.services.email_service import email_service


class AuthService:
    @staticmethod
    def check_email(db: Session, req: CheckEmailRequest) -> CheckEmailResponse:
        """Check if email is already registered and if it's active."""
        user = db.query(User).filter(User.email == req.email.lower()).first()
        if not user:
            return CheckEmailResponse(
                email=req.email,
                exists=False,
                is_active=False,
                message="Email is available for registration."
            )
        
        return CheckEmailResponse(
            email=req.email,
            exists=True,
            is_active=(user.status == "active"),
            message="Email already registered." if user.status == "active" else "Email registered but pending verification."
        )

    @staticmethod
    def register_user(db: Session, req: UserRegisterRequest) -> MessageResponse:
        """
        Step 2 & 3: Register a new user under a chosen company.
        User starts with status='pending', and a 6-digit OTP is dispatched.
        """
        email_clean = req.email.lower()
        existing_user = db.query(User).filter(User.email == email_clean).first()
        if existing_user:
            if existing_user.status == "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email already exists."
                )
            # If pending, update existing registration
            user = existing_user
            user.name = req.name
            user.phone = req.phone
            user.password_hash = hash_password(req.password)
            user.company_id = req.company_id
            user.designation = req.designation
            user.department = req.department
            user.employee_id = req.employee_id
            user.location = req.location
        else:
            # Verify company exists
            company = db.query(Company).filter(Company.id == req.company_id).first()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Selected company not found."
                )

            # Assign default role (e.g., 'Sales User' or first role)
            default_role = db.query(Role).filter(Role.name == "Sales User").first()
            role_id = default_role.id if default_role else None

            user = User(
                company_id=req.company_id,
                name=req.name,
                email=email_clean,
                phone=req.phone,
                password_hash=hash_password(req.password),
                role_id=role_id,
                status="pending",
                designation=req.designation,
                department=req.department,
                employee_id=req.employee_id,
                location=req.location,
                mfa_enabled=False
            )
            db.add(user)
            db.flush()

        # Invalidate old OTPs for this user & type
        db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.type == "email"
        ).update({"is_verified": True})

        # Generate and save new 6-digit OTP
        otp_code = generate_otp(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = OTPVerification(
            user_id=user.id,
            otp_code=otp_code,
            type="email",
            expires_at=expires_at,
            is_verified=False
        )
        db.add(otp_record)
        db.commit()

        # Dispatch OTP via email service
        email_service.send_otp_email(user.email, user.name, otp_code, "email")

        return MessageResponse(
            success=True,
            message="Registration initiated. A 6-digit verification code has been sent to your email.",
            data={"email": user.email, "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}
        )

    @staticmethod
    def verify_otp(db: Session, req: VerifyOTPRequest) -> MessageResponse:
        """
        Step 4: Verify 6-digit OTP and activate user account.
        """
        email_clean = req.email.lower()
        user = db.query(User).filter(User.email == email_clean).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        now = datetime.now(timezone.utc)
        otp_entry = db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.otp_code == req.otp_code.strip(),
            OTPVerification.type == req.type,
            OTPVerification.is_verified == False
        ).order_by(OTPVerification.created_at.desc()).first()

        if not otp_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code."
            )

        # Check expiration
        entry_expiry = otp_entry.expires_at
        if entry_expiry.tzinfo is None:
            entry_expiry = entry_expiry.replace(tzinfo=timezone.utc)

        if now > entry_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new code."
            )

        otp_entry.is_verified = True
        if req.type == "email":
            user.status = "active"

        db.commit()

        return MessageResponse(
            success=True,
            message="Email verified successfully! Your account is now active.",
            data={"email": user.email, "status": user.status}
        )

    @staticmethod
    def resend_otp(db: Session, req: ResendOTPRequest) -> MessageResponse:
        """Resend a new 6-digit OTP code to the user's email."""
        email_clean = req.email.lower()
        user = db.query(User).filter(User.email == email_clean).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Invalidate previous unverified codes
        db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.type == req.type,
            OTPVerification.is_verified == False
        ).update({"is_verified": True})

        otp_code = generate_otp(6)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_record = OTPVerification(
            user_id=user.id,
            otp_code=otp_code,
            type=req.type,
            expires_at=expires_at,
            is_verified=False
        )
        db.add(otp_record)
        db.commit()

        email_service.send_otp_email(user.email, user.name, otp_code, req.type)

        return MessageResponse(
            success=True,
            message="A fresh verification code has been sent to your email.",
            data={"email": user.email, "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}
        )

    @staticmethod
    def login(db: Session, req: LoginRequest) -> TokenResponse:
        """
        Authenticate user with email and password.
        Handles pending verification, deactivated accounts, and MFA if enabled.
        """
        email_clean = req.email.lower()
        user = db.query(User).filter(User.email == email_clean).first()
        
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        if user.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is pending email verification. Please verify your OTP."
            )

        if user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive. Please contact your administrator."
            )

        # Check if user requires MFA
        if user.mfa_enabled:
            otp_code = generate_otp(6)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
            
            otp_record = OTPVerification(
                user_id=user.id,
                otp_code=otp_code,
                type="mfa",
                expires_at=expires_at,
                is_verified=False
            )
            db.add(otp_record)
            db.commit()
            
            email_service.send_otp_email(user.email, user.name, otp_code, "mfa")
            
            temp_token = create_access_token(
                {"sub": user.id, "email": user.email, "mfa_pending": True},
                expires_delta=timedelta(minutes=10)
            )
            
            return TokenResponse(
                requires_mfa=True,
                temp_token=temp_token,
                message="MFA code sent to your registered email."
            )

        return AuthService._build_login_response(db, user)

    @staticmethod
    def verify_mfa(db: Session, req: VerifyMFARequest) -> TokenResponse:
        """Verify MFA code challenge during login."""
        payload = decode_token(req.temp_token)
        if not payload or not payload.get("mfa_pending"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired MFA session."
            )

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        now = datetime.now(timezone.utc)
        otp_entry = db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.otp_code == req.otp_code.strip(),
            OTPVerification.type == "mfa",
            OTPVerification.is_verified == False
        ).order_by(OTPVerification.created_at.desc()).first()

        if not otp_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA verification code."
            )

        entry_expiry = otp_entry.expires_at
        if entry_expiry.tzinfo is None:
            entry_expiry = entry_expiry.replace(tzinfo=timezone.utc)

        if now > entry_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA code has expired. Please log in again."
            )

        otp_entry.is_verified = True
        db.commit()

        return AuthService._build_login_response(db, user)

    @staticmethod
    def forgot_password(db: Session, req: ForgotPasswordRequest) -> MessageResponse:
        """Send password reset OTP."""
        email_clean = req.email.lower()
        user = db.query(User).filter(User.email == email_clean).first()
        
        # Avoid account enumeration: always return standard success message
        if user and user.status == "active":
            otp_code = generate_otp(6)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
            
            otp_record = OTPVerification(
                user_id=user.id,
                otp_code=otp_code,
                type="reset",
                expires_at=expires_at,
                is_verified=False
            )
            db.add(otp_record)
            db.commit()
            
            email_service.send_otp_email(user.email, user.name, otp_code, "reset")

        return MessageResponse(
            success=True,
            message="If an active account exists with this email, a password reset code has been sent."
        )

    @staticmethod
    def reset_password(db: Session, req: ResetPasswordRequest) -> MessageResponse:
        """Reset password with verified OTP."""
        email_clean = req.email.lower()
        user = db.query(User).filter(User.email == email_clean).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        now = datetime.now(timezone.utc)
        otp_entry = db.query(OTPVerification).filter(
            OTPVerification.user_id == user.id,
            OTPVerification.otp_code == req.otp_code.strip(),
            OTPVerification.type == "reset",
            OTPVerification.is_verified == False
        ).order_by(OTPVerification.created_at.desc()).first()

        if not otp_entry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid password reset code."
            )

        entry_expiry = otp_entry.expires_at
        if entry_expiry.tzinfo is None:
            entry_expiry = entry_expiry.replace(tzinfo=timezone.utc)

        if now > entry_expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset code has expired. Please request a new one."
            )

        # Update password
        user.password_hash = hash_password(req.new_password)
        otp_entry.is_verified = True
        db.commit()

        return MessageResponse(
            success=True,
            message="Password successfully reset! You can now log in with your new password."
        )

    @staticmethod
    def _build_login_response(db: Session, user: User) -> TokenResponse:
        """Helper to create tokens and user representation."""
        role_name = user.role.name if user.role else "User"
        company_name = user.company.name if user.company else None

        token_payload = {
            "sub": user.id,
            "email": user.email,
            "company_id": user.company_id,
            "role": role_name,
            "is_super_admin": (role_name == "Platform Super Admin")
        }

        access_token = create_access_token(token_payload)
        refresh_token = create_refresh_token(token_payload)

        user_out = UserOut(
            id=user.id,
            company_id=user.company_id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role_id=user.role_id,
            status=user.status,
            designation=user.designation,
            department=user.department,
            employee_id=user.employee_id,
            location=user.location,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            company_name=company_name,
            role_name=role_name
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_out,
            requires_mfa=False,
            message="Login successful"
        )
