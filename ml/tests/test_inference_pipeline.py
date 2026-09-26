#!/usr/bin/env python3
"""
Unit tests for UrbanSense Standalone YOLOv8 Pothole Video Inference Pipeline.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ml.inference.detect import main as detect_main, run_video_inference


class TestInferencePipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.video_path = Path(self.temp_dir.name) / "sample_test.mp4"
        self.video_path.write_text("dummy video binary content", encoding="utf-8")
        self.output_json = Path(self.temp_dir.name) / "detections.json"
        self.output_video = Path(self.temp_dir.name) / "annotated.mp4"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_video_inference_mock_execution(self):
        stats = run_video_inference(
            video_path=self.video_path,
            output_json=self.output_json,
            output_video=self.output_video,
            conf_thres=0.25,
            source_id="test_bus_route",
            mock=True
        )

        self.assertEqual(stats["source_id"], "test_bus_route")
        self.assertTrue(self.output_json.exists())
        self.assertTrue(self.output_video.exists())
        self.assertTrue(stats["total_detections"] > 0)
        self.assertTrue(stats["frames_with_detections"] > 0)
        self.assertTrue(stats["avg_confidence"] > 0.0)

        # Validate JSON content schema
        content = json.loads(self.output_json.read_text(encoding="utf-8"))
        self.assertIn("detections", content)
        detections = content["detections"]
        self.assertTrue(len(detections) > 0)

        sample_det = detections[0]
        self.assertIn("frame_id", sample_det)
        self.assertIn("timestamp", sample_det)
        self.assertIn("bbox", sample_det)
        self.assertIn("confidence", sample_det)
        self.assertEqual(sample_det["class"], "pothole")

        bbox = sample_det["bbox"]
        self.assertIn("x1", bbox)
        self.assertIn("y1", bbox)
        self.assertIn("x2", bbox)
        self.assertIn("y2", bbox)
        self.assertTrue(bbox["x2"] > bbox["x1"])
        self.assertTrue(bbox["y2"] > bbox["y1"])

    def test_detect_cli(self):
        detect_main([
            "--video", str(self.video_path),
            "--output-json", str(self.output_json),
            "--output-video", str(self.output_video),
            "--conf", "0.3",
            "--mock"
        ])

        self.assertTrue(self.output_json.exists())
        self.assertTrue(self.output_video.exists())


if __name__ == "__main__":
    unittest.main()
