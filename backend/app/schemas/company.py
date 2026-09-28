from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class CompanyBase(BaseModel):
    name: str
    domain: str
    logo_url: Optional[str] = None
    status: str = "active"


class CompanyCreate(CompanyBase):
    pass


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
