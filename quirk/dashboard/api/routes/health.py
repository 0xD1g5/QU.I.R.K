"""Health check endpoint."""
from fastapi import APIRouter

from quirk.dashboard.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """GET /api/health — liveness probe. Returns {status: ok}."""
    return HealthResponse(status="ok")
