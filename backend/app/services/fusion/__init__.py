"""Composable services for turning raw pothole sightings into incidents."""

from app.services.fusion.confidence import ConfidenceScorer
from app.services.fusion.engine import FusionEngine, FusionOutcome
from app.services.fusion.persistence import SqlAlchemyFusionService
from app.services.fusion.spatial import PostGISSpatialGate, SpatialGate
from app.services.fusion.temporal import TemporalGate
from app.services.fusion.threshold import ThresholdFilter

__all__ = [
    "ConfidenceScorer",
    "FusionEngine",
    "FusionOutcome",
    "PostGISSpatialGate",
    "SqlAlchemyFusionService",
    "SpatialGate",
    "TemporalGate",
    "ThresholdFilter",
]
