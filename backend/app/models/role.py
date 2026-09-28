from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Role(BaseModel):
    """System and Tenant roles."""
    __tablename__ = "roles"

    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")


class UserRole(BaseModel):
    """Many-to-many link between Users and Roles."""
    __tablename__ = "user_roles"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
