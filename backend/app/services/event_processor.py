"""Idempotent raw-sighting persistence for validated pothole events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping
from uuid import UUID

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import RawSighting
from app.services.event_validation import EventContractValidator


class EventProcessor:
    """Validate and persist events once, making broker retries safe."""

    def __init__(
        self,
        validator: EventContractValidator | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._validator = validator or EventContractValidator()
        self._session_factory = session_factory or get_session_factory()

    def process(self, event: Mapping[str, Any]) -> bool:
        """Persist an event and return whether a new raw sighting was created.

        `event_id` is unique in PostgreSQL. A replayed message is therefore accepted
        but treated as already processed, allowing Kafka/Redpanda retries safely.
        """
        payload = self._validator.validate(event)
        event_id = UUID(payload["event_id"])
        session = self._session_factory()

        try:
            existing = session.scalar(
                select(RawSighting.id).where(RawSighting.event_id == event_id)
            )
            if existing is not None:
                return False

            session.add(self._build_raw_sighting(payload, event_id))
            session.commit()
            return True
        except IntegrityError:
            # A concurrent consumer committed the same event first. This is a safe replay.
            session.rollback()
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _build_raw_sighting(payload: Mapping[str, Any], event_id: UUID) -> RawSighting:
        timestamp = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        latitude = float(payload["gps_lat"])
        longitude = float(payload["gps_lon"])
        image_path = payload.get("image_ref") or payload.get("frame_ref")

        return RawSighting(
            event_id=event_id,
            track_id=str(payload["track_id"]),
            detection_class=str(payload["class"]),
            confidence=float(payload["confidence"]),
            location=WKTElement(f"POINT({longitude} {latitude})", srid=4326),
            latitude=latitude,
            longitude=longitude,
            sighted_at=timestamp,
            source_id=str(payload["source_id"]),
            frame_id=int(payload["frame_id"]),
            bbox=dict(payload["bbox"]),
            image_path=str(image_path) if image_path is not None else None,
        )
