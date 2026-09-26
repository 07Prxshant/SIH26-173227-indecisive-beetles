#!/usr/bin/env python3
"""
Unit tests for UrbanSense Local Replay Pipeline (ml/inference/replay.py).
"""

import tempfile
import unittest
from pathlib import Path

from ml.inference.replay import run_replay, main as replay_main


class TestReplayPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_path = Path(self.temp_dir.name) / "sample_test.mp4"
        self.video_path.write_text("dummy binary video content", encoding="utf-8")

        self.gps_path = Path(self.temp_dir.name) / "gps.csv"
        self.gps_path.write_text(
            "timestamp,latitude,longitude\n"
            "2026-09-27T10:00:00Z,37.7749,-122.4194\n"
            "2026-09-27T10:00:05Z,37.7755,-122.4180\n",
            encoding="utf-8"
        )
        self.output_jsonl = Path(self.temp_dir.name) / "events.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_replay_pipeline(self):
        summary = run_replay(
            video_path=self.video_path,
            gps_path=self.gps_path,
            broker="localhost:9092",
            topic="pothole-events",
            source_id="test_bus_route",
            mock_inference=True,
            dry_run_kafka=True,
            output_jsonl=self.output_jsonl
        )

        self.assertEqual(summary["source_id"], "test_bus_route")
        self.assertEqual(summary["topic"], "pothole-events")
        self.assertTrue(summary["events_generated"] > 0)
        self.assertEqual(summary["events_published"], summary["events_generated"])
        self.assertTrue(self.output_jsonl.exists())

    def test_replay_cli_module_invocation(self):
        replay_main([
            "--video", str(self.video_path),
            "--gps", str(self.gps_path),
            "--broker", "localhost:9092",
            "--topic", "pothole-events",
            "--source-id", "cli_test",
            "--mock-inference",
            "--dry-run-kafka",
            "--output-jsonl", str(self.output_jsonl)
        ])

        self.assertTrue(self.output_jsonl.exists())


if __name__ == "__main__":
    unittest.main()
