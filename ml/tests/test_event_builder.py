#!/usr/bin/env python3
"""
Unit tests for UrbanSense Pothole Event Builder & Contract Validator (ml/event_builder).
"""

import json
import tempfile
import unittest
import uuid
from pathlib import Path

from ml.gps.synchronizer import GPSSample, GPSSynchronizer
from ml.event_builder.builder import PotholeEventBuilder, build_events_from_files
from ml.event_builder.validator import validate_event, DEFAULT_SCHEMA_PATH


class TestEventBuilder(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_jsonl = Path(self.temp_dir.name) / "events.jsonl"
        self.detections_json = Path(self.temp_dir.name) / "detections.json"

        # Mock sample detections
        self.sample_detections = [
            {
                "frame_id": 15,
                "timestamp": "2026-09-27T10:00:00.500000Z",
                "bbox": {"x1": 100.0, "y1": 250.0, "x2": 220.0, "y2": 330.0},
                "confidence": 0.87,
                "class": "pothole",
                "track_id": "1"
            },
            {
                "frame_id": 16,
                "timestamp": "2026-09-27T10:00:00.533333Z",
                "bbox": {"x1": 102.0, "y1": 250.0, "x2": 222.0, "y2": 330.0},
                "confidence": 0.89,
                "class": "pothole",
                "track_id": "1"  # Same track (should be skipped when only_new_tracks=True)
            },
            {
                "frame_id": 45,
                "timestamp": "2026-09-27T10:00:01.500000Z",
                "bbox": {"x1": 400.0, "y1": 200.0, "x2": 520.0, "y2": 280.0},
                "confidence": 0.82,
                "class": "pothole",
                "track_id": "2"  # New track
            }
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_schema_contract_validator(self):
        valid_event = {
            "event_id": str(uuid.uuid4()),
            "class": "pothole",
            "bbox": {"x1": 100.0, "y1": 250.0, "x2": 220.0, "y2": 330.0},
            "confidence": 0.87,
            "gps_lat": 37.7749,
            "gps_lon": -122.4194,
            "timestamp": "2026-09-27T10:00:00Z",
            "track_id": "1",
            "source_id": "bus_route_42",
            "frame_id": 15
        }

        is_valid, errors = validate_event(valid_event, schema_path=DEFAULT_SCHEMA_PATH)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)

        # Invalid event (missing field & invalid class)
        invalid_event = valid_event.copy()
        invalid_event["class"] = "crack"  # Must be 'pothole'
        del invalid_event["gps_lat"]

        is_valid, errors = validate_event(invalid_event, schema_path=DEFAULT_SCHEMA_PATH)
        self.assertFalse(is_valid)
        self.assertTrue(any("pothole" in e for e in errors))
        self.assertTrue(any("gps_lat" in e for e in errors))

    def test_new_tracks_event_generation(self):
        builder = PotholeEventBuilder(
            source_id="camera_01",
            only_new_tracks=True
        )

        events = builder.process_detections(self.sample_detections)

        # Expected 2 events (track_id "1" on frame 15, track_id "2" on frame 45)
        # Frame 16 (track_id "1") should be omitted as duplicate track
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["track_id"], "1")
        self.assertEqual(events[0]["frame_id"], 15)
        self.assertEqual(events[1]["track_id"], "2")
        self.assertEqual(events[1]["frame_id"], 45)

    def test_all_sightings_event_generation(self):
        builder = PotholeEventBuilder(
            source_id="camera_01",
            only_new_tracks=False
        )

        events = builder.process_detections(self.sample_detections)
        self.assertEqual(len(events), 3)

    def test_build_events_from_files_and_jsonl_output(self):
        # Write mock detections JSON
        det_data = {
            "source_id": "test_stream",
            "detections": self.sample_detections
        }
        self.detections_json.write_text(json.dumps(det_data), encoding="utf-8")

        # Write mock GPS CSV
        gps_csv = Path(self.temp_dir.name) / "gps.csv"
        gps_csv.write_text(
            "timestamp,latitude,longitude\n"
            "2026-09-27T10:00:00.500000Z,37.7749,-122.4194\n"
            "2026-09-27T10:00:01.500000Z,37.7755,-122.4180\n",
            encoding="utf-8"
        )

        events = build_events_from_files(
            detections_json_path=self.detections_json,
            gps_file_path=gps_csv,
            output_jsonl_path=self.output_jsonl,
            source_id="test_stream",
            only_new_tracks=True
        )

        self.assertEqual(len(events), 2)
        self.assertTrue(self.output_jsonl.exists())

        # Verify JSONL lines
        lines = [line.strip() for line in self.output_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)

        evt1 = json.loads(lines[0])
        self.assertEqual(evt1["source_id"], "test_stream")
        self.assertEqual(evt1["class"], "pothole")
        self.assertAlmostEqual(evt1["gps_lat"], 37.7749)
        self.assertAlmostEqual(evt1["gps_lon"], -122.4194)

        # Validate each line against schema contract
        for line in lines:
            evt_obj = json.loads(line)
            valid, errs = validate_event(evt_obj, schema_path=DEFAULT_SCHEMA_PATH)
            self.assertTrue(valid, f"JSONL line contract validation error: {errs}")


if __name__ == "__main__":
    unittest.main()
