from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    """User account entity with multi-tenant company association and profile attributes."""
    __tablename__ = "users"

    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    
    # Status: pending (awaiting OTP email verification), active, inactive
    status = Column(String(50), default="pending", nullable=False)
    
    # Profile & Organization details (from Image 2, step 3)
    designation = Column(String(150), nullable=True)
    department = Column(String(150), nullable=True)
    employee_id = Column(String(100), nullable=True)
    location = Column(String(150), nullable=True)
    
    # Security flags
    mfa_enabled = Column(Boolean, default=False, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="users")
    role = relationship("Role", back_populates="users")
    otp_verifications = relationship(
        "OTPVerification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(OTPVerification.created_at)"
    )
