"""Deterministic local road-segment resolution for the SIH replay route."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class GridRoadSegmentResolver:
    """Group nearby replay sightings until a real road matcher is connected."""

    precision: int = 4

    def resolve(self, event: Mapping[str, object]) -> str:
        latitude = round(float(event["gps_lat"]), self.precision)
        longitude = round(float(event["gps_lon"]), self.precision)
        return f"local-grid:{latitude:.{self.precision}f}:{longitude:.{self.precision}f}"
