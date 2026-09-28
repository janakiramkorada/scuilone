from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class OTPVerification(BaseModel):
    """OTP Verification records for email confirmation, MFA and password resets."""
    __tablename__ = "otp_verifications"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    otp_code = Column(String(10), nullable=False)
    type = Column(String(50), nullable=False)  # email, mfa, reset
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="otp_verifications")
