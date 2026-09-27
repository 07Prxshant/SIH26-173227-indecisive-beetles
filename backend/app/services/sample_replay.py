"""Publish the deterministic ML-shaped sample route to ``pothole-events``."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.event_producer import PotholeEventProducer

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_EVENTS_PATH = REPOSITORY_ROOT / "ml" / "sample" / "replay_events.json"


def replay_sample_events() -> int:
    """Publish every schema-valid sample event and wait for broker acknowledgement."""
    events = json.loads(SAMPLE_EVENTS_PATH.read_text(encoding="utf-8"))
    producer = PotholeEventProducer()
    try:
        for event in events:
            producer.publish(event).get(timeout=10)
    finally:
        producer.close()
    return len(events)


if __name__ == "__main__":
    print(f"Published {replay_sample_events()} events to pothole-events")
