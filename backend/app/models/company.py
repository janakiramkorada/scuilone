from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Company(BaseModel):
    """Company / Tenant entity."""
    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, index=True, nullable=False)
    logo_url = Column(String(500), nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, inactive

    # Relationships
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
