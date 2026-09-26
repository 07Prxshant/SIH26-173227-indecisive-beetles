"""Fake-event integration tests for the Kafka/Redpanda ingestion path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.services.event_processor import EventProcessor
from app.services.event_validation import EventValidationError


FAKE_EVENT = {
    "event_id": "b7b8df51-19b0-4b59-84a8-9a4d3eebd4a2",
    "class": "pothole",
    "bbox": {"x1": 10, "y1": 20, "x2": 110, "y2": 120},
    "confidence": 0.82,
    "gps_lat": 28.6139,
    "gps_lon": 77.2090,
    "timestamp": "2026-09-26T12:00:00Z",
    "track_id": "track-12",
    "source_id": "bus-12-front",
    "frame_id": 1842,
    "image_ref": "samples/pothole-1842.jpg",
}


@dataclass
class FakeSession:
    existing_id: Any = None
    added: Any = None
    committed: bool = False
    rolled_back: bool = False
    closed: bool = False

    def scalar(self, _statement: Any) -> Any:
        return self.existing_id

    def add(self, model: Any) -> None:
        self.added = model

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_fake_event_is_validated_and_persisted_as_raw_sighting() -> None:
    session = FakeSession()
    processor = EventProcessor(session_factory=lambda: session)

    created = processor.process(FAKE_EVENT)

    assert created is True
    assert session.committed is True
    assert session.added.source_id == "bus-12-front"
    assert session.added.frame_id == 1842
    assert session.added.image_path == "samples/pothole-1842.jpg"


def test_invalid_fake_event_is_rejected_before_persistence() -> None:
    session = FakeSession()
    processor = EventProcessor(session_factory=lambda: session)
    invalid_event = {**FAKE_EVENT, "class": "crack"}

    with pytest.raises(EventValidationError):
        processor.process(invalid_event)

    assert session.added is None
    assert session.committed is False


def test_replayed_event_id_is_not_persisted_twice() -> None:
    session = FakeSession(existing_id="already-persisted")
    processor = EventProcessor(session_factory=lambda: session)

    created = processor.process(FAKE_EVENT)

    assert created is False
    assert session.added is None
    assert session.committed is False
