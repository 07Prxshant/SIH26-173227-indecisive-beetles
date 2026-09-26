"""SQLAlchemy adapter that persists results from the pure fusion engine."""

from __future__ import annotations

from datetime import datetime
from typing import Callable
from uuid import UUID

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import RawSighting, VerifiedIncident
from app.services.fusion.engine import FusionEngine, FusionOutcome, FusionRepository
from app.services.fusion.spatial import PostGISSpatialGate, _incident_from_model
from app.services.fusion.types import Incident, Sighting


def sighting_from_model(model: RawSighting) -> Sighting:
    """Project a persisted raw sighting into the value used by fusion rules."""
    return Sighting(
        event_id=model.event_id,
        confidence=model.confidence,
        latitude=model.latitude,
        longitude=model.longitude,
        sighted_at=model.sighted_at,
        source_id=model.source_id,
        image_path=model.image_path,
    )


class SqlAlchemyFusionRepository(FusionRepository):
    """Persistence adapter for raw-sighting links and verified incidents."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def already_fused(self, event_id: object) -> bool:
        return self._session.scalar(
            select(RawSighting.incident_id).where(RawSighting.event_id == event_id)
        ) is not None

    def active_sightings(self, incident_id: object, reference_time: datetime) -> list[Sighting]:
        models = self._session.scalars(
            select(RawSighting)
            .where(RawSighting.incident_id == incident_id)
            .where(RawSighting.sighted_at <= reference_time)
        ).all()
        return [sighting_from_model(model) for model in models]

    def create_incident(self, sighting: Sighting, road_segment_id: str) -> Incident:
        model = VerifiedIncident(
            geometry=WKTElement(f"POINT({sighting.longitude} {sighting.latitude})", srid=4326),
            latitude=sighting.latitude,
            longitude=sighting.longitude,
            road_segment_id=road_segment_id,
            confidence=0.0,
            sighting_count=0,
            first_seen=sighting.sighted_at,
            last_seen=sighting.sighted_at,
            status="candidate",
            representative_image=sighting.image_path,
        )
        self._session.add(model)
        self._session.flush()
        return _incident_from_model(model)

    def attach_sighting(self, incident: Incident, sighting: Sighting, road_segment_id: str) -> None:
        model = self._session.scalar(
            select(RawSighting).where(RawSighting.event_id == sighting.event_id)
        )
        if model is None:
            raise ValueError(f"Raw sighting {sighting.event_id} must be persisted before fusion")
        model.incident_id = incident.id
        model.road_segment_id = road_segment_id

    def save_incident(self, incident: Incident) -> None:
        model = self._session.get(VerifiedIncident, incident.id)
        if model is None:
            raise ValueError(f"Incident {incident.id} disappeared during fusion")
        model.confidence = incident.confidence
        model.sighting_count = incident.sighting_count
        model.last_seen = incident.last_seen
        model.status = incident.status


class SqlAlchemyFusionService:
    """Transactional entry point for fusing an already-persisted raw sighting."""

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def fuse_raw_sighting(self, event_id: UUID, road_segment_id: str) -> FusionOutcome:
        """Run all fusion stages and atomically persist their output."""
        session = self._session_factory()
        try:
            model = session.scalar(select(RawSighting).where(RawSighting.event_id == event_id))
            if model is None:
                raise ValueError(f"Unknown raw sighting event_id: {event_id}")
            repository = SqlAlchemyFusionRepository(session)
            engine = FusionEngine(repository, PostGISSpatialGate(session))
            outcome = engine.fuse(sighting_from_model(model), road_segment_id)
            session.commit()
            return outcome
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
