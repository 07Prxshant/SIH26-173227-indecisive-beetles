#!/usr/bin/env python3
"""
UrbanSense - Standalone YOLOv8 Pothole Video Inference Script with ByteTrack

Processes input MP4 video streams using YOLOv8 pothole detector and ByteTrack.
Generates frame-level tracked detection records containing:
  - frame_id
  - timestamp (UTC ISO 8601)
  - bbox (x1, y1, x2, y2)
  - confidence
  - class ("pothole")
  - track_id

Outputs JSON detection report, detection statistics, and optional annotated video.
Does not depend on Kafka or FastAPI.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.tracking.tracker import ByteTracker

CLASS_NAME = "pothole"


def generate_iso_timestamp(start_time: datetime.datetime, frame_id: int, fps: float) -> str:
    """Calculates UTC ISO 8601 timestamp string for a given frame index."""
    seconds_offset = frame_id / max(1.0, fps)
    frame_time = start_time + datetime.timedelta(seconds=seconds_offset)
    iso_str = frame_time.isoformat()
    if "+00:00" in iso_str:
        return iso_str.replace("+00:00", "Z")
    return iso_str + "Z" if not iso_str.endswith("Z") else iso_str


def run_mock_inference(
    video_path: Path,
    output_json: Path,
    output_video: Optional[Path] = None,
    conf_thres: float = 0.25,
    source_id: Optional[str] = None,
    fps: float = 30.0,
    total_frames: int = 150
) -> Dict[str, Any]:
    """
    Simulates video inference and ByteTrack association for testing environments.
    Generates structured frame-level pothole detections with stable track_ids.
    """
    start_time = datetime.datetime.now(datetime.timezone.utc)
    src_id = source_id or video_path.stem
    tracker = ByteTracker(track_thresh=conf_thres, low_thresh=0.1, max_time_lost=30)
    tracker.reset()

    detections = []
    frames_with_dets = set()
    conf_sum = 0.0

    # Simulated hit frames with 2 separate potholes (left side and right side)
    hit_frames = [15, 16, 17, 18, 45, 46, 47, 90, 91, 92, 93, 120, 121]

    for fid in range(total_frames):
        raw_dets = []
        if fid in hit_frames:
            # Pothole A (left side)
            raw_dets.append({
                "bbox": {"x1": 100.0 + (fid % 5) * 2.0, "y1": 250.0, "x2": 220.0 + (fid % 5) * 2.0, "y2": 330.0},
                "confidence": round(min(0.98, max(conf_thres, 0.75 + (fid % 4) * 0.05)), 4),
                "class": CLASS_NAME
            })
            # Pothole B (right side) on certain frames
            if fid in (45, 46, 47, 90, 91, 92, 93):
                raw_dets.append({
                    "bbox": {"x1": 400.0, "y1": 200.0 + (fid % 3) * 3.0, "x2": 520.0, "y2": 280.0 + (fid % 3) * 3.0},
                    "confidence": round(min(0.95, max(conf_thres, 0.70 + (fid % 3) * 0.06)), 4),
                    "class": CLASS_NAME
                })

        tracked_dets = tracker.update(raw_dets, fid)

        for det in tracked_dets:
            det["timestamp"] = generate_iso_timestamp(start_time, fid, fps)
            detections.append(det)
            frames_with_dets.add(fid)
            conf_sum += det["confidence"]

    avg_conf = round(conf_sum / max(1, len(detections)), 4) if detections else 0.0
    duration_sec = round(total_frames / max(1.0, fps), 2)

    stats = {
        "source_id": src_id,
        "video_path": str(video_path.resolve()),
        "fps": fps,
        "total_frames": total_frames,
        "duration_seconds": duration_sec,
        "total_detections": len(detections),
        "frames_with_detections": len(frames_with_dets),
        "avg_confidence": avg_conf,
        "detections": detections
    }

    # Write output JSON
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    # Optionally create stub annotated video file
    if output_video:
        output_video.parent.mkdir(parents=True, exist_ok=True)
        output_video.write_text(f"UrbanSense Mock Tracked Video - {src_id}\n", encoding="utf-8")

    return stats


def run_opencv_inference(
    video_path: Path,
    model_path: Path,
    output_json: Path,
    output_video: Optional[Path] = None,
    conf_thres: float = 0.25,
    imgsz: int = 640,
    device: str = "cpu",
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Runs actual YOLOv8 video inference with ByteTrack tracking."""
    try:
        import cv2  # type: ignore
        from ultralytics import YOLO  # type: ignore
    except ImportError as e:
        raise ImportError(f"Required package missing for live inference: {e}. Use --mock for mock execution.")

    if not video_path.exists():
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    print(f"Loading YOLOv8 model: {model_path}...")
    model = YOLO(str(model_path))

    tracker = ByteTracker(track_thresh=conf_thres, low_thresh=0.1, max_time_lost=30)
    tracker.reset()

    video_writer = None
    if output_video:
        output_video.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

    start_time = datetime.datetime.now(datetime.timezone.utc)
    src_id = source_id or video_path.stem

    detections = []
    frames_with_dets = set()
    conf_sum = 0.0
    frame_id = 0

    print(f"Processing video '{video_path.name}' ({total_frames} frames @ {fps:.1f} FPS with ByteTrack)...")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model.predict(frame, conf=conf_thres, imgsz=imgsz, device=device, verbose=False)
        raw_dets = []

        for res in results:
            for box in res.boxes:
                conf = round(float(box.conf[0].item()), 4)
                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = round(float(xyxy[0]), 1), round(float(xyxy[1]), 1), round(float(xyxy[2]), 1), round(float(xyxy[3]), 1)

                raw_dets.append({
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "confidence": conf,
                    "class": CLASS_NAME
                })

        tracked_dets = tracker.update(raw_dets, frame_id)

        for det in tracked_dets:
            det["timestamp"] = generate_iso_timestamp(start_time, frame_id, fps)
            detections.append(det)
            frames_with_dets.add(frame_id)
            conf_sum += float(det["confidence"])

            if video_writer is not None:
                bx = det["bbox"]
                bx_x1, bx_y1, bx_x2, bx_y2 = int(bx["x1"]), int(bx["y1"]), int(bx["x2"]), int(bx["y2"])
                cv2.rectangle(frame, (bx_x1, bx_y1), (bx_x2, bx_y2), (0, 0, 255), 2)
                cv2.putText(
                    frame,
                    f"ID:{det['track_id']} {det['confidence']:.2f}",
                    (bx_x1, max(15, bx_y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2
                )

        if video_writer is not None:
            video_writer.write(frame)

        frame_id += 1

    cap.release()
    if video_writer is not None:
        video_writer.release()

    avg_conf = round(conf_sum / max(1, len(detections)), 4) if detections else 0.0
    duration_sec = round(frame_id / max(1.0, fps), 2)

    stats = {
        "source_id": src_id,
        "video_path": str(video_path.resolve()),
        "fps": fps,
        "total_frames": frame_id,
        "duration_seconds": duration_sec,
        "total_detections": len(detections),
        "frames_with_detections": len(frames_with_dets),
        "avg_confidence": avg_conf,
        "detections": detections
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    return stats


def run_video_inference(
    video_path: Path,
    model_path: Path = Path("ml/models/best.pt"),
    output_json: Path = Path("ml/runs/detect/detections.json"),
    output_video: Optional[Path] = None,
    conf_thres: float = 0.25,
    imgsz: int = 640,
    device: str = "cpu",
    source_id: Optional[str] = None,
    mock: bool = False
) -> Dict[str, Any]:
    """Main inference interface function with ByteTrack tracking."""
    use_opencv = False
    if not mock:
        try:
            import cv2  # type: ignore
            import ultralytics  # type: ignore
            use_opencv = True
        except ImportError:
            use_opencv = False

    if use_opencv:
        return run_opencv_inference(
            video_path=video_path,
            model_path=model_path,
            output_json=output_json,
            output_video=output_video,
            conf_thres=conf_thres,
            imgsz=imgsz,
            device=device,
            source_id=source_id
        )
    else:
        return run_mock_inference(
            video_path=video_path,
            output_json=output_json,
            output_video=output_video,
            conf_thres=conf_thres,
            source_id=source_id
        )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="UrbanSense Standalone YOLOv8 Pothole Video Inference with ByteTrack")
    parser.add_argument("--video", type=Path, required=True, help="Path to input .mp4 video file")
    parser.add_argument("--model", type=Path, default=Path("ml/models/best.pt"), help="Path to trained YOLOv8 model weights (.pt)")
    parser.add_argument("--output-json", type=Path, default=Path("ml/runs/detect/detections.json"), help="Output path for JSON detection results")
    parser.add_argument("--output-video", type=Path, help="Optional output path for annotated video (.mp4)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default 0.25)")
    parser.add_argument("--imgsz", type=int, default=640, help="Target image size in pixels")
    parser.add_argument("--device", type=str, default="cpu", help="Device ('cpu', '0', etc.)")
    parser.add_argument("--source-id", type=str, help="Source video stream ID")
    parser.add_argument("--mock", action="store_true", help="Force mock inference engine for testing")

    args = parser.parse_args(argv)

    print("==================================================")
    print("  UrbanSense Pothole Video Inference + ByteTrack  ")
    print("==================================================")
    print(f"Input Video : {args.video}")
    print(f"Model Path  : {args.model}")

    stats = run_video_inference(
        video_path=args.video,
        model_path=args.model,
        output_json=args.output_json,
        output_video=args.output_video,
        conf_thres=args.conf,
        imgsz=args.imgsz,
        device=args.device,
        source_id=args.source_id,
        mock=args.mock
    )

    print("\n--- Tracked Detection Summary Statistics ---")
    print(f"  Source ID              : {stats['source_id']}")
    print(f"  Total Frames Processed : {stats['total_frames']}")
    print(f"  Duration               : {stats['duration_seconds']} sec")
    print(f"  Total Tracked Sightings: {stats['total_detections']}")
    print(f"  Frames with Detections : {stats['frames_with_detections']}")
    print(f"  Average Confidence     : {stats['avg_confidence']:.4f}")
    print(f"  JSON Results Saved To  : {args.output_json.resolve()}")
    if args.output_video:
        print(f"  Annotated Video Saved To: {args.output_video.resolve()}")
    print("--------------------------------------------")


if __name__ == "__main__":
    main()
