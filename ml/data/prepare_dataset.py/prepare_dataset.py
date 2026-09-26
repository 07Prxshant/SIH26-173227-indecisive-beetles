 """Create a single-class YOLO dataset from RDD2022 or custom YOLO labels."""
from __future__ import annotations
import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".ppm"}


def yolo_labels(path):
    if path is None:
        return []
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        try:
            class_id = int(fields[0])
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: class id must be an integer") from exc
        if class_id == 0:
            rows.append(" ".join(["0", *fields[1:]]))
    return rows


def rdd_labels(path):
    root = ET.parse(path).getroot()
    size = root.find("size")
    if size is None:
        raise ValueError(f"Missing size element: {path}")
    width = float(size.findtext("width", "0"))
    height = float(size.findtext("height", "0"))
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions: {path}")
    rows = []
    for obj in root.findall("object"):
        if obj.findtext("name", "").strip().lower() not in {"d40", "pothole", "potholes"}:
            continue
        box = obj.find("bndbox")
        if box is None:
            raise ValueError(f"Missing pothole bounding box: {path}")
        xmin = max(0, float(box.findtext("xmin", "0")) - 1)
        ymin = max(0, float(box.findtext("ymin", "0")) - 1)
        xmax = min(width, float(box.findtext("xmax", "0")))
        ymax = min(height, float(box.findtext("ymax", "0")))
        if xmax <= xmin or ymax <= ymin:
            raise ValueError(f"Invalid pothole box: {path}")
        x = (xmin + xmax) / (2 * width)
        y = (ymin + ymax) / (2 * height)
        rows.append(f"0 {x:.6f} {y:.6f} {(xmax-xmin)/width:.6f} {(ymax-ymin)/height:.6f}")
    return rows


def locate_label(image, kind):
    for parent in image.parents:
        if parent.name.lower() == "images":
            base = parent.parent
            if kind == "rdd2022":
                label = base / "annotations" / "xmls" / f"{image.stem}.xml"
            else:
                label = base / "labels" / image.relative_to(parent).with_suffix(".txt")
            if label.is_file():
                return label
    label = image.with_suffix(".xml" if kind == "rdd2022" else ".txt")
    return label if label.is_file() else None


def prepare_dataset(source, output, input_format="auto", ratios=(.8, .1, .1), seed=42):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        raise ValueError(f"Source directory does not exist: {source}")
    if output == source or source in output.parents:
        raise ValueError("Output must not be the source or inside the source")
    if len(ratios) != 3 or any(r < 0 for r in ratios) or abs(sum(ratios)-1) > 1e-8:
        raise ValueError("Split ratios must be non-negative and sum to 1")
    images_root = source / "images" if (source / "images").is_dir() else source
    images = sorted(p for p in images_root.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    if not images:
        raise ValueError(f"No supported images under {source}")
    items = []
    for image in images:
        xml = locate_label(image, "rdd2022")
        kind = "rdd2022" if input_format == "rdd2022" or (input_format == "auto" and xml) else "yolo"
        label = xml if kind == "rdd2022" else locate_label(image, "yolo")
        if kind == "rdd2022" and label is None:
            raise ValueError(f"RDD annotation XML missing for {image}")
        rows = rdd_labels(label) if kind == "rdd2022" else yolo_labels(label)
        items.append((image, rows))
    random.Random(seed).shuffle(items)
    n = len(items)
    if n >= 3:
        n_train = max(1, min(n-2, int(n*ratios[0])))
        n_val = max(1, min(n-n_train-1, int(n*ratios[1])))
    elif n == 2:
        n_train, n_val = 1, 1
    else:
        n_train, n_val = 1, 0
    splits = {"train": items[:n_train], "val": items[n_train:n_train+n_val], "test": items[n_train+n_val:]}
    for split, entries in splits.items():
        image_dir, label_dir = output / "images" / split, output / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for index, (image, rows) in enumerate(entries):
            name = f"{index:06d}_{image.stem}"
            shutil.copy2(image, image_dir / f"{name}{image.suffix.lower()}")
            (label_dir / f"{name}.txt").write_text(chr(10).join(rows) + (chr(10) if rows else ""), encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    yaml = [f"path: {output.as_posix()}", "train: images/train", "val: images/val", "test: images/test", "names:", "  0: pothole"]
    (output / "dataset.yaml").write_text(chr(10).join(yaml) + chr(10), encoding="utf-8")
    return {key: len(value) for key, value in splits.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--format", choices=("auto", "rdd2022", "yolo"), default="auto")
    parser.add_argument("--train-ratio", type=float, default=.8)
    parser.add_argument("--val-ratio", type=float, default=.1)
    parser.add_argument("--test-ratio", type=float, default=.1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    counts = prepare_dataset(args.source, args.output, args.format, (args.train_ratio, args.val_ratio, args.test_ratio), args.seed)
    print(f"Prepared {sum(counts.values())} images: {counts}")


if __name__ == "__main__":
    main()
