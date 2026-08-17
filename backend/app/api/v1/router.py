from fastapi import APIRouter

from app.api.v1 import analyse, dashboard, dossiers

api_router = APIRouter()
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(dossiers.router, tags=["dossiers"])
api_router.include_router(analyse.router)
