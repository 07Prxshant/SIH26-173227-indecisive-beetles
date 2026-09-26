"""WebSocket tests proving live verified-incident delivery to dashboard clients."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes.live_feed import get_live_feed_manager
from app.main import create_app
from app.schemas.incidents import IncidentResponse, IncidentStatus
from app.services.live_feed import ConnectionManager


INCIDENT_ID = UUID("16cc90f3-f592-4d6e-aeb4-ff6681984623")


def incident(status: IncidentStatus = IncidentStatus.VERIFIED) -> IncidentResponse:
    """Return a deterministic payload accepted by the live-feed manager."""
    return IncidentResponse(
        incident_id=INCIDENT_ID,
        latitude=28.6139,
        longitude=77.2090,
        road_segment_id="delhi-connaught-place-01",
        confidence=0.82,
        sighting_count=3,
        first_seen=datetime(2026, 9, 26, 11, tzinfo=timezone.utc),
        last_seen=datetime(2026, 9, 26, 12, tzinfo=timezone.utc),
        status=status,
        representative_image="samples/pothole.jpg",
    )


def client_with_manager() -> tuple[TestClient, ConnectionManager]:
    application = create_app()
    manager = ConnectionManager()
    application.dependency_overrides[get_live_feed_manager] = lambda: manager
    return TestClient(application), manager


def test_verified_incident_triggers_websocket_notification() -> None:
    client, manager = client_with_manager()

    with client.websocket_connect("/api/v1/live-feed") as websocket:
        assert manager.connection_count == 1
        assert manager.publish_incident_created(incident()) is True

        payload = websocket.receive_json()

    assert payload["type"] == "incident_created"
    assert payload["incident"]["incident_id"] == str(INCIDENT_ID)
    assert payload["incident"]["status"] == "verified"
    assert manager.connection_count == 0


def test_live_feed_broadcasts_to_multiple_clients() -> None:
    client, manager = client_with_manager()

    with client.websocket_connect("/api/v1/live-feed") as first:
        with client.websocket_connect("/api/v1/live-feed") as second:
            assert manager.connection_count == 2
            assert manager.publish_incident_created(incident()) is True

            assert first.receive_json()["type"] == "incident_created"
            assert second.receive_json()["type"] == "incident_created"

    assert manager.connection_count == 0


def test_live_feed_rejects_non_verified_incidents() -> None:
    client, manager = client_with_manager()

    with client.websocket_connect("/api/v1/live-feed"):
        assert manager.publish_incident_created(incident(IncidentStatus.CANDIDATE)) is False
