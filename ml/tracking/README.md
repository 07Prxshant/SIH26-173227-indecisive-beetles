# UrbanSense ByteTrack Pothole Tracking Engine

This directory implements the ByteTrack multi-object tracking module for maintaining stable pothole identities (`track_id`) across consecutive video frames in the **UrbanSense Pothole Detection MVP**.

---

## Architecture Overview

```text
Simulated Video Stream
        │
        ▼
   YOLOv8 Detector
        │ (Detections: bbox, confidence)
        ▼
   ByteTrack Engine
        │ (Two-stage IoU association)
        ▼
   Tracked Detections (bbox, confidence, track_id)
```

---

## ByteTrack Association Rules

ByteTrack processes detections in two stages:

1. **High-Confidence Association**:
   - Detections with `confidence >= track_thresh` (default `0.5`) are matched against existing active tracks using Intersection-over-Union (IoU).
2. **Low-Confidence Association (Recovery)**:
   - Remaining unmatched active tracks are matched against low-confidence detections (`low_thresh <= confidence < track_thresh`).
   - This recovers tracks during **temporary missed detections** (e.g. motion blur or partial occlusion).
3. **Track Creation & Termination**:
   - Unmatched high-confidence detections create new tracks.
   - Tracks undetected for > `max_time_lost` frames (default `30` frames) are automatically terminated and removed.

---

## Tracked Output Format

Every tracked detection contains a stable `track_id`:

```json
{
  "frame_id": 15,
  "timestamp": "2026-09-27T00:00:00.500Z",
  "bbox": {
    "x1": 100.0,
    "y1": 250.0,
    "x2": 220.0,
    "y2": 330.0
  },
  "confidence": 0.88,
  "class": "pothole",
  "track_id": "1"
}
```
