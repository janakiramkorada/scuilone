from sqlalchemy.orm import Session
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.company import Company
from app.models.role import Role
from app.models.user import User
from app.models.otp import OTPVerification


def init_db(db: Session) -> None:
    """Create tables and populate seed data for companies, roles and default users."""
    Base.metadata.create_all(bind=engine)

    # 1. Seed Roles
    initial_roles = [
        {"name": "Platform Super Admin", "description": "Manage tenants, plans, global settings and operations"},
        {"name": "Tenant Admin", "description": "Manage users, roles, modules, pipelines and settings"},
        {"name": "Manager", "description": "Manage team pipeline, assignments and approvals"},
        {"name": "Sales User", "description": "Manage leads, contacts, opportunities and activities"},
        {"name": "Support User", "description": "Handle customer issues, tickets and communications"},
    ]

    role_objs = {}
    for r in initial_roles:
        existing = db.query(Role).filter(Role.name == r["name"]).first()
        if not existing:
            role = Role(name=r["name"], description=r["description"])
            db.add(role)
            db.flush()
            role_objs[r["name"]] = role
        else:
            role_objs[r["name"]] = existing

    # 2. Seed Initial Companies (Tenants) from Registration Flow UI
    initial_companies = [
        {"name": "RK Real Estate", "domain": "realestate.scuilone.com", "logo_url": "/logos/realestate.svg"},
        {"name": "EduGlobal", "domain": "education.scuilone.com", "logo_url": "/logos/education.svg"},
        {"name": "TechSolutions", "domain": "software.scuilone.com", "logo_url": "/logos/software.svg"},
        {"name": "SafeLife Insurance", "domain": "insurance.scuilone.com", "logo_url": "/logos/insurance.svg"},
        {"name": "AutoDrive Motors", "domain": "automobile.scuilone.com", "logo_url": "/logos/automobile.svg"},
    ]

    company_objs = {}
    for c in initial_companies:
        existing = db.query(Company).filter(Company.domain == c["domain"]).first()
        if not existing:
            company = Company(
                name=c["name"],
                domain=c["domain"],
                logo_url=c["logo_url"],
                status="active"
            )
            db.add(company)
            db.flush()
            company_objs[c["name"]] = company
        else:
            company_objs[c["name"]] = existing

    # 3. Seed Default Platform Super Admin
    super_admin_email = "admin@scuilone.com"
    existing_super_admin = db.query(User).filter(User.email == super_admin_email).first()
    if not existing_super_admin:
        super_admin = User(
            name="Super Admin",
            email=super_admin_email,
            phone="+91 9876543210",
            password_hash=hash_password("Admin@123456"),
            role_id=role_objs["Platform Super Admin"].id,
            status="active",
            designation="Platform Administrator",
            department="Operations",
            mfa_enabled=False
        )
        db.add(super_admin)

    # 4. Seed Demo Tenant Admin (for RK Real Estate)
    tenant_admin_email = "admin@rkrealestate.com"
    existing_tenant_admin = db.query(User).filter(User.email == tenant_admin_email).first()
    if not existing_tenant_admin and "RK Real Estate" in company_objs:
        tenant_admin = User(
            company_id=company_objs["RK Real Estate"].id,
            name="RK Real Estate Admin",
            email=tenant_admin_email,
            phone="+91 9876501234",
            password_hash=hash_password("Tenant@123456"),
            role_id=role_objs["Tenant Admin"].id,
            status="active",
            designation="Managing Director",
            department="Executive",
            location="Hyderabad",
            mfa_enabled=False
        )
        db.add(tenant_admin)

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
        print("Database initialized and seeded successfully.")
    finally:
        db.close()
