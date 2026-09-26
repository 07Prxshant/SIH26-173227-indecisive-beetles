"""Rolling-window rules for incident corroboration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from app.services.fusion.types import Sighting


class TemporalGate:
    """Keep only sightings in the configured rolling corroboration window."""

    def __init__(self, window: timedelta = timedelta(days=14)) -> None:
        self.window = window

    def active_sightings(self, sightings: Iterable[Sighting], reference_time: datetime) -> list[Sighting]:
        """Return sightings at or after the rolling-window cutoff."""
        cutoff = reference_time - self.window
        return [sighting for sighting in sightings if sighting.sighted_at >= cutoff]
