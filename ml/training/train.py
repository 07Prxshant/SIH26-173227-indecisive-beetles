#!/usr/bin/env python3
"""
UrbanSense - YOLOv8 Pothole Training Script

Trains a single-class YOLOv8 model for pothole detection with configurable
hyperparameters, metrics logging, reproducible seeding, and local artifact management.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.config.loader import load_train_config


def set_reproducible_seed(seed: int) -> None:
    """Sets random seed across standard library and ML frameworks if installed."""
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass

    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def run_mock_training(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Simulates a YOLOv8 training loop when running in mock mode or when
    ultralytics package is absent. Logs metrics and creates model artifacts.
    """
    print(f"[MOCK TRAINER] Initializing simulated YOLOv8 training for '{args.name}'...")
    print(f"[MOCK TRAINER] Data: {args.data} | Epochs: {args.epochs} | ImgSz: {args.imgsz} | Batch: {args.batch} | Device: {args.device}")

    run_dir = Path(args.project) / args.name
    weights_dir = run_dir / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    history = []
    best_map50 = 0.0

    for epoch in range(1, args.epochs + 1):
        # Simulate realistic metric progression
        progress = epoch / max(1, args.epochs)
        train_loss = max(0.01, 0.15 * (1.0 - 0.8 * progress))
        val_loss = max(0.02, 0.18 * (1.0 - 0.75 * progress))
        precision = min(0.95, 0.50 + 0.42 * progress)
        recall = min(0.92, 0.45 + 0.44 * progress)
        map50 = min(0.94, 0.48 + 0.44 * progress)
        map50_95 = min(0.72, 0.30 + 0.40 * progress)

        if map50 > best_map50:
            best_map50 = map50

        metrics_epoch = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "mAP50": round(map50, 4),
            "mAP50-95": round(map50_95, 4),
        }
        history.append(metrics_epoch)

    # Write dummy weight files
    best_pt = weights_dir / "best.pt"
    last_pt = weights_dir / "last.pt"
    best_pt.write_text(f"UrbanSense Mock YOLOv8 Weights - best.pt - mAP50: {best_map50:.4f}\n", encoding="utf-8")
    last_pt.write_text("UrbanSense Mock YOLOv8 Weights - last.pt\n", encoding="utf-8")

    final_metrics = history[-1]
    summary = {
        "status": "success",
        "mode": "mock",
        "model_type": args.model,
        "epochs_completed": args.epochs,
        "best_mAP50": round(best_map50, 4),
        "final_metrics": final_metrics,
        "artifacts": {
            "weights_dir": str(weights_dir.resolve()),
            "best_model": str(best_pt.resolve()),
            "last_model": str(last_pt.resolve()),
        }
    }

    (run_dir / "metrics.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    (run_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


def run_ultralytics_training(args: argparse.Namespace) -> Dict[str, Any]:
    """Runs actual YOLOv8 training using Ultralytics framework."""
    from ultralytics import YOLO

    print(f"Loading base YOLOv8 model: {args.model}...")
    model = YOLO(args.model)

    print(f"Starting training run '{args.name}' on device '{args.device}'...")
    results = model.train(
        data=str(Path(args.data).resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        seed=args.seed,
        project=args.project,
        name=args.name,
        single_cls=True,
        exist_ok=True,
        workers=args.workers
    )

    run_dir = Path(args.project) / args.name
    best_pt = run_dir / "weights" / "best.pt"
    last_pt = run_dir / "weights" / "last.pt"

    summary = {
        "status": "success",
        "mode": "ultralytics",
        "model_type": args.model,
        "epochs_completed": args.epochs,
        "artifacts": {
            "run_dir": str(run_dir.resolve()),
            "best_model": str(best_pt.resolve()) if best_pt.exists() else None,
            "last_model": str(last_pt.resolve()) if last_pt.exists() else None,
        }
    }

    (run_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: Optional[list] = None) -> None:
    config_defaults = load_train_config()

    parser = argparse.ArgumentParser(description="UrbanSense YOLOv8 Single-Class Pothole Training Pipeline")
    parser.add_argument("--config", type=Path, help="Path to training configuration YAML file")
    parser.add_argument("--data", type=str, default=config_defaults.get("data", "ml/datasets/potholes/dataset.yaml"), help="Path to dataset.yaml")
    parser.add_argument("--model", type=str, default=config_defaults.get("model", "yolov8n.pt"), help="Base YOLOv8 model (yolov8n.pt, yolov8s.pt, etc.)")
    parser.add_argument("--epochs", type=int, default=config_defaults.get("epochs", 50), help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=config_defaults.get("imgsz", 640), help="Target image size in pixels")
    parser.add_argument("--batch", type=int, default=config_defaults.get("batch", 16), help="Batch size")
    parser.add_argument("--device", type=str, default=config_defaults.get("device", "cpu"), help="CUDA device ('0', 'cpu', etc.)")
    parser.add_argument("--seed", type=int, default=config_defaults.get("seed", 42), help="Random seed for reproducibility")
    parser.add_argument("--workers", type=int, default=config_defaults.get("workers", 4), help="Number of dataloader workers")
    parser.add_argument("--project", type=str, default=config_defaults.get("project", "ml/runs"), help="Output runs directory")
    parser.add_argument("--name", type=str, default=config_defaults.get("name", "pothole_yolov8n"), help="Training run name")
    parser.add_argument("--mock", action="store_true", help="Force mock training loop execution for testing")

    args = parser.parse_args(argv)

    if args.config:
        file_config = load_train_config(args.config)
        for k, v in file_config.items():
            if hasattr(args, k) and getattr(args, k) is None:
                setattr(args, k, v)

    set_reproducible_seed(args.seed)

    print("==================================================")
    print("   UrbanSense YOLOv8 Pothole Training Pipeline    ")
    print("==================================================")

    use_ultralytics = False
    if not args.mock:
        try:
            import ultralytics
            use_ultralytics = True
        except ImportError:
            print("Notice: 'ultralytics' package not found in current Python environment.")
            print("Falling back to simulated/mock training pipeline.")
            use_ultralytics = False

    if use_ultralytics:
        summary = run_ultralytics_training(args)
    else:
        summary = run_mock_training(args)

    print("\n--- Training Complete ---")
    print(f"Run Summary: {json.dumps(summary, indent=2)}")
    print("\nLocal Artifact Notice:")
    print("To store your trained weights locally for runtime inference, copy the best model to ml/models/:")
    print(f"  cp {summary['artifacts']['best_model']} ml/models/best.pt")


if __name__ == "__main__":
    main()
