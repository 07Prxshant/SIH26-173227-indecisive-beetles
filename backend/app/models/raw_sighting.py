"""Raw detection events persisted before any fusion logic is applied."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawSighting(Base):
    """A geo-tagged pothole detection received from the ML event stream."""

    __tablename__ = "raw_sightings"
    __table_args__ = (
        Index("ix_raw_sightings_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(Uuid, unique=True, nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    detection_class: Mapped[str] = mapped_column("class", String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    sighted_at: Mapped[datetime] = mapped_column("timestamp", DateTime(timezone=True), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    frame_id: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
