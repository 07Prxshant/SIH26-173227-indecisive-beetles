# UrbanSense Pothole Video Inference Module

This directory provides standalone YOLOv8 video inference for detecting potholes from input `.mp4` video files.

---

## Output Detection Schema

The inference script processes each frame and outputs structured JSON detection objects matching system standards:

```json
{
  "source_id": "bus_route_04",
  "video_path": "/path/to/bus_route_04.mp4",
  "fps": 30.0,
  "total_frames": 300,
  "duration_seconds": 10.0,
  "total_detections": 12,
  "frames_with_detections": 8,
  "avg_confidence": 0.8540,
  "detections": [
    {
      "frame_id": 15,
      "timestamp": "2026-09-27T00:00:00.500Z",
      "bbox": {
        "x1": 120.0,
        "y1": 250.0,
        "x2": 240.0,
        "y2": 330.0
      },
      "confidence": 0.88,
      "class": "pothole"
    }
  ]
}
```

---

## Usage Instructions

### Basic Video Inference

```bash
python ml/inference/detect.py \
  --video data/sample/test_video.mp4 \
  --model ml/models/best.pt \
  --output-json ml/runs/detect/detections.json
```

### Video Inference with Annotated Output Video

```bash
python ml/inference/detect.py \
  --video data/sample/test_video.mp4 \
  --model ml/models/best.pt \
  --output-json ml/runs/detect/detections.json \
  --output-video ml/runs/detect/annotated.mp4 \
  --conf 0.25
```

### Command-Line Arguments

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--video` | Path | **(Required)** | Path to input `.mp4` video file |
| `--model` | Path | `ml/models/best.pt` | Path to trained YOLOv8 model weights |
| `--output-json` | Path | `ml/runs/detect/detections.json` | Destination path for detection JSON |
| `--output-video` | Path | `None` | Optional destination path for annotated `.mp4` video |
| `--conf` | Float | `0.25` | Minimum confidence threshold |
| `--imgsz` | Int | `640` | Target image resolution for inference |
| `--device` | String | `cpu` | Inference hardware device (`cpu`, `0`) |
| `--source-id` | String | Video stem | Stream identifier |
| `--mock` | Flag | `False` | Forces mock inference engine for testing |
