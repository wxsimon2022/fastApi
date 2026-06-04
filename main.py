import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print(
        f"启动 {settings.app_name} v{settings.app_version} "
        f"→ http://{settings.host}:{settings.port}"
    )
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
