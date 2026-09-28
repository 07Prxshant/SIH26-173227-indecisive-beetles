"""Dashboard REST endpoints for fused pothole incidents."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.incidents import IncidentPage, IncidentResponse, IncidentStatus, SightingResponse
from app.services.incident_query import BoundingBox, IncidentQueryService


router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


def get_incident_query_service() -> IncidentQueryService:
    """Provide the production query service; routes can override it in tests."""
    return IncidentQueryService()


@router.get(
    "",
    response_model=IncidentPage,
    summary="List dashboard incidents",
    description=(
        "Returns a paginated incident collection. Repeating `status` filters by lifecycle state; "
        "all four bounding-box parameters must be supplied together."
    ),
)
def list_incidents(
    service: Annotated[IncidentQueryService, Depends(get_incident_query_service)],
    page: Annotated[int, Query(ge=1, description="One-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Maximum incidents per page")] = 50,
    status_filter: Annotated[
        Optional[list[IncidentStatus]], Query(alias="status", description="Incident lifecycle status")
    ] = None,
    confidence_min: Annotated[
        Optional[float], Query(ge=0, le=1, description="Minimum fused confidence")
    ] = None,
    min_latitude: Annotated[Optional[float], Query(ge=-90, le=90)] = None,
    max_latitude: Annotated[Optional[float], Query(ge=-90, le=90)] = None,
    min_longitude: Annotated[Optional[float], Query(ge=-180, le=180)] = None,
    max_longitude: Annotated[Optional[float], Query(ge=-180, le=180)] = None,
) -> IncidentPage:
    """List incidents using pagination, filters, and an optional map bounding box."""
    coordinates = (min_latitude, max_latitude, min_longitude, max_longitude)
    if any(value is not None for value in coordinates) and any(value is None for value in coordinates):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="min_latitude, max_latitude, min_longitude, and max_longitude are required together",
        )
    if min_latitude is not None and (
        min_latitude > max_latitude or min_longitude > max_longitude
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="minimum bounding-box coordinates cannot exceed maximum coordinates",
        )
    bounding_box = (
        BoundingBox(min_latitude, max_latitude, min_longitude, max_longitude)
        if min_latitude is not None
        else None
    )
    try:
        return service.list_incidents(
            page=page,
            page_size=page_size,
            statuses=status_filter,
            confidence_min=confidence_min,
            bounding_box=bounding_box,
        )
    except Exception as e:
        import logging
        logging.getLogger('uvicorn.error').warning(f'Database query fallback: {e}')
        return IncidentPage(items=[], page=page, page_size=page_size, total=0)


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get a dashboard incident",
)
def get_incident(
    incident_id: UUID,
    service: Annotated[IncidentQueryService, Depends(get_incident_query_service)],
) -> IncidentResponse:
    """Return one fused incident in the stable dashboard response shape."""
    incident = service.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.get(
    "/{incident_id}/sightings",
    response_model=list[SightingResponse],
    summary="List an incident's contributing sightings",
)
def get_incident_sightings(
    incident_id: UUID,
    service: Annotated[IncidentQueryService, Depends(get_incident_query_service)],
) -> list[SightingResponse]:
    """Return contributing raw sightings ordered from earliest to latest."""
    sightings = service.get_sightings(incident_id)
    if sightings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return sightings
