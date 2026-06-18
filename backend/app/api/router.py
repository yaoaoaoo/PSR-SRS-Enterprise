"""V1 API router — registers all route modules."""

from fastapi import APIRouter

from app.api.routes import evaluation, events, health, items, profiles, search, system, users

router = APIRouter()

router.include_router(health.router)
router.include_router(search.router)
router.include_router(items.router)
router.include_router(users.router)
router.include_router(evaluation.router)
router.include_router(events.router)
router.include_router(profiles.router)
router.include_router(system.router)
