"""Endpoint tests for the dashboard incident REST API."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.routes.incidents import get_incident_query_service
from app.main import create_app
from app.schemas.incidents import IncidentPage, IncidentResponse, IncidentStatus, SightingResponse
from app.services.incident_query import BoundingBox


INCIDENT_ID = UUID("16cc90f3-f592-4d6e-aeb4-ff6681984623")
MISSING_ID = UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")
SEEN_AT = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)


class FakeIncidentQueryService:
    """Deterministic route dependency with no PostgreSQL requirement."""

    def __init__(self) -> None:
        self.list_arguments: dict[str, object] | None = None
        self.incident = IncidentResponse(
            incident_id=INCIDENT_ID,
            latitude=28.6139,
            longitude=77.2090,
            road_segment_id="delhi-connaught-place-01",
            confidence=0.82,
            sighting_count=3,
            first_seen=SEEN_AT,
            last_seen=SEEN_AT,
            status=IncidentStatus.VERIFIED,
            representative_image="samples/pothole.jpg",
        )
        self.sighting = SightingResponse(
            event_id=UUID("86aa54e9-32ce-4db9-9cbf-40f5b85db332"),
            track_id="track-12",
            detection_class="pothole",
            confidence=0.82,
            latitude=28.6139,
            longitude=77.2090,
            sighted_at=SEEN_AT,
            source_id="bus-12-front",
            frame_id=1842,
            bbox={"x1": 10, "y1": 20, "x2": 110, "y2": 120},
            image_path="samples/pothole.jpg",
            road_segment_id="delhi-connaught-place-01",
        )

    def list_incidents(self, **kwargs: object) -> IncidentPage:
        self.list_arguments = kwargs
        return IncidentPage(items=[self.incident], total=1, page=kwargs["page"], page_size=kwargs["page_size"])

    def get_incident(self, incident_id: UUID) -> IncidentResponse | None:
        return self.incident if incident_id == INCIDENT_ID else None

    def get_sightings(self, incident_id: UUID) -> list[SightingResponse] | None:
        return [self.sighting] if incident_id == INCIDENT_ID else None


def client_with_fake_service() -> tuple[TestClient, FakeIncidentQueryService]:
    application = create_app()
    service = FakeIncidentQueryService()
    application.dependency_overrides[get_incident_query_service] = lambda: service
    return TestClient(application), service


def test_list_incidents_supports_pagination_and_filters() -> None:
    client, service = client_with_fake_service()

    response = client.get(
        "/api/v1/incidents",
        params={
            "page": 2,
            "page_size": 10,
            "status": ["verified", "candidate"],
            "confidence_min": 0.7,
            "min_latitude": 28.60,
            "max_latitude": 28.70,
            "min_longitude": 77.20,
            "max_longitude": 77.30,
        },
    )

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert response.json()["items"][0]["incident_id"] == str(INCIDENT_ID)
    assert service.list_arguments == {
        "page": 2,
        "page_size": 10,
        "statuses": [IncidentStatus.VERIFIED, IncidentStatus.CANDIDATE],
        "confidence_min": 0.7,
        "bounding_box": BoundingBox(28.60, 28.70, 77.20, 77.30),
    }


def test_list_incidents_rejects_incomplete_bounding_box() -> None:
    client, _ = client_with_fake_service()

    response = client.get("/api/v1/incidents", params={"min_latitude": 28.60})

    assert response.status_code == 422


def test_list_incidents_rejects_inverted_bounding_box() -> None:
    client, _ = client_with_fake_service()

    response = client.get(
        "/api/v1/incidents",
        params={
            "min_latitude": 28.70,
            "max_latitude": 28.60,
            "min_longitude": 77.20,
            "max_longitude": 77.30,
        },
    )

    assert response.status_code == 422


def test_get_incident_returns_documented_shape() -> None:
    client, _ = client_with_fake_service()

    response = client.get(f"/api/v1/incidents/{INCIDENT_ID}")

    assert response.status_code == 200
    assert set(response.json()) == {
        "incident_id", "latitude", "longitude", "road_segment_id", "confidence",
        "sighting_count", "first_seen", "last_seen", "status", "representative_image",
        "detector_confidence", "track_id", "source_id",
    }
    assert response.json()["status"] == "verified"


def test_get_missing_incident_returns_404() -> None:
    client, _ = client_with_fake_service()

    response = client.get(f"/api/v1/incidents/{MISSING_ID}")

    assert response.status_code == 404


def test_get_incident_sightings_returns_contributing_events() -> None:
    client, _ = client_with_fake_service()

    response = client.get(f"/api/v1/incidents/{INCIDENT_ID}/sightings")

    assert response.status_code == 200
    assert response.json()[0]["event_id"] == "86aa54e9-32ce-4db9-9cbf-40f5b85db332"
    assert response.json()[0]["detection_class"] == "pothole"


def test_get_sightings_for_missing_incident_returns_404() -> None:
    client, _ = client_with_fake_service()

    response = client.get(f"/api/v1/incidents/{MISSING_ID}/sightings")

    assert response.status_code == 404


def test_openapi_documents_incident_routes_and_response_models() -> None:
    client, _ = client_with_fake_service()

    document = client.get("/openapi.json").json()

    assert "/api/v1/incidents" in document["paths"]
    assert "/api/v1/incidents/{incident_id}/sightings" in document["paths"]
    assert "IncidentPage" in document["components"]["schemas"]
    assert "SightingResponse" in document["components"]["schemas"]
