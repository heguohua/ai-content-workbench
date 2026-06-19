"""API 路由"""

from app.routers.user import router as user_router
from app.routers.health import router as health_router
from app.routers.article import router as article_router
from app.routers.payment import payment_router, webhook_router
from app.routers.statistics import router as statistics_router
from app.routers.project import router as project_router
from app.routers.session import router as session_router
from app.routers.skill import router as skill_router
from app.routers.artifact import router as artifact_router

__all__ = [
    "user_router",
    "health_router",
    "article_router",
    "payment_router",
    "webhook_router",
    "statistics_router",
    "project_router",
    "session_router",
    "skill_router",
    "artifact_router",
]
