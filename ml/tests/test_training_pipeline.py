#!/usr/bin/env python3
"""
Unit tests for UrbanSense YOLOv8 Training and Evaluation Pipeline.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ml.config.loader import load_train_config, parse_simple_yaml_config
from ml.training.train import main as train_main
from ml.training.evaluate import main as eval_main, run_mock_evaluation


class TestTrainingPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name) / "runs"
        self.config_yaml = Path(self.temp_dir.name) / "custom_config.yaml"

        yaml_content = """
data: ml/datasets/potholes/dataset.yaml
model: yolov8n.pt
epochs: 2
imgsz: 320
batch: 4
device: cpu
seed: 123
"""
        self.config_yaml.write_text(yaml_content, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_config_loader(self):
        config = parse_simple_yaml_config(self.config_yaml)
        self.assertEqual(config["epochs"], 2)
        self.assertEqual(config["imgsz"], 320)
        self.assertEqual(config["batch"], 4)
        self.assertEqual(config["device"], "cpu")
        self.assertEqual(config["seed"], 123)

    def test_train_mock_execution(self):
        run_name = "test_run"
        train_main([
            "--mock",
            "--epochs", "2",
            "--imgsz", "320",
            "--batch", "4",
            "--project", str(self.project_dir),
            "--name", run_name,
            "--seed", "42"
        ])

        run_dir = self.project_dir / run_name
        self.assertTrue(run_dir.exists())
        self.assertTrue((run_dir / "weights" / "best.pt").exists())
        self.assertTrue((run_dir / "metrics.json").exists())
        self.assertTrue((run_dir / "training_summary.json").exists())

        summary = json.loads((run_dir / "training_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["mode"], "mock")
        self.assertIn("best_mAP50", summary)

    def test_evaluate_mock_execution(self):
        dummy_model = Path(self.temp_dir.name) / "best.pt"
        dummy_model.write_text("dummy model weights", encoding="utf-8")

        eval_main([
            "--mock",
            "--model", str(dummy_model),
            "--split", "val",
            "--imgsz", "320"
        ])

        eval_json = Path(self.temp_dir.name) / "eval_results_val.json"
        self.assertTrue(eval_json.exists())

        metrics = json.loads(eval_json.read_text(encoding="utf-8"))
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("mAP50", metrics)
        self.assertIn("mAP50-95", metrics)
        self.assertEqual(metrics["class"], "pothole")


if __name__ == "__main__":
    unittest.main()
