#!/usr/bin/env python3
"""
UrbanSense - Pothole Dataset Preparation Pipeline

Converts RDD2022 (PASCAL VOC XML) and custom YOLO format pothole datasets
into a standardized YOLOv8 single-class dataset structure.

Single-class mapping:
  0: pothole
"""

import argparse
import os
import random
import shutil
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Supported image extensions
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CLASS_NAME = "pothole"
CLASS_ID = 0

# RDD2022 specific class identifiers for potholes
RDD_POTHOLE_TAGS = {"d40", "pothole", "potholes", "0"}


def get_image_size(file_path: Path) -> Tuple[int, int]:
    """
    Reads image dimensions (width, height) using standard library byte parsing.
    Supports PNG and JPEG file formats.
    """
    with open(file_path, "rb") as f:
        head = f.read(32)

    # PNG format
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        w, h = struct.unpack(">II", head[16:24])
        return w, h

    # JPEG format
    if head.startswith(b"\xff\xd8"):
        with open(file_path, "rb") as f:
            f.seek(0)
            f.read(2)
            b = f.read(1)
            while b:
                while b != b"\xff":
                    b = f.read(1)
                while b == b"\xff":
                    b = f.read(1)
                b_ord = ord(b)
                if 0xC0 <= b_ord <= 0xC3:
                    f.read(3)
                    h, w = struct.unpack(">HH", f.read(4))
                    return w, h
                else:
                    len_bytes = f.read(2)
                    if len(len_bytes) < 2:
                        break
                    length = struct.unpack(">H", len_bytes)[0]
                    f.read(length - 2)
                b = f.read(1)

    # Fallback to default dimensions if unparseable header
    return 640, 640


