"""Schema for the health-check response."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable response body for the health endpoint."""

    status: str = "ok"
    service: str = "urban-sense-backend"
