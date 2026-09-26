# UrbanSense YOLOv8 Pothole Training Pipeline

This directory provides the training and evaluation framework for training a single-class (`0: pothole`) YOLOv8 object detector for the **UrbanSense Pothole Detection MVP**.

---

## Configuration

Training defaults are defined in [`ml/config/train_config.yaml`](../config/train_config.yaml):

```yaml
data: ml/datasets/potholes/dataset.yaml
model: yolov8n.pt
epochs: 50
imgsz: 640
batch: 16
device: cpu
seed: 42
workers: 4
project: ml/runs
name: pothole_yolov8n
single_cls: true
```

All parameters can be overridden via command-line arguments.

---

## 1. Train Model

Run `train.py` from the root directory:

```bash
python ml/training/train.py \
  --data ml/datasets/potholes/dataset.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 16 \
  --device cpu \
  --seed 42 \
  --name pothole_yolov8n
```

### Storing Model Weights Locally

Trained model weights are output to `ml/runs/pothole_yolov8n/weights/best.pt`.

> [!IMPORTANT]
> **Git Policy**: Never commit large model binary files (`*.pt`, `*.onnx`, `*.engine`) to Git repository history. The `ml/models/` and `ml/runs/` directories are git-ignored.

To prepare a trained model for local backend/inference execution, copy the best weights to `ml/models/`:

```bash
cp ml/runs/pothole_yolov8n/weights/best.pt ml/models/best.pt
```

---

## 2. Evaluate Model

Run `evaluate.py` to calculate test/validation metrics:

```bash
python ml/training/evaluate.py \
  --model ml/models/best.pt \
  --data ml/datasets/potholes/dataset.yaml \
  --split val \
  --imgsz 640
```

### Metrics Reported

- **Precision**: Ratio of true pothole detections over total predicted detections.
- **Recall**: Ratio of true pothole detections over total ground truth potholes.
- **mAP50**: Mean Average Precision at IoU threshold of 0.50.
- **mAP50-95**: Mean Average Precision averaged across IoU thresholds from 0.50 to 0.95.
