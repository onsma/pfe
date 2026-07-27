from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

