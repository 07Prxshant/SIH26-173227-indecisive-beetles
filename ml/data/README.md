# UrbanSense ML Pothole Dataset Pipeline

This directory contains scripts and guidelines for preparing and validating single-class YOLOv8 pothole datasets for the **UrbanSense Pothole Detection MVP**.

---

## Class Mapping Standard

All detection models and annotations use the single-class target specification:

| Class ID | Class Name | Description |
| :--- | :--- | :--- |
| **`0`** | **`pothole`** | Road pothole or severe surface degradation |

---

## Dataset Directory Structure

Developers should place raw and processed dataset files in the following locations (these directories are git-ignored):

```text
SIH26-indecisive-beetles/
├── data/
│   ├── raw/                 # Put raw downloaded datasets here (e.g. RDD2022)
│   └── sample/              # Synthetic/sample fixture datasets for tests
└── ml/
    ├── data/
    │   ├── prepare_dataset.py # Converts RDD2022/YOLO annotations into YOLOv8 dataset
    │   └── README.md          # Dataset documentation
    ├── datasets/
    │   └── potholes/          # Prepared YOLO format dataset (images, labels, dataset.yaml)
    └── scripts/
        └── validate_dataset.py # Validates dataset format, bounding boxes, and splits
```

> [!IMPORTANT]
> **Git Rules**: Never commit large raw images or video datasets to Git. Raw datasets under `data/raw/` and prepared datasets under `ml/datasets/` are excluded by `.gitignore`.

---

## Supported Source Formats

1. **RDD2022 (Road Damage Detection 2022)**:
   - PASCAL VOC style XML files containing `<object>` entries with `<name>D40</name>` or `<name>pothole</name>`.
   - Bounding boxes (`xmin`, `ymin`, `xmax`, `ymax`) are automatically converted to normalized YOLO coordinates.
2. **Custom / YOLO Format**:
   - `.txt` label files containing normalized YOLO bounding boxes.
   - Class IDs are mapped automatically to `0: pothole`.

---

## Usage Instructions

### 1. Prepare Dataset

Run `prepare_dataset.py` to convert raw images and annotations into the YOLO split structure:

```bash
python ml/data/prepare_dataset.py \
  --source data/raw/rdd2022 \
  --output ml/datasets/potholes \
  --format auto \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1 \
  --seed 42
```

### 2. Validate Dataset

Run `validate_dataset.py` to inspect bounding boxes, class mappings, file pairing, and summary statistics:

```bash
python ml/scripts/validate_dataset.py --dataset ml/datasets/potholes
```

---

## Generated YOLO Structure (`ml/datasets/potholes/`)

```text
ml/datasets/potholes/
├── dataset.yaml
├── images/
│   ├── train/
│   ├── val/
│   └── test/
└── labels/
    ├── train/
    ├── val/
    └── test/
```

### `dataset.yaml` Example

```yaml
path: /path/to/ml/datasets/potholes
train: images/train
val: images/val
test: images/test

names:
  0: pothole
```
