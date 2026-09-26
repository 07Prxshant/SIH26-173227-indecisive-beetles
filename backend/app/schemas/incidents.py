"""Response models exposed by the incident dashboard API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentStatus(str, Enum):
    """Lifecycle states available to dashboard consumers."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    RESOLVED = "resolved"


class IncidentResponse(BaseModel):
    """A dashboard-ready fused pothole incident."""

    model_config = ConfigDict(from_attributes=True)

    incident_id: UUID
    latitude: float
    longitude: float
    road_segment_id: str
    confidence: float = Field(ge=0, le=1)
    sighting_count: int = Field(ge=0)
    first_seen: datetime
    last_seen: datetime
    status: IncidentStatus
    representative_image: Optional[str] = None


class IncidentPage(BaseModel):
    """A page of incidents for map and table views."""

    items: list[IncidentResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class SightingResponse(BaseModel):
    """A raw ML sighting that contributes to an incident."""

    event_id: UUID
    track_id: str
    detection_class: str
    confidence: float = Field(ge=0, le=1)
    latitude: float
    longitude: float
    sighted_at: datetime
    source_id: str
    frame_id: int = Field(ge=0)
    bbox: dict[str, Any]
    image_path: Optional[str] = None
    road_segment_id: Optional[str] = None
