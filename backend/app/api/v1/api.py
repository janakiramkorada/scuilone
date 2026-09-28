from fastapi import APIRouter
from app.api.v1.endpoints import auth, companies

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Registration"])
api_router.include_router(companies.router, prefix="/companies", tags=["Companies & Tenants"])
