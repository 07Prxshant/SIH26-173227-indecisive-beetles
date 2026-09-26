"""PostGIS-backed matching of a sighting to an active incident."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from geoalchemy2 import Geography, WKTElement
from sqlalchemy import Select, cast, select
from sqlalchemy.sql import func

from app.models import VerifiedIncident
from app.services.fusion.types import Incident, Sighting


class SpatialGate(Protocol):
    """Find an unresolved incident on the same road segment within the radius."""

    def find_match(
        self,
        sighting: Sighting,
        road_segment_id: str,
        reference_time: datetime,
    ) -> Optional[Incident]:
        """Return the nearest eligible incident, if any."""


class PostGISSpatialGate:
    """Run the production spatial gate through PostGIS ``ST_DWithin``."""

    def __init__(self, session: object, distance_meters: float = 15.0) -> None:
        self._session = session
        self.distance_meters = distance_meters

    def statement(
        self,
        sighting: Sighting,
        road_segment_id: str,
        reference_time: datetime,
    ) -> Select[tuple[VerifiedIncident]]:
        """Build the deterministic PostGIS query used for incident matching."""
        point = cast(
            WKTElement(f"POINT({sighting.longitude} {sighting.latitude})", srid=4326),
            Geography(geometry_type="POINT", srid=4326),
        )
        return (
            select(VerifiedIncident)
            .where(VerifiedIncident.road_segment_id == road_segment_id)
            .where(VerifiedIncident.status.in_(("candidate", "verified")))
            .where(VerifiedIncident.last_seen >= reference_time)
            .where(
                func.ST_DWithin(
                    cast(VerifiedIncident.geometry, Geography(geometry_type="POINT", srid=4326)),
                    point,
                    self.distance_meters,
                )
            )
            .order_by(
                func.ST_Distance(
                    cast(VerifiedIncident.geometry, Geography(geometry_type="POINT", srid=4326)),
                    point,
                )
            )
            .limit(1)
        )

    def find_match(
        self,
        sighting: Sighting,
        road_segment_id: str,
        reference_time: datetime,
    ) -> Optional[Incident]:
        """Execute the spatial query and return a database-agnostic incident."""
        model = self._session.scalar(self.statement(sighting, road_segment_id, reference_time))
        return _incident_from_model(model) if model is not None else None


def _incident_from_model(model: VerifiedIncident) -> Incident:
    """Map an ORM model without leaking ORM details into the fusion engine."""
    return Incident(
        id=model.id,
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
