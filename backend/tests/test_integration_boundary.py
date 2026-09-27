"""Contract-boundary tests for the local end-to-end replay path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.services.event_consumer import PotholeEventConsumer
from app.services.event_validation import EventContractValidator
from app.services.road_segment import GridRoadSegmentResolver


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_sample_ml_events_match_the_shared_contract() -> None:
    events = json.loads((REPOSITORY_ROOT / "ml" / "sample" / "replay_events.json").read_text())
    validator = EventContractValidator()

    assert len(events) == 2
    assert all(validator.validate(event)["class"] == "pothole" for event in events)


def test_consumer_fuses_each_new_persisted_event() -> None:
    event: dict[str, Any] = {
        "event_id": "c7fcf4e1-e6ce-42fa-a2bb-8bdc6d9f9a50",
        "gps_lat": 12.9754,
        "gps_lon": 77.6022,
    }
    calls: list[tuple[UUID, str]] = []

    class Processor:
        def process(self, _event: dict[str, Any]) -> bool:
            return True

    class FusionService:
        def fuse_raw_sighting(self, event_id: UUID, road_segment_id: str) -> None:
            calls.append((event_id, road_segment_id))

    consumer = PotholeEventConsumer(
        consumer=object(), processor=Processor(), fusion_service=FusionService(),
        road_segment_resolver=GridRoadSegmentResolver(),
    )

    assert consumer.process_event(event) is True
    assert calls == [(UUID(event["event_id"]), "local-grid:12.9754:77.6022")]
