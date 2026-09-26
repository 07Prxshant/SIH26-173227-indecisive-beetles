"""Dashboard-visibility policy for fused incidents."""

from __future__ import annotations


class ThresholdFilter:
    """Promote incidents meeting either documented verification condition."""

    def __init__(self, confidence_threshold: float = 0.6, sighting_threshold: int = 2) -> None:
        self.confidence_threshold = confidence_threshold
        self.sighting_threshold = sighting_threshold

    def is_verified(self, confidence: float, corroborating_sightings: int) -> bool:
        """Return whether the incident is eligible for the dashboard."""
        return (
            confidence >= self.confidence_threshold
            or corroborating_sightings >= self.sighting_threshold
        )
