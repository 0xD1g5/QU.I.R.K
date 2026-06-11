"""Runtime config endpoint — no auth required (frontend needs this before login)."""
from fastapi import APIRouter

from quirk.config import get_vertical
from quirk.dashboard.api.schemas import ConfigResponse

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    """GET /api/config — returns active vertical setting."""
    return ConfigResponse(vertical=get_vertical())
