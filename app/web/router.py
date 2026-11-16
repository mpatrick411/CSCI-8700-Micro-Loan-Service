from fastapi import APIRouter

from app.web import routes_admin, routes_officer, routes_student

api_router = APIRouter(prefix="/api")
api_router.include_router(routes_student.router)
api_router.include_router(routes_officer.router)
api_router.include_router(routes_admin.router)
