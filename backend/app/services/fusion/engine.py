"""Orchestrator for spatial, temporal, confidence, and threshold fusion stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

from app.services.fusion.confidence import ConfidenceScorer
from app.services.fusion.spatial import SpatialGate
from app.services.fusion.temporal import TemporalGate
from app.services.fusion.threshold import ThresholdFilter
from app.services.fusion.types import Incident, Sighting


class FusionRepository(Protocol):
    """Persistence boundary, deliberately separate from the fusion rules."""

    def already_fused(self, event_id: object) -> bool:
        """Return true when a replayed raw event already supports an incident."""

    def active_sightings(self, incident_id: object, reference_time: datetime) -> list[Sighting]:
        """Return persisted sightings attached to an incident."""

    def create_incident(self, sighting: Sighting, road_segment_id: str) -> Incident:
        """Create a candidate incident initialized from one sighting."""

    def attach_sighting(self, incident: Incident, sighting: Sighting, road_segment_id: str) -> None:
        """Persist the raw-sighting to incident association."""

    def save_incident(self, incident: Incident) -> None:
        """Persist derived incident fields."""


@dataclass(frozen=True)
class FusionOutcome:
    """Result returned after one raw sighting passes through fusion."""

    incident: Optional[Incident]
    created: bool
    duplicate: bool
    dashboard_visible: bool
    promoted: bool


class FusionEngine:
    """Fuse one raw sighting using independently testable pipeline stages."""

    def __init__(
        self,
        repository: FusionRepository,
        spatial_gate: SpatialGate,
        temporal_gate: TemporalGate | None = None,
        confidence_scorer: ConfidenceScorer | None = None,
        threshold_filter: ThresholdFilter | None = None,
    ) -> None:
        self._repository = repository
        self._spatial_gate = spatial_gate
        self._temporal_gate = temporal_gate or TemporalGate()
        self._confidence_scorer = confidence_scorer or ConfidenceScorer()
        self._threshold_filter = threshold_filter or ThresholdFilter()

    def fuse(self, sighting: Sighting, road_segment_id: str) -> FusionOutcome:
        """Create or update an incident, making duplicate event replays harmless."""
        if self._repository.already_fused(sighting.event_id):
            return FusionOutcome(
                None, created=False, duplicate=True, dashboard_visible=False, promoted=False
            )

        cutoff = sighting.sighted_at - self._temporal_gate.window
        incident = self._spatial_gate.find_match(sighting, road_segment_id, cutoff)
        created = incident is None
        if incident is None:
            incident = self._repository.create_incident(sighting, road_segment_id)
        was_verified = incident.status == "verified"

        self._repository.attach_sighting(incident, sighting, road_segment_id)
        active_sightings = self._temporal_gate.active_sightings(
            self._repository.active_sightings(incident.id, sighting.sighted_at),
            sighting.sighted_at,
        )
        incident.confidence = self._confidence_scorer.score(active_sightings)
        incident.sighting_count = len(active_sightings)
        incident.last_seen = max(item.sighted_at for item in active_sightings)
        incident.status = (
            "verified"
            if self._threshold_filter.is_verified(incident.confidence, incident.sighting_count)
            else "candidate"
        )
        self._repository.save_incident(incident)
        return FusionOutcome(
            incident,
            created=created,
            duplicate=False,
            dashboard_visible=incident.status == "verified",
            promoted=not was_verified and incident.status == "verified",
        )
