"""Bridge committed fusion promotions into the dashboard live-feed manager."""

from __future__ import annotations

from typing import Protocol

from app.schemas.incidents import IncidentResponse
from app.services.fusion.types import Incident
from app.services.live_feed import ConnectionManager, live_feed_manager


class IncidentPublisher(Protocol):
    """Publish a newly dashboard-visible incident after it is committed."""

    def publish_incident_created(self, incident: Incident) -> bool:
        """Publish a just-verified incident."""


class LiveIncidentPublisher:
    """Convert a fusion-domain incident into the documented WebSocket payload."""

    def __init__(self, manager: ConnectionManager = live_feed_manager) -> None:
        self._manager = manager

    def publish_incident_created(self, incident: Incident) -> bool:
        """Send the event when a connected dashboard is available."""
        return self._manager.publish_incident_created(
            IncidentResponse(
                incident_id=incident.id,
                latitude=incident.latitude,
                longitude=incident.longitude,
                road_segment_id=incident.road_segment_id,
                confidence=incident.confidence,
                sighting_count=incident.sighting_count,
                first_seen=incident.first_seen,
                last_seen=incident.last_seen,
                status=incident.status,
                representative_image=incident.representative_image,
            )
        )
