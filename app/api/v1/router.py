from fastapi import APIRouter

from app.api.v1.endpoints import health, redis_demo, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(redis_demo.router)
api_router.include_router(users.router)
