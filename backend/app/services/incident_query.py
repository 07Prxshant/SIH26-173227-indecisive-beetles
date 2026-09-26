"""Read-only dashboard queries for fused UrbanSense incidents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import RawSighting, VerifiedIncident
from app.schemas.incidents import IncidentPage, IncidentResponse, IncidentStatus, SightingResponse


@dataclass(frozen=True)
class BoundingBox:
    """Latitude/longitude bounds used to restrict map-area queries."""

    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


class IncidentQueryService:
    """Query and serialize dashboard data without exposing ORM models to routes."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def list_incidents(
        self,
        *,
        page: int,
        page_size: int,
        statuses: Optional[Sequence[IncidentStatus]] = None,
        confidence_min: Optional[float] = None,
        bounding_box: Optional[BoundingBox] = None,
    ) -> IncidentPage:
        """Return a stable, filtered page of incidents for dashboard rendering."""
        session = self._session_factory()
        try:
            statement = self._filtered_statement(statuses, confidence_min, bounding_box)
            total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
            models = session.scalars(
                statement.order_by(VerifiedIncident.last_seen.desc(), VerifiedIncident.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return IncidentPage(
                items=[incident_response(model) for model in models],
                total=total,
                page=page,
                page_size=page_size,
            )
        finally:
            session.close()

    def get_incident(self, incident_id: UUID) -> Optional[IncidentResponse]:
        """Return one incident or ``None`` when it does not exist."""
        session = self._session_factory()
        try:
            model = session.get(VerifiedIncident, incident_id)
            return incident_response(model) if model is not None else None
        finally:
            session.close()

    def get_sightings(self, incident_id: UUID) -> Optional[list[SightingResponse]]:
        """Return contributing sightings, or ``None`` when the incident is absent."""
        session = self._session_factory()
        try:
            if session.get(VerifiedIncident, incident_id) is None:
                return None
            models = session.scalars(
                select(RawSighting)
                .where(RawSighting.incident_id == incident_id)
                .order_by(RawSighting.sighted_at.asc(), RawSighting.id)
            ).all()
            return [sighting_response(model) for model in models]
        finally:
            session.close()

    @staticmethod
    def _filtered_statement(
        statuses: Optional[Sequence[IncidentStatus]],
        confidence_min: Optional[float],
        bounding_box: Optional[BoundingBox],
    ):
        statement = select(VerifiedIncident)
        if statuses:
            statement = statement.where(VerifiedIncident.status.in_([status.value for status in statuses]))
        if confidence_min is not None:
            statement = statement.where(VerifiedIncident.confidence >= confidence_min)
        if bounding_box is not None:
            statement = statement.where(
                VerifiedIncident.latitude.between(
                    bounding_box.min_latitude, bounding_box.max_latitude
                ),
                VerifiedIncident.longitude.between(
                    bounding_box.min_longitude, bounding_box.max_longitude
                ),
            )
        return statement


def incident_response(model: VerifiedIncident) -> IncidentResponse:
    """Convert a persistence model to the stable public incident shape."""
    return IncidentResponse(
        incident_id=model.id,
        latitude=model.latitude,
        longitude=model.longitude,
        road_segment_id=model.road_segment_id,
        confidence=model.confidence,
        sighting_count=model.sighting_count,
        first_seen=model.first_seen,
        last_seen=model.last_seen,
        status=model.status,
        representative_image=model.representative_image,
    )


def sighting_response(model: RawSighting) -> SightingResponse:
    """Convert a persistence model to the stable public sighting shape."""
    return SightingResponse(
        event_id=model.event_id,
        track_id=model.track_id,
        detection_class=model.detection_class,
        confidence=model.confidence,
        latitude=model.latitude,
        longitude=model.longitude,
        sighted_at=model.sighted_at,
        source_id=model.source_id,
        frame_id=model.frame_id,
        bbox=model.bbox,
        image_path=model.image_path,
        road_segment_id=model.road_segment_id,
    )
