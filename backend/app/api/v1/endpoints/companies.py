from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyOut, CompanyCreate

router = APIRouter()


@router.get("", response_model=List[CompanyOut])
def get_companies(db: Session = Depends(get_db)):
    """
    List all active companies / tenants.
    Used by Step 1 of user registration: 'Choose Your Company'.
    """
    return db.query(Company).filter(Company.status == "active").all()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a single company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(company_in: CompanyCreate, db: Session = Depends(get_db)):
    """Provision a new company / tenant."""
    existing = db.query(Company).filter(Company.domain == company_in.domain.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A company with this domain already exists."
        )

    company = Company(
        name=company_in.name,
        domain=company_in.domain.lower(),
        logo_url=company_in.logo_url,
        status=company_in.status
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
