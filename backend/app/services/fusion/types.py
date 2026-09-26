"""Small, database-agnostic values shared by fusion services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class Sighting:
    """The fusion-relevant projection of a persisted raw sighting."""

    event_id: UUID
    confidence: float
    latitude: float
    longitude: float
    sighted_at: datetime
    source_id: str
    image_path: Optional[str] = None


@dataclass
class Incident:
    """The fusion-relevant projection of an active pothole incident."""

    id: UUID
    latitude: float
    longitude: float
    road_segment_id: str
    confidence: float
    sighting_count: int
    first_seen: datetime
    last_seen: datetime
    status: str
    representative_image: Optional[str] = None
