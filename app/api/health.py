from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["health"])  # simple readiness endpoint
def health() -> dict:
    return {"status": "ok"}