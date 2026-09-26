#!/usr/bin/env python3
"""
Unit tests for UrbanSense Pothole Dataset Pipeline (preparation and validation).
"""

import tempfile
import unittest
from pathlib import Path

from ml.data.prepare_dataset import prepare_dataset, get_image_size, parse_xml_annotation, parse_yolo_annotation
from ml.scripts.validate_dataset import validate_dataset, validate_label_file


class TestDatasetPipeline(unittest.TestCase):

    def setUp(self):
        self.sample_rdd_dir = Path("data/sample/rdd2022")
        self.sample_yolo_dir = Path("data/sample/yolo")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "potholes"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_image_size_parser(self):
        sample_img = self.sample_rdd_dir / "sample_rdd_01.png"
        width, height = get_image_size(sample_img)
        self.assertEqual(width, 100)
        self.assertEqual(height, 100)

    def test_parse_rdd_xml_annotation(self):
        xml_file = self.sample_rdd_dir / "sample_rdd_01.xml"
        img_file = self.sample_rdd_dir / "sample_rdd_01.png"
        rows = parse_xml_annotation(xml_file, img_file)
        self.assertTrue(len(rows) >= 1)
        # Class 0, x_center, y_center, width, height
        parts = rows[0].split()
        self.assertEqual(parts[0], "0")
        self.assertEqual(len(parts), 5)

    def test_prepare_dataset_rdd(self):
        counts = prepare_dataset(
            source_dir=self.sample_rdd_dir,
            output_dir=self.output_dir,
            fmt="rdd2022",
            ratios=(0.6, 0.2, 0.2),
            seed=42
        )
        self.assertEqual(sum(counts.values()), 3)
        self.assertTrue((self.output_dir / "dataset.yaml").exists())
        self.assertTrue((self.output_dir / "images" / "train").exists())
        self.assertTrue((self.output_dir / "labels" / "train").exists())

    def test_prepare_dataset_yolo(self):
        counts = prepare_dataset(
            source_dir=self.sample_yolo_dir,
            output_dir=self.output_dir,
            fmt="yolo",
            ratios=(0.6, 0.2, 0.2),
            seed=42
        )
        self.assertEqual(sum(counts.values()), 3)
        self.assertTrue((self.output_dir / "dataset.yaml").exists())

    def test_validate_prepared_dataset(self):
        prepare_dataset(
            source_dir=self.sample_rdd_dir,
            output_dir=self.output_dir,
            fmt="auto",
            ratios=(0.6, 0.2, 0.2),
            seed=42
        )
        is_valid = validate_dataset(self.output_dir)
        self.assertTrue(is_valid)

    def test_validate_label_file_invalid_class(self):
        lbl_file = Path(self.temp_dir.name) / "invalid.txt"
        lbl_file.write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")
        errors, box_cnt = validate_label_file(lbl_file)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Invalid class_id 1", errors[0])

    def test_validate_label_file_out_of_bounds(self):
        lbl_file = Path(self.temp_dir.name) / "out_of_bounds.txt"
        lbl_file.write_text("0 1.5 0.5 0.2 0.2\n", encoding="utf-8")
        errors, box_cnt = validate_label_file(lbl_file)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Center coordinates out of bounds", errors[0])


if __name__ == "__main__":
    unittest.main()
