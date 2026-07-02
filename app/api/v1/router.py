from app.api.v1.endpoints import auth, demand, department, user
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(demand.router)
api_router.include_router(department.router)
api_router.include_router(user.router)
