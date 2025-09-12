from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.crawl import router as crawl_router
from app.api.browse import router as browse_router
from app.api.tiktok import router as tiktok_router


router = APIRouter()

router.include_router(health_router)
router.include_router(crawl_router)
router.include_router(browse_router)
router.include_router(tiktok_router)