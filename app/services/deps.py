"""Service 层依赖注入。"""

from typing import Annotated

from fastapi import Depends

from app.config import get_settings
from app.db.deps import UserRepo, MessageRepo
from app.redis.deps import RedisCacheDep
from app.services.auth_service import AuthService
from app.services.concurrent_service import ConcurrentQueryService
from app.services.user_service import UserService


def get_auth_service(repo: UserRepo, cache: RedisCacheDep) -> AuthService:
    return AuthService(repo=repo, cache=cache, settings=get_settings())


def get_user_service(repo: UserRepo, cache: RedisCacheDep) -> UserService:
    return UserService(repo=repo, cache=cache, settings=get_settings())


def get_concurrent_query_service() -> ConcurrentQueryService:
    return ConcurrentQueryService()


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ConcurrentQueryServiceDep = Annotated[
    ConcurrentQueryService,
    Depends(get_concurrent_query_service),
]

from app.services.messages_service import MessageService


def get_messages_service(repo: MessageRepo) -> MessageService:
    return MessageService(repo=repo)


MessageServiceDep = Annotated[MessageService, Depends(get_messages_service)]
