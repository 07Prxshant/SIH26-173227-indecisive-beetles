"""Unit tests for the PostGIS persistence model definitions."""

from geoalchemy2 import Geography, Geometry

from app.models import RawSighting, VerifiedIncident


def test_raw_sighting_has_required_event_columns() -> None:
    columns = RawSighting.__table__.c

    assert {
        "id", "event_id", "track_id", "class", "confidence", "location",
        "latitude", "longitude", "timestamp", "source_id", "frame_id", "bbox",
        "image_path", "road_segment_id", "incident_id", "created_at",
    } <= set(columns.keys())
    assert isinstance(columns.location.type, Geography)
    assert columns.event_id.unique is True


def test_verified_incident_has_required_persistence_columns() -> None:
    columns = VerifiedIncident.__table__.c

    assert {
        "id", "geometry", "latitude", "longitude", "road_segment_id", "confidence",
        "sighting_count", "first_seen", "last_seen", "status", "representative_image",
        "created_at", "updated_at",
    } <= set(columns.keys())
    assert isinstance(columns.geometry.type, Geometry)
    assert columns.representative_image.nullable is True
