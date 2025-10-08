from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.crawl import router as crawl_router
from app.api.browse import router as browse_router, browse as browse_service  # noqa: F401
from app.api.tiktok import router as tiktok_router, tiktok_service  # noqa: F401


router = APIRouter()

router.include_router(health_router)
router.include_router(crawl_router)
router.include_router(browse_router)
router.include_router(tiktok_router)
