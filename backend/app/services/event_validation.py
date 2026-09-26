"""Validation of ML events against the shared UrbanSense JSON Schema contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EVENT_SCHEMA_PATH = REPOSITORY_ROOT / "contracts" / "event.schema.json"


class EventValidationError(ValueError):
    """Raised when an event does not satisfy the shared event contract."""


class EventContractValidator:
    """Load and apply the versioned pothole-event JSON Schema."""

    def __init__(self, schema_path: Path = EVENT_SCHEMA_PATH) -> None:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self._validator = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(self, event: Mapping[str, Any]) -> dict[str, Any]:
        """Return a plain event dictionary or raise an actionable validation error."""
        errors = sorted(self._validator.iter_errors(dict(event)), key=lambda item: list(item.path))
        if errors:
            details = "; ".join(error.message for error in errors)
            raise EventValidationError(details)
        return dict(event)
