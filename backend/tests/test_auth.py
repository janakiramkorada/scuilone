import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.db.init_db import init_db
from app.services.email_service import last_sent_otps

# In-memory test SQLite DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_scuilone.db"
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


def test_get_companies():
    res = client.get("/api/v1/companies")
    assert res.status_code == 200
    companies = res.json()
    assert len(companies) >= 5
    company_names = [c["name"] for c in companies]
    assert "RK Real Estate" in company_names
    assert "TechSolutions" in company_names


def test_check_email():
    res = client.post("/api/v1/auth/check-email", json={"email": "newuser@example.com"})
    assert res.status_code == 200
    assert res.json()["exists"] is False

    # Seeded admin email should exist
    res_admin = client.post("/api/v1/auth/check-email", json={"email": "admin@scuilone.com"})
    assert res_admin.status_code == 200
    assert res_admin.json()["exists"] is True


def test_full_user_registration_and_activation_flow():
    # 1. Fetch company ID for RK Real Estate
    comp_res = client.get("/api/v1/companies")
    rk_company = next(c for c in comp_res.json() if c["name"] == "RK Real Estate")
    company_id = rk_company["id"]

    email = "bavya@example.com"
    
    # 2. Register user (matches mockups in Image 2)
    reg_payload = {
        "company_id": company_id,
        "name": "Bavya Upparalla",
        "email": email,
        "phone": "+91 9876543210",
        "password": "Password@123",
        "designation": "Software Engineer",
        "department": "Technology",
        "employee_id": "EMP001",
        "location": "Hyderabad"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    assert reg_res.json()["success"] is True

    # 3. Trying to login before OTP verification should be forbidden (403)
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    assert login_res.status_code == 403
    assert "pending email verification" in login_res.json()["detail"]

    # 4. Verify OTP using the code sent by email service
    assert email in last_sent_otps
    otp = last_sent_otps[email]
    
    verify_res = client.post("/api/v1/auth/verify-otp", json={
        "email": email,
        "otp_code": otp,
        "type": "email"
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True
    assert verify_res.json()["data"]["status"] == "active"

    # 5. Login now should succeed and issue JWT tokens
    login_success = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    assert login_success.status_code == 200
    data = login_success.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["company_name"] == "RK Real Estate"
    assert data["user"]["status"] == "active"

    token = data["access_token"]

    # 6. Retrieve profile using Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["name"] == "Bavya Upparalla"
    assert me_data["employee_id"] == "EMP001"
    assert me_data["designation"] == "Software Engineer"


def test_login_invalid_password():
    res = client.post("/api/v1/auth/login", json={"email": "admin@scuilone.com", "password": "WrongPassword"})
    assert res.status_code == 401


def test_forgot_and_reset_password_flow():
    email = "admin@scuilone.com"
    
    # 1. Request forgot password
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200

    otp = last_sent_otps.get(email)
    assert otp is not None

    # 2. Reset password with OTP
    reset_res = client.post("/api/v1/auth/reset-password", json={
        "email": email,
        "otp_code": otp,
        "new_password": "NewSecretPassword@123"
    })
    assert reset_res.status_code == 200
    assert reset_res.json()["success"] is True

    # 3. Login with new password
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "NewSecretPassword@123"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_mfa_login_flow():
    # 1. Enable MFA on a user
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@scuilone.com").first()
        user.mfa_enabled = True
        db.commit()
    finally:
        db.close()

    # 2. Login should prompt for MFA
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@scuilone.com", "password": "NewSecretPassword@123"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["requires_mfa"] is True
    assert "temp_token" in data
    temp_token = data["temp_token"]

    # 3. An MFA OTP was sent
    otp = last_sent_otps.get("admin@scuilone.com")
    assert otp is not None

    # 4. Verify MFA
    mfa_res = client.post("/api/v1/auth/verify-mfa", json={
        "email": "admin@scuilone.com",
        "otp_code": otp,
        "temp_token": temp_token
    })
    assert mfa_res.status_code == 200
    mfa_data = mfa_res.json()
    assert "access_token" in mfa_data
    assert mfa_data["user"]["email"] == "admin@scuilone.com"
