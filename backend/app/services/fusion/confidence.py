"""Confidence calculation for corroborated pothole incidents."""

from __future__ import annotations

from collections.abc import Iterable

from app.services.fusion.types import Sighting


class ConfidenceScorer:
    """Apply the documented, capped confidence formula to active sightings."""

    def score(self, sightings: Iterable[Sighting]) -> float:
        active = list(sightings)
        if not active:
            return 0.0

        # A report may contain a lower-confidence frame later in its track.  Using
        # the strongest active detector observation preserves the detector signal.
        base_detector_conf = max(sighting.confidence for sighting in active)
        corroborating_sightings = len(active)
        distinct_viewpoints = len({sighting.source_id for sighting in active})
        return min(
            1.0,
            base_detector_conf
            + 0.10 * (corroborating_sightings - 1)
            + 0.05 * distinct_viewpoints,
        )
