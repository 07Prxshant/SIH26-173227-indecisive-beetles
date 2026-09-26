"""Health-check endpoint matching the shared API contract."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Report that the backend process is available."""
    return HealthResponse()
