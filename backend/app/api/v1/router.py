"""v1 路由聚合入口。"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    events,
    favorites,
    groups,
    health,
    notifications,
    restaurants,
    reviews,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(groups.router)
api_router.include_router(restaurants.router)
api_router.include_router(events.router)
api_router.include_router(reviews.router)
api_router.include_router(favorites.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
