#!/usr/bin/env python3
"""
UrbanSense - Pothole Event Builder

Constructs GPS-synchronized pothole sighting event packets for newly confirmed tracks
and validates them against /contracts/event.schema.json before exporting to JSONL.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.gps.synchronizer import GPSSynchronizer, parse_gps_file
from ml.event_builder.validator import validate_event


class PotholeEventBuilder:
    """
    Builds and validates schema-compliant event packets from tracked detections and GPS samples.
    """

    def __init__(
        self,
        source_id: str,
        gps_synchronizer: Optional[GPSSynchronizer] = None,
        offset_seconds: float = 0.0,
        only_new_tracks: bool = True,
        user_location: Optional[Tuple[float, float]] = None
    ):
        self.source_id = source_id
        self.gps_synchronizer = gps_synchronizer
        self.offset_seconds = offset_seconds
        self.only_new_tracks = only_new_tracks
        self.user_location = user_location
        self.seen_tracks: Set[str] = set()

    def reset(self) -> None:
        """Resets tracked identity state."""
        self.seen_tracks.clear()

    def build_event(
        self,
        detection: Dict[str, Any],
        source_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Processes a single tracked detection dictionary and constructs an event packet
        for newly confirmed tracks (or all sightings if only_new_tracks is False).
        """
        track_id = str(detection["track_id"])

        if self.only_new_tracks:
            if track_id in self.seen_tracks:
                return None
            self.seen_tracks.add(track_id)

        # Retrieve GPS coordinates
        default_coords = self.user_location if self.user_location else (12.97530, 77.60210)
        if self.gps_synchronizer and not self.gps_synchronizer.is_empty():
            gps_lat, gps_lon = self.gps_synchronizer.get_gps_at_time(
                target_time=detection["timestamp"],
                offset_seconds=self.offset_seconds,
                default_coords=default_coords
            )
        elif self.user_location:
            gps_lat, gps_lon = self.user_location
        else:
            gps_lat = float(detection.get("gps_lat", 12.97530))
            gps_lon = float(detection.get("gps_lon", 77.60210))

        # Format timestamp to UTC ISO 8601
        ts_str = str(detection["timestamp"])
        if not ts_str.endswith("Z") and "+00:00" not in ts_str and "-" not in ts_str[-6:]:
            ts_str += "Z"

        bbox = detection["bbox"]
        event_packet = {
            "event_id": str(uuid.uuid4()),
            "class": "pothole",
            "bbox": {
                "x1": round(float(bbox["x1"]), 2),
                "y1": round(float(bbox["y1"]), 2),
                "x2": round(float(bbox["x2"]), 2),
                "y2": round(float(bbox["y2"]), 2)
            },
            "confidence": round(float(detection["confidence"]), 4),
            "gps_lat": round(float(gps_lat), 6),
            "gps_lon": round(float(gps_lon), 6),
            "timestamp": ts_str,
            "track_id": track_id,
            "source_id": str(source_id or self.source_id),
            "frame_id": int(detection["frame_id"])
        }

        if "frame_ref" in detection:
            event_packet["frame_ref"] = str(detection["frame_ref"])
        elif "image_ref" in detection:
            event_packet["image_ref"] = str(detection["image_ref"])

        # Validate against schema contract
        is_valid, errors = validate_event(event_packet)
        if not is_valid:
            raise ValueError(f"Generated event packet failed contract validation: {errors}")

        return event_packet

    def process_detections(
        self,
        detections: List[Dict[str, Any]],
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Processes a list of frame-level detections into event packets."""
        events = []
        for det in detections:
            evt = self.build_event(det, source_id=source_id)
            if evt is not None:
                events.append(evt)
        return events


def build_events_from_files(
    detections_json_path: Path,
    gps_file_path: Optional[Path],
    output_jsonl_path: Path,
    source_id: Optional[str] = None,
    offset_seconds: float = 0.0,
    only_new_tracks: bool = True
) -> List[Dict[str, Any]]:
    """
    Reads detection results JSON and optional GPS trace file (CSV/GPX),
    synchronizes coordinates, builds event packets, and writes to JSONL.
    """
    if not detections_json_path.exists():
        raise FileNotFoundError(f"Detections JSON file not found: {detections_json_path}")

    raw_data = json.loads(detections_json_path.read_text(encoding="utf-8"))
    src_id = source_id or raw_data.get("source_id", "default_source")

    detections = raw_data.get("detections", []) if isinstance(raw_data, dict) else raw_data

    gps_sync = None
    if gps_file_path and gps_file_path.exists():
        samples = parse_gps_file(gps_file_path)
        gps_sync = GPSSynchronizer(samples)

    builder = PotholeEventBuilder(
        source_id=src_id,
        gps_synchronizer=gps_sync,
        offset_seconds=offset_seconds,
        only_new_tracks=only_new_tracks
    )

    events = builder.process_detections(detections, source_id=src_id)

    # Write events to JSONL output
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return events


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="UrbanSense - Build GPS Synchronized Pothole Events (JSONL)"
    )
    parser.add_argument("--detections", type=Path, required=True, help="Path to input detections JSON file")
    parser.add_argument("--gps", type=Path, help="Path to input GPS trace file (.csv or .gpx)")
    parser.add_argument("--output-jsonl", type=Path, default=Path("ml/runs/events/events.jsonl"), help="Output path for JSONL events")
    parser.add_argument("--source-id", type=str, help="Source identifier")
    parser.add_argument("--offset-sec", type=float, default=0.0, help="Video to GPS offset in seconds")
    parser.add_argument("--all-sightings", action="store_true", help="Emit events for all frame sightings instead of only newly confirmed tracks")

    args = parser.parse_args(argv)

    print("==================================================")
    print("   UrbanSense Pothole Event Builder (GPS Sync)    ")
    print("==================================================")

    events = build_events_from_files(
        detections_json_path=args.detections,
        gps_file_path=args.gps,
        output_jsonl_path=args.output_jsonl,
        source_id=args.source_id,
        offset_seconds=args.offset_sec,
        only_new_tracks=not args.all_sightings
    )

    print(f"Successfully generated {len(events)} event packets.")
    print(f"Output saved to: {args.output_jsonl.resolve()}")


if __name__ == "__main__":
    main()
