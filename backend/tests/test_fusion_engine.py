"""Deterministic unit tests for the UrbanSense pothole fusion pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from uuid import UUID, uuid5

import pytest

from app.services.fusion.engine import FusionEngine
from app.services.fusion.spatial import PostGISSpatialGate
from app.services.fusion.types import Incident, Sighting


BASE_TIME = datetime(2026, 9, 26, 12, tzinfo=timezone.utc)
EVENT_NAMESPACE = UUID("ac5c5cc2-4253-4013-b102-15e98ed8e48b")


def make_sighting(
    name: str,
    *,
    latitude: float = 28.613900,
    longitude: float = 77.209000,
    confidence: float = 0.40,
    source_id: str = "bus-a-front",
    age: timedelta = timedelta(),
) -> Sighting:
    return Sighting(
        event_id=uuid5(EVENT_NAMESPACE, name),
        confidence=confidence,
        latitude=latitude,
        longitude=longitude,
        sighted_at=BASE_TIME - age,
        source_id=source_id,
        image_path=f"frames/{name}.jpg",
    )


class InMemoryFusionRepository:
    """Minimal persistence fake that leaves the production PostGIS gate untouched."""

    def __init__(self) -> None:
        self.incidents: dict[UUID, Incident] = {}
        self.sightings: dict[UUID, list[Sighting]] = {}
        self.fused_event_ids: set[UUID] = set()
        self._next_id = 0

    def already_fused(self, event_id: object) -> bool:
        return event_id in self.fused_event_ids

    def active_sightings(self, incident_id: object, reference_time: datetime) -> list[Sighting]:
        return list(self.sightings[incident_id])

    def create_incident(self, sighting: Sighting, road_segment_id: str) -> Incident:
        self._next_id += 1
        incident = Incident(
            id=uuid5(EVENT_NAMESPACE, f"incident-{self._next_id}"),
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
        self.incidents[incident.id] = incident
        self.sightings[incident.id] = []
        return incident

    def attach_sighting(self, incident: Incident, sighting: Sighting, road_segment_id: str) -> None:
        self.sightings[incident.id].append(sighting)
        self.fused_event_ids.add(sighting.event_id)

    def save_incident(self, incident: Incident) -> None:
        self.incidents[incident.id] = incident


class InMemorySpatialGate:
    """Distance-equivalent test double for deterministic unit tests."""

    def __init__(self, repository: InMemoryFusionRepository, distance_meters: float = 15.0) -> None:
        self.repository = repository
        self.distance_meters = distance_meters

    def find_match(self, sighting: Sighting, road_segment_id: str, reference_time: datetime) -> Incident | None:
        eligible = (
            incident
            for incident in self.repository.incidents.values()
            if incident.road_segment_id == road_segment_id
            and incident.status in {"candidate", "verified"}
            and incident.last_seen >= reference_time
            and haversine_meters(
                sighting.latitude, sighting.longitude, incident.latitude, incident.longitude
            ) <= self.distance_meters
        )
        return next(eligible, None)


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Small test-only geographic distance helper."""
    earth_radius_m = 6_371_000
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lon2 - lon1)
    haversine = sin(latitude_delta / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(longitude_delta / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(haversine))


def build_engine() -> tuple[FusionEngine, InMemoryFusionRepository]:
    repository = InMemoryFusionRepository()
    return FusionEngine(repository, InMemorySpatialGate(repository)), repository


def test_new_sighting_creates_candidate_incident() -> None:
    engine, repository = build_engine()

    outcome = engine.fuse(make_sighting("new"), "segment-1")

    assert outcome.created is True
    assert outcome.dashboard_visible is False
    assert outcome.incident is not None
    assert outcome.incident.status == "candidate"
    assert outcome.incident.sighting_count == 1
    assert len(repository.incidents) == 1


def test_same_pothole_within_15m_merges_with_existing_incident() -> None:
    engine, _ = build_engine()
    first = engine.fuse(make_sighting("first"), "segment-1")

    outcome = engine.fuse(make_sighting("nearby", latitude=28.613970), "segment-1")

    assert outcome.created is False
    assert outcome.incident is not None
    assert outcome.incident.id == first.incident.id
    assert outcome.incident.sighting_count == 2


def test_different_pothole_more_than_15m_away_creates_another_incident() -> None:
    engine, repository = build_engine()
    engine.fuse(make_sighting("first"), "segment-1")

    outcome = engine.fuse(make_sighting("far", latitude=28.614200), "segment-1")

    assert outcome.created is True
    assert len(repository.incidents) == 2


def test_same_coordinates_on_a_different_road_segment_do_not_merge() -> None:
    engine, repository = build_engine()
    engine.fuse(make_sighting("segment-one"), "segment-1")

    outcome = engine.fuse(make_sighting("segment-two"), "segment-2")

    assert outcome.created is True
    assert len(repository.incidents) == 2


def test_same_location_outside_14_day_window_creates_new_incident() -> None:
    engine, repository = build_engine()
    engine.fuse(make_sighting("old", age=timedelta(days=15)), "segment-1")

    outcome = engine.fuse(make_sighting("current"), "segment-1")

    assert outcome.created is True
    assert len(repository.incidents) == 2


def test_confidence_increases_from_corroboration() -> None:
    engine, _ = build_engine()
    first = engine.fuse(make_sighting("first", confidence=0.40), "segment-1")
    assert first.incident is not None
    first_confidence = first.incident.confidence
    corroborated = engine.fuse(make_sighting("second", confidence=0.40), "segment-1")

    assert corroborated.incident is not None
    assert corroborated.incident.confidence > first_confidence
    assert corroborated.incident.confidence == 0.55


def test_two_corroborating_sightings_promote_incident_at_threshold() -> None:
    engine, _ = build_engine()
    engine.fuse(make_sighting("first", confidence=0.25), "segment-1")

    outcome = engine.fuse(make_sighting("second", confidence=0.25), "segment-1")

    assert outcome.dashboard_visible is True
    assert outcome.incident is not None
    assert outcome.incident.status == "verified"
    assert outcome.incident.confidence == pytest.approx(0.40)


def test_duplicate_sighting_does_not_change_incident() -> None:
    engine, repository = build_engine()
    sighting = make_sighting("duplicate")
    first = engine.fuse(sighting, "segment-1")

    replay = engine.fuse(sighting, "segment-1")

    assert replay.duplicate is True
    assert replay.incident is None
    assert first.incident is not None
    assert len(repository.sightings[first.incident.id]) == 1


def test_multiple_viewpoints_add_the_distinct_viewpoint_bonus() -> None:
    engine, _ = build_engine()
    engine.fuse(make_sighting("first", confidence=0.40, source_id="bus-a-front"), "segment-1")

    outcome = engine.fuse(
        make_sighting("second", confidence=0.40, source_id="bus-b-front"), "segment-1"
    )

    assert outcome.incident is not None
    assert outcome.incident.confidence == 0.60
    assert outcome.dashboard_visible is True


def test_production_spatial_gate_builds_postgis_st_dwithin_query() -> None:
    gate = PostGISSpatialGate(session=object())
    statement = gate.statement(make_sighting("sql"), "segment-1", BASE_TIME - timedelta(days=14))

    assert "ST_DWithin" in str(statement)
    assert gate.distance_meters == 15.0
