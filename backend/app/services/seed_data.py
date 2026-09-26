"""Deterministic local dashboard data, intentionally separate from production ingestion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import RawSighting, VerifiedIncident


DEMO_INCIDENTS = (
    {
        "id": UUID("16cc90f3-f592-4d6e-aeb4-ff6681984623"),
        "event_id": UUID("86aa54e9-32ce-4db9-9cbf-40f5b85db332"),
        "latitude": 28.613900,
        "longitude": 77.209000,
        "road_segment_id": "delhi-connaught-place-01",
        "confidence": 0.82,
        "sighting_count": 3,
        "status": "verified",
        "source_id": "bus-12-front",
    },
    {
        "id": UUID("fc854e0d-c2b6-4e80-9e4a-0b71637ffb49"),
        "event_id": UUID("f91a1d9a-d770-4b48-b447-6bb15ff3d23f"),
        "latitude": 28.614700,
        "longitude": 77.210100,
        "road_segment_id": "delhi-connaught-place-02",
        "confidence": 0.58,
        "sighting_count": 1,
        "status": "candidate",
        "source_id": "bus-14-front",
    },
)


def seed_demo_data(session: Session) -> int:
    """Insert missing deterministic incidents and their representative sightings."""
    now = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)
    created = 0
    for item in DEMO_INCIDENTS:
        if session.get(VerifiedIncident, item["id"]) is not None:
            continue
        incident = VerifiedIncident(
            id=item["id"],
            geometry=WKTElement(f"POINT({item['longitude']} {item['latitude']})", srid=4326),
            latitude=item["latitude"],
            longitude=item["longitude"],
            road_segment_id=item["road_segment_id"],
            confidence=item["confidence"],
            sighting_count=item["sighting_count"],
            first_seen=now - timedelta(hours=3),
            last_seen=now - timedelta(minutes=15),
            status=item["status"],
            representative_image=f"samples/{item['id']}.jpg",
        )
        sightings = [
            RawSighting(
                event_id=item["event_id"] if index == 0 else uuid5(item["event_id"], str(index)),
                track_id=f"seed-track-{created + 1}-{index + 1}",
                detection_class="pothole",
                confidence=item["confidence"],
                location=WKTElement(f"POINT({item['longitude']} {item['latitude']})", srid=4326),
                latitude=item["latitude"],
                longitude=item["longitude"],
                sighted_at=now - timedelta(minutes=15 * (index + 1)),
                source_id=f"{item['source_id']}-{index + 1}",
                frame_id=100 + created * 10 + index,
                bbox={"x1": 10, "y1": 20, "x2": 110, "y2": 120},
                image_path=f"samples/{item['id']}.jpg",
                road_segment_id=item["road_segment_id"],
                incident_id=item["id"],
            )
            for index in range(item["sighting_count"])
        ]
        session.add_all((incident, *sightings))
        created += 1
    return created


def run_seed() -> None:
    """Run the idempotent local seed command after database migration."""
    session = get_session_factory()()
    try:
        created = seed_demo_data(session)
        session.commit()
        print(f"Seeded {created} UrbanSense demo incidents.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
