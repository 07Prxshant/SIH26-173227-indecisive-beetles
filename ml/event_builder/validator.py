#!/usr/bin/env python3
"""
UrbanSense - Event Packet Validation Engine

Validates generated pothole sighting event dictionaries against the schema contract:
contracts/event.schema.json
"""

import json
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "contracts" / "event.schema.json"

ISO_8601_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


def validate_event(
    event: Dict[str, Any],
    schema_path: Optional[Path] = None
) -> Tuple[bool, List[str]]:
    """
    Validates an event packet against UrbanSense contract rules (contracts/event.schema.json).
    Returns a tuple of (is_valid: bool, errors: List[str]).
    """
    errors: List[str] = []

    # Check required fields
    required_fields = [
        "event_id", "class", "bbox", "confidence", "gps_lat",
        "gps_lon", "timestamp", "track_id", "source_id", "frame_id"
    ]
    for field in required_fields:
        if field not in event:
            errors.append(f"Missing required field: '{field}'")

    # Check additionalProperties restriction
    allowed_fields = set(required_fields) | {"image_ref", "frame_ref"}
    for key in event.keys():
        if key not in allowed_fields:
            errors.append(f"Unexpected additional field: '{key}'")

    # 1. event_id (uuid string)
    event_id = event.get("event_id")
    if not isinstance(event_id, str):
        errors.append("Field 'event_id' must be a string")
    else:
        try:
            uuid.UUID(event_id)
        except ValueError:
            errors.append(f"Field 'event_id' is not a valid UUID: '{event_id}'")

    # 2. class (const "pothole")
    cls_val = event.get("class")
    if cls_val != "pothole":
        errors.append(f"Field 'class' must be 'pothole', got '{cls_val}'")

    # 3. bbox ({x1, y1, x2, y2}, numbers >= 0)
    bbox = event.get("bbox")
    if not isinstance(bbox, dict):
        errors.append("Field 'bbox' must be an object")
    else:
        for bkey in ("x1", "y1", "x2", "y2"):
            if bkey not in bbox:
                errors.append(f"Bbox missing coordinate: '{bkey}'")
            elif not isinstance(bbox[bkey], (int, float)) or isinstance(bbox[bkey], bool):
                errors.append(f"Bbox coordinate '{bkey}' must be a number")
            elif bbox[bkey] < 0:
                errors.append(f"Bbox coordinate '{bkey}' must be >= 0: {bbox[bkey]}")

        # Additional bbox logic check
        if isinstance(bbox.get("x1"), (int, float)) and isinstance(bbox.get("x2"), (int, float)):
            if bbox["x2"] < bbox["x1"]:
                errors.append(f"Bbox x2 ({bbox['x2']}) cannot be less than x1 ({bbox['x1']})")
        if isinstance(bbox.get("y1"), (int, float)) and isinstance(bbox.get("y2"), (int, float)):
            if bbox["y2"] < bbox["y1"]:
                errors.append(f"Bbox y2 ({bbox['y2']}) cannot be less than y1 ({bbox['y1']})")

    # 4. confidence (number between 0 and 1)
    conf = event.get("confidence")
    if not isinstance(conf, (int, float)) or isinstance(conf, bool):
        errors.append("Field 'confidence' must be a number")
    elif not (0.0 <= conf <= 1.0):
        errors.append(f"Field 'confidence' must be between 0.0 and 1.0, got {conf}")

    # 5. gps_lat (number -90 to 90)
    lat = event.get("gps_lat")
    if not isinstance(lat, (int, float)) or isinstance(lat, bool):
        errors.append("Field 'gps_lat' must be a number")
    elif not (-90.0 <= lat <= 90.0):
        errors.append(f"Field 'gps_lat' must be between -90.0 and 90.0, got {lat}")

    # 6. gps_lon (number -180 to 180)
    lon = event.get("gps_lon")
    if not isinstance(lon, (int, float)) or isinstance(lon, bool):
        errors.append("Field 'gps_lon' must be a number")
    elif not (-180.0 <= lon <= 180.0):
        errors.append(f"Field 'gps_lon' must be between -180.0 and 180.0, got {lon}")

    # 7. timestamp (date-time string)
    ts = event.get("timestamp")
    if not isinstance(ts, str):
        errors.append("Field 'timestamp' must be a string")
    elif not ISO_8601_REGEX.match(ts):
        errors.append(f"Field 'timestamp' must be a valid ISO 8601 date-time string, got '{ts}'")

    # 8. track_id (string, minLength >= 1)
    track_id = event.get("track_id")
    if not isinstance(track_id, str):
        errors.append("Field 'track_id' must be a string")
    elif len(track_id) < 1:
        errors.append("Field 'track_id' cannot be empty")

    # 9. source_id (string, minLength >= 1)
    source_id = event.get("source_id")
    if not isinstance(source_id, str):
        errors.append("Field 'source_id' must be a string")
    elif len(source_id) < 1:
        errors.append("Field 'source_id' cannot be empty")

    # 10. frame_id (integer >= 0)
    frame_id = event.get("frame_id")
    if not isinstance(frame_id, int) or isinstance(frame_id, bool):
        errors.append("Field 'frame_id' must be an integer")
    elif frame_id < 0:
        errors.append(f"Field 'frame_id' must be >= 0, got {frame_id}")

    # Optional fields
    for opt_field in ("image_ref", "frame_ref"):
        if opt_field in event:
            val = event[opt_field]
            if not isinstance(val, str) or len(val) < 1:
                errors.append(f"Field '{opt_field}' must be a non-empty string")

    # Optional jsonschema check if package installed
    target_schema = schema_path or DEFAULT_SCHEMA_PATH
    if target_schema.exists():
        try:
            import jsonschema  # type: ignore
            schema_data = json.loads(target_schema.read_text(encoding="utf-8"))
            jsonschema.validate(instance=event, schema=schema_data)
        except ImportError:
            pass  # Handled by fallback rules above
        except Exception as e:
            errors.append(f"jsonschema validation failure: {e}")

    return len(errors) == 0, errors
