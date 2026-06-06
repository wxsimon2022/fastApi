from fastapi import APIRouter

from app.controllers.v1 import auth, demo, health, redis_demo, users, messages

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(demo.router)
api_router.include_router(redis_demo.router)
api_router.include_router(users.router)
api_router.include_router(messages.router)
