#!/usr/bin/env python3
"""
UrbanSense - Pothole Dataset Validation Script

Validates YOLOv8 single-class pothole dataset structure, dataset.yaml config,
label bounding boxes, class mapping, and image-label file pairing.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
REQUIRED_CLASS_ID = 0
REQUIRED_CLASS_NAME = "pothole"


def parse_simple_yaml(yaml_path: Path) -> Dict[str, Any]:
    """
    Parses key YAML fields (path, train, val, test, names) without external dependencies.
    """
    lines = yaml_path.read_text(encoding="utf-8").splitlines()
    data: Dict[str, Any] = {"names": {}}
    in_names = False

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("names:"):
            in_names = True
            continue

        if in_names:
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                try:
                    data["names"][int(k.strip())] = v.strip().strip("'\"")
                except ValueError:
                    in_names = False

        if not in_names and ":" in stripped:
            k, v = stripped.split(":", 1)
            data[k.strip()] = v.strip().strip("'\"")

    return data


def validate_label_file(label_path: Path) -> Tuple[List[str], int]:
    """
    Validates a single YOLO label file.
    Returns a tuple of (errors_list, valid_box_count).
    """
    errors = []
    box_count = 0
    content = label_path.read_text(encoding="utf-8").strip()
    if not content:
        return errors, box_count

    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 5:
            errors.append(f"{label_path.name}:{idx} Invalid format, expected 5 columns, got {len(parts)}: '{line}'")
            continue

        try:
            class_id = int(parts[0])
            x_c = float(parts[1])
            y_c = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except ValueError:
            errors.append(f"{label_path.name}:{idx} Non-numeric values found: '{line}'")
            continue

        if class_id != REQUIRED_CLASS_ID:
            errors.append(f"{label_path.name}:{idx} Invalid class_id {class_id}, expected {REQUIRED_CLASS_ID} ({REQUIRED_CLASS_NAME})")

        if not (0.0 <= x_c <= 1.0 and 0.0 <= y_c <= 1.0):
            errors.append(f"{label_path.name}:{idx} Center coordinates out of bounds [0, 1]: ({x_c}, {y_c})")

        if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
            errors.append(f"{label_path.name}:{idx} Dimensions out of bounds (0, 1]: ({w}, {h})")

        xmin = x_c - (w / 2.0)
        xmax = x_c + (w / 2.0)
        ymin = y_c - (h / 2.0)
        ymax = y_c + (h / 2.0)

        if xmin < -0.05 or ymin < -0.05 or xmax > 1.05 or ymax > 1.05:
            errors.append(f"{label_path.name}:{idx} Box coordinates exceed image boundary: [{xmin:.2f}, {ymin:.2f}, {xmax:.2f}, {ymax:.2f}]")

        box_count += 1

    return errors, box_count


def validate_dataset(dataset_dir: Path) -> bool:
    """
    Validates complete YOLO single-class dataset structure and bounding boxes.
    """
    errors: List[str] = []
    warnings: List[str] = []
    stats: Dict[str, Dict[str, int]] = {}

    print(f"--- Validating YOLO Dataset: {dataset_dir.resolve()} ---")

    if not dataset_dir.exists() or not dataset_dir.is_dir():
        print(f"ERROR: Dataset directory does not exist: {dataset_dir}")
        return False

    yaml_path = dataset_dir / "dataset.yaml"
    if not yaml_path.exists():
        errors.append(f"Missing dataset.yaml configuration file at {yaml_path}")
    else:
        yaml_data = parse_simple_yaml(yaml_path)
        names = yaml_data.get("names", {})
        if REQUIRED_CLASS_ID not in names or names[REQUIRED_CLASS_ID] != REQUIRED_CLASS_NAME:
            errors.append(f"dataset.yaml must contain class mapping `{REQUIRED_CLASS_ID}: {REQUIRED_CLASS_NAME}`. Found: {names}")

    splits = ["train", "val", "test"]
    total_images = 0
    total_boxes = 0

    for split in splits:
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.exists():
            errors.append(f"Missing image directory for split '{split}': {img_dir}")
            continue
        if not lbl_dir.exists():
            errors.append(f"Missing label directory for split '{split}': {lbl_dir}")
            continue

        images = [f for f in img_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
        labels = [f for f in lbl_dir.iterdir() if f.is_file() and f.suffix.lower() == ".txt"]

        img_stems = {f.stem: f for f in images}
        lbl_stems = {f.stem: f for f in labels}

        missing_labels = set(img_stems.keys()) - set(lbl_stems.keys())
        missing_images = set(lbl_stems.keys()) - set(img_stems.keys())

        if missing_labels:
            warnings.append(f"Split '{split}': {len(missing_labels)} images have no corresponding label file (background images)")
        if missing_images:
            errors.append(f"Split '{split}': {len(missing_images)} label files have no corresponding image file")

        split_boxes = 0
        for stem, lbl_file in lbl_stems.items():
            lbl_errs, box_cnt = validate_label_file(lbl_file)
            errors.extend(lbl_errs)
            split_boxes += box_cnt

        stats[split] = {
            "images": len(images),
            "labels": len(labels),
            "boxes": split_boxes
        }

        total_images += len(images)
        total_boxes += split_boxes

    print("\n--- Dataset Summary ---")
    for split, sdata in stats.items():
        print(f"  Split '{split}': {sdata['images']} images, {sdata['labels']} label files, {sdata['boxes']} pothole bounding boxes")
    print(f"  Total Images: {total_images}")
    print(f"  Total Potholes Detected: {total_boxes}")

    if warnings:
        print(f"\n--- Warnings ({len(warnings)}) ---")
        for w in warnings[:10]:
            print(f"  WARNING: {w}")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for e in errors[:20]:
            print(f"  ERROR: {e}")
        print("\nDataset validation FAILED!")
        return False

    print("\nDataset validation SUCCESSFUL!")
    return True


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="UrbanSense YOLO Dataset Validation Script")
    parser.add_argument("--dataset", type=Path, default=Path("ml/datasets/potholes"), help="Path to YOLO dataset directory to validate")
    args = parser.parse_args(argv)

    success = validate_dataset(args.dataset)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