def parse_xml_annotation(xml_path: Path, image_path: Path) -> List[str]:
    """
    Parses a PASCAL VOC XML annotation file (RDD2022 format) and extracts pothole bounding boxes.
    Converts coordinates [xmin, ymin, xmax, ymax] into YOLO format: [class_id, x_center, y_center, width, height].
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Extract image dimensions from XML or fallback to image file
    size_elem = root.find("size")
    if size_elem is not None and size_elem.find("width") is not None and size_elem.find("height") is not None:
        width = int(size_elem.find("width").text or 0)
        height = int(size_elem.find("height").text or 0)
    else:
        width, height = 0, 0

    if width <= 0 or height <= 0:
        width, height = get_image_size(image_path)

    if width <= 0 or height <= 0:
        return []

    yolo_rows = []
    for obj in root.findall("object"):
        name_elem = obj.find("name")
        if name_elem is None or not name_elem.text:
            continue

        obj_name = name_elem.text.strip().lower()
        # Check if the object is a pothole (RDD2022 code D40 or explicit pothole label)
        if obj_name not in RDD_POTHOLE_TAGS:
            continue

        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue

        try:
            xmin = float(bndbox.find("xmin").text)
            ymin = float(bndbox.find("ymin").text)
            xmax = float(bndbox.find("xmax").text)
            ymax = float(bndbox.find("ymax").text)
        except (ValueError, TypeError, AttributeError):
            continue

        # Convert to normalized YOLO format
        x_center = max(0.0, min(1.0, ((xmin + xmax) / 2.0) / width))
        y_center = max(0.0, min(1.0, ((ymin + ymax) / 2.0) / height))
        bbox_w = max(0.0, min(1.0, (xmax - xmin) / width))
        bbox_h = max(0.0, min(1.0, (ymax - ymin) / height))

        if bbox_w > 0 and bbox_h > 0:
            yolo_rows.append(f"{CLASS_ID} {x_center:.6f} {y_center:.6f} {bbox_w:.6f} {bbox_h:.6f}")

    return yolo_rows


def parse_yolo_annotation(txt_path: Path) -> List[str]:
    """
    Parses an existing YOLO text annotation file and remaps class IDs to single-class pothole (0).
    """
    if not txt_path.exists():
        return []

    yolo_rows = []
    lines = txt_path.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            # Force class ID to 0 for single-class pothole model
            _, x_center, y_center, bbox_w, bbox_h = parts[:5]
            yolo_rows.append(f"{CLASS_ID} {x_center} {y_center} {bbox_w} {bbox_h}")

    return yolo_rows


def discover_dataset_entries(source_dir: Path, fmt: str = "auto") -> List[Tuple[Path, List[str]]]:
    """
    Discovers image files and matches them with their annotations in XML or TXT format.
    """
    entries = []
    image_files = []

    for root, _, files in os.walk(source_dir):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                image_files.append(Path(root) / file)

    image_files.sort()

    for img_path in image_files:
        stem = img_path.stem
        parent = img_path.parent

        # Search locations for annotations
        possible_xmls = [
            parent / f"{stem}.xml",
            parent.parent / "annotations" / f"{stem}.xml",
            parent.parent / "labels" / f"{stem}.xml",
            source_dir / "annotations" / f"{stem}.xml",
            source_dir / "labels" / f"{stem}.xml",
        ]

        possible_txts = [
            parent / f"{stem}.txt",
            parent.parent / "labels" / f"{stem}.txt",
            parent.parent / "annotations" / f"{stem}.txt",
            source_dir / "labels" / f"{stem}.txt",
            source_dir / "annotations" / f"{stem}.txt",
        ]

        annotation_rows = []

        if fmt in ("rdd2022", "xml", "auto"):
            for xml_file in possible_xmls:
                if xml_file.exists():
                    annotation_rows = parse_xml_annotation(xml_file, img_path)
                    break

        if not annotation_rows and fmt in ("yolo", "txt", "auto"):
            for txt_file in possible_txts:
                if txt_file.exists():
                    annotation_rows = parse_yolo_annotation(txt_file)
                    break

        entries.append((img_path, annotation_rows))

    return entries


def prepare_dataset(
    source_dir: Path,
    output_dir: Path,
    fmt: str = "auto",
    ratios: Tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 42
) -> Dict[str, int]:
    """
    Prepares YOLOv8 single-class dataset with train/val/test splits and dataset.yaml configuration.
    """
    train_r, val_r, test_r = ratios
    total_r = train_r + val_r + test_r
    if abs(total_r - 1.0) > 1e-4:
        train_r, val_r, test_r = train_r / total_r, val_r / total_r, test_r / total_r

    entries = discover_dataset_entries(source_dir, fmt=fmt)
    if not entries:
        raise ValueError(f"No image files found in source directory: {source_dir}")

    # Shuffle deterministically
    random.seed(seed)
    random.shuffle(entries)

    n_total = len(entries)
    if n_total >= 3:
        n_train = max(1, min(n_total - 2, int(n_total * train_r)))
        n_val = max(1, min(n_total - n_train - 1, int(n_total * val_r)))
    elif n_total == 2:
        n_train, n_val = 1, 1
    else:
        n_train, n_val = 1, 0

    splits = {
        "train": entries[:n_train],
        "val": entries[n_train:n_train + n_val],
        "test": entries[n_train + n_val:]
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    counts = {}
    for split_name, split_entries in splits.items():
        img_dir = output_dir / "images" / split_name
        lbl_dir = output_dir / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for idx, (img_path, rows) in enumerate(split_entries):
            filename_base = f"{idx:06d}_{img_path.stem}"
            dest_img = img_dir / f"{filename_base}{img_path.suffix.lower()}"
            dest_lbl = lbl_dir / f"{filename_base}.txt"

            shutil.copy2(img_path, dest_img)
            dest_lbl.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")

        counts[split_name] = len(split_entries)

    # Generate dataset.yaml
    yaml_lines = [
        f"path: {output_dir.resolve().as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "",
        "names:",
        f"  {CLASS_ID}: {CLASS_NAME}",
        ""
    ]
    (output_dir / "dataset.yaml").write_text("\n".join(yaml_lines), encoding="utf-8")

    return counts


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="UrbanSense Pothole Dataset Preparation Script")
    parser.add_argument("--source", type=Path, required=True, help="Path to raw source dataset directory")
    parser.add_argument("--output", type=Path, required=True, help="Path to destination YOLO dataset directory")
    parser.add_argument("--format", choices=["auto", "rdd2022", "yolo"], default="auto", help="Source annotation format")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Test split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible splits")

    args = parser.parse_args(argv)

    counts = prepare_dataset(
        source_dir=args.source,
        output_dir=args.output,
        fmt=args.format,
        ratios=(args.train_ratio, args.val_ratio, args.test_ratio),
        seed=args.seed
    )

    print(f"Dataset preparation complete! Total processed: {sum(counts.values())}")
    print(f"Splits: Train={counts['train']}, Val={counts['val']}, Test={counts['test']}")
    print(f"Output directory: {args.output.resolve()}")
    print(f"YAML config: {(args.output / 'dataset.yaml').resolve()}")


if __name__ == "__main__":
    main()
