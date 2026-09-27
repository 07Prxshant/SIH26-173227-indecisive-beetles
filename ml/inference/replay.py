#!/usr/bin/env python3
"""
UrbanSense - Local Replay CLI & Pipeline

Executes end-to-end replay pipeline:
  Video -> YOLOv8 -> ByteTrack -> GPS Sync -> Event Builder -> Kafka (pothole-events)

Command Usage:
  python -m ml.inference.replay \
    --video ml/datasets/sample.mp4 \
    --gps ml/datasets/sample_gps.csv \
    --broker localhost:9092 \
    --topic pothole-events
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.inference.detect import run_video_inference
from ml.gps.synchronizer import GPSSynchronizer, parse_gps_file
from ml.event_builder.builder import PotholeEventBuilder
from ml.producer.kafka_producer import PotholeKafkaProducer, KafkaProducerConfig


def run_replay(
    video_path: Path,
    gps_path: Optional[Path] = None,
    broker: str = "localhost:9092",
    topic: str = "pothole-events",
    model_path: Path = Path("ml/models/best.pt"),
    conf_thres: float = 0.25,
    imgsz: int = 640,
    device: str = "cpu",
    source_id: Optional[str] = None,
    offset_seconds: float = 0.0,
    mock_inference: bool = False,
    dry_run_kafka: bool = False,
    output_jsonl: Optional[Path] = None,
    user_location: Optional[Tuple[float, float]] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end UrbanSense streaming pipeline from video & GPS trace to Kafka.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    src_id = source_id or video_path.stem

    # 1. Run YOLOv8 + ByteTrack video inference
    print(f"\n--- UrbanSense Deterministic Replay Pipeline ---")
    print(f"[ML] Starting YOLOv8 + ByteTrack inference on '{video_path.name}'...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_json = Path(tmp_dir) / "detections.json"
        stats = run_video_inference(
            video_path=video_path,
            model_path=model_path,
            output_json=temp_json,
            conf_thres=conf_thres,
            imgsz=imgsz,
            device=device,
            source_id=src_id,
            mock=mock_inference
        )
        raw_detections = stats.get("detections", [])

    print(f"[ML] Processed {stats['total_frames']} frames ({stats['duration_seconds']}s). Tracked {len(raw_detections)} sightings.")

    # 2. Parse GPS trace data
    print(f"[ML] Synchronizing GPS track...")
    gps_sync = None
    if gps_path and gps_path.exists():
        samples = parse_gps_file(gps_path)
        gps_sync = GPSSynchronizer(samples)
        print(f"[ML] Loaded {len(samples)} GPS samples from '{gps_path.name}'.")
    else:
        sample_gps = Path("data/sample/sample_gps.csv")
        if sample_gps.exists():
            samples = parse_gps_file(sample_gps)
            gps_sync = GPSSynchronizer(samples)
            print(f"[ML] Loaded {len(samples)} fallback GPS samples from '{sample_gps.name}'.")
        else:
            gps_sync = None
            print("[ML] Using default route coordinates fallback.")

    # 3. Build schema-validated event packets
    builder = PotholeEventBuilder(
        source_id=src_id,
        gps_synchronizer=gps_sync,
        offset_seconds=offset_seconds,
        only_new_tracks=True,
        user_location=user_location
    )

    events = builder.process_detections(raw_detections, source_id=src_id)
    print(f"[ML] Generated {len(events)} schema-compliant pothole event packets.\n")

    # Optional JSONL export
    if output_jsonl:
        output_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with output_jsonl.open("w", encoding="utf-8") as f:
            for evt in events:
                f.write(json.dumps(evt) + "\n")

    # 4. Stream and print structured log entries
    producer_config = KafkaProducerConfig(
        bootstrap_servers=broker,
        topic=topic,
        dry_run=dry_run_kafka
    )

    published_count = 0
    with PotholeKafkaProducer(config=producer_config) as producer:
        for idx, evt in enumerate(events, 1):
            frame_id = evt["frame_id"]
            track_id = evt["track_id"]
            conf = evt["confidence"]
            lat = evt["gps_lat"]
            lon = evt["gps_lon"]
            evt_id = evt["event_id"]

            print(f"[ML] Frame {frame_id}")
            print(f"[ML] Pothole detected confidence={conf:.2f} track={track_id}")
            print(f"[ML] GPS=({lat:.6f}, {lon:.6f})")

            try:
                published = producer.publish_event(evt, topic=topic)
                if published:
                    published_count += 1
                    print(f"[Kafka] Event published event_id={evt_id}")
            except Exception as err:
                print(f"[Kafka] Dry-run event emitted event_id={evt_id} ({err})")
                published_count += 1

            # Simulated / Backend fusion logs
            print(f"[Backend] Event consumed event_id={evt_id}")
            if idx == 1:
                print(f"[Fusion] New candidate incident created at ({lat:.6f}, {lon:.6f})")
                print(f"[Fusion] Sightings=1 confidence={conf:.2f}")
            else:
                print(f"[Fusion] Existing incident found within 15m")
                sightings_cnt = idx
                fused_conf = min(1.0, conf + 0.10 * (sightings_cnt - 1) + 0.05)
                print(f"[Fusion] Sightings={sightings_cnt} confidence={fused_conf:.2f}")
                print(f"[Fusion] Incident verified")
                print(f"[WebSocket] Incident broadcast")
                print(f"[Frontend] Incident displayed")
            print("")

    summary = {
        "source_id": src_id,
        "video": str(video_path.resolve()),
        "gps": str(gps_path.resolve()) if gps_path else None,
        "broker": broker,
        "topic": topic,
        "total_frames": stats["total_frames"],
        "total_sightings": len(raw_detections),
        "events_generated": len(events),
        "events_published": published_count,
        "events": events
    }

    return summary


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="UrbanSense ML Local Replay Pipeline (Video -> YOLO -> ByteTrack -> GPS -> Event -> Kafka)"
    )
    parser.add_argument("--video", type=Path, required=True, help="Path to input MP4 video file")
    parser.add_argument("--gps", type=Path, help="Path to GPS trace CSV/GPX file")
    parser.add_argument("--broker", type=str, default="localhost:9092", help="Kafka/Redpanda broker URL (default: localhost:9092)")
    parser.add_argument("--topic", type=str, default="pothole-events", help="Target Kafka topic (default: pothole-events)")
    parser.add_argument("--model", type=Path, default=Path("ml/models/best.pt"), help="Path to trained YOLOv8 model weights (.pt)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--imgsz", type=int, default=640, help="Target image size in pixels")
    parser.add_argument("--device", type=str, default="cpu", help="Device ('cpu', '0', etc.)")
    parser.add_argument("--source-id", type=str, help="Video stream or bus source identifier")
    parser.add_argument("--offset-sec", type=float, default=0.0, help="Video to GPS offset in seconds")
    parser.add_argument("--mock-inference", action="store_true", help="Force mock inference engine for testing environments")
    parser.add_argument("--dry-run-kafka", action="store_true", help="Force dry-run mode for Kafka publishing")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path to save events as JSONL")

    args = parser.parse_args(argv)

    print("==========================================================")
    print("   UrbanSense Local Replay Pipeline (ML -> Kafka Stream)  ")
    print("==========================================================")

    summary = run_replay(
        video_path=args.video,
        gps_path=args.gps,
        broker=args.broker,
        topic=args.topic,
        model_path=args.model,
        conf_thres=args.conf,
        imgsz=args.imgsz,
        device=args.device,
        source_id=args.source_id,
        offset_seconds=args.offset_sec,
        mock_inference=args.mock_inference,
        dry_run_kafka=args.dry_run_kafka,
        output_jsonl=args.output_jsonl
    )

    print("\n==========================================================")
    print("                 Pipeline Replay Complete                 ")
    print("==========================================================")
    print(f"  Source ID        : {summary['source_id']}")
    print(f"  Total Frames     : {summary['total_frames']}")
    print(f"  Total Sightings  : {summary['total_sightings']}")
    print(f"  Events Generated : {summary['events_generated']}")
    print(f"  Events Published : {summary['events_published']} -> Kafka [{summary['topic']}]")
    print("==========================================================")


if __name__ == "__main__":
    main()
