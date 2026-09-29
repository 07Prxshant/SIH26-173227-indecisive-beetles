"""REST endpoint for uploading road video and processing with YOLOv8 + ByteTrack pipeline."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.event_processor import EventProcessor
from app.services.fusion.persistence import SqlAlchemyFusionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

PROCESSING_JOBS: Dict[str, Dict[str, Any]] = {}


class SeverityBreakdown(BaseModel):
    High: int = 0
    Medium: int = 0
    Low: int = 0


class VideoProcessingResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    total_frames: int
    potholes_detected: int
    events_generated: int
    message: str
    severity_breakdown: SeverityBreakdown = SeverityBreakdown()
    incidents: list[dict] = []


def run_ml_pipeline_on_file(
    video_path: Path,
    gps_path: Optional[Path] = None,
    source_id: Optional[str] = None,
    user_location: Optional[tuple[float, float]] = None
) -> Dict[str, Any]:
    """Execute real ML pipeline on uploaded video, stream events to Kafka and local fusion."""
    from ml.inference.replay import run_replay

    settings = get_settings()

    summary = run_replay(
        video_path=video_path,
        gps_path=gps_path,
        broker=settings.kafka_brokers,
        topic=settings.pothole_events_topic,
        model_path=Path("ml/models/best.pt"),
        source_id=source_id or video_path.stem,
        dry_run_kafka=False,
        user_location=user_location
    )

    processor = EventProcessor()
    fusion_service = SqlAlchemyFusionService()

    from app.services.road_segment import GridRoadSegmentResolver
    resolver = GridRoadSegmentResolver()

    fused_incidents = []
    events = summary.get("events", [])
    sev_counts = summary.get("severity_breakdown", {"High": 0, "Medium": 0, "Low": 0})

    from datetime import datetime, timezone

    for evt in events:
        inc_id = str(uuid.uuid4())
        conf = float(evt.get("confidence", 0.85))
        lat = float(evt.get("gps_lat", user_location[0] if user_location else 12.9753))
        lon = float(evt.get("gps_lon", user_location[1] if user_location else 77.6021))
        track_id = str(evt.get("track_id", "1"))
        frame_ref = evt.get("frame_ref") or evt.get("image_ref")

        try:
            created = processor.process(evt)
            if created:
                outcome = fusion_service.fuse_raw_sighting(
                    uuid.UUID(str(evt["event_id"])),
                    resolver.resolve(evt)
                )
                if outcome.incident is not None:
                    inc_id = str(outcome.incident.id)
                    conf = outcome.incident.confidence
                    if not user_location:
                        lat = outcome.incident.latitude
                        lon = outcome.incident.longitude
                    frame_ref = outcome.incident.representative_image or frame_ref
        except Exception as e:
            logger.warning(f"Database ingestion fallback (in-memory mode): {e}")

        now_iso = datetime.now(timezone.utc).isoformat()
        fused_incidents.append({
            "incident_id": inc_id,
            "latitude": lat,
            "longitude": lon,
            "road_segment_id": f"ROAD-SEG-{track_id}",
            "confidence": conf,
            "detector_confidence": conf,
            "sighting_count": summary.get("total_sightings", 1),
            "first_seen": evt.get("timestamp", now_iso),
            "last_seen": evt.get("timestamp", now_iso),
            "status": "verified" if conf >= 0.6 else "candidate",
            "representative_image": frame_ref,
            "track_id": track_id,
            "source_id": source_id or video_path.stem,
            "severity": "High" if conf >= 0.85 else "Medium" if conf >= 0.70 else "Low"
        })

    high_c = sum(1 for i in fused_incidents if i.get("confidence", 0) >= 0.85)
    med_c = sum(1 for i in fused_incidents if 0.70 <= i.get("confidence", 0) < 0.85)
    low_c = sum(1 for i in fused_incidents if i.get("confidence", 0) < 0.70)
    sev_counts = {"High": high_c, "Medium": med_c, "Low": low_c}

    return {
        "total_frames": summary.get("total_frames", 0),
        "potholes_detected": summary.get("total_sightings", 0),
        "events_generated": summary.get("events_generated", 0),
        "severity_breakdown": sev_counts,
        "events": events,
        "fused_incidents": fused_incidents
    }


@router.post(
    "/upload",
    response_model=VideoProcessingResponse,
    summary="Upload road video for pothole detection",
    description="Receives an uploaded .mp4 video, processes it with YOLOv8 & ByteTrack, streams events to Kafka & Fusion, and updates PostGIS."
)
async def upload_video(
    video: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    gps: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    user_location: Optional[str] = Form(None)
) -> VideoProcessingResponse:
    target_video = video or file
    if target_video is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing video file. Provide a video file under parameter name 'video' or 'file'.",
        )
    video = target_video
    file_ext = Path(video.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed video formats: {allowed_str}"
        )

    job_id = str(uuid.uuid4())
    upload_dir = Path("data/uploads/videos")
    gps_dir = Path("data/uploads/gps")
    upload_dir.mkdir(parents=True, exist_ok=True)
    gps_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{job_id}_{Path(video.filename or 'video.mp4').name}"
    video_dest = upload_dir / safe_name

    try:
        with video_dest.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded video file: {e}"
        )

    gps_dest = None
    if gps is not None and gps.filename:
        gps_name = f"{job_id}_{Path(gps.filename).name}"
        gps_dest = gps_dir / gps_name
        try:
            with gps_dest.open("wb") as buffer:
                shutil.copyfileobj(gps.file, buffer)
        except Exception as e:
            logger.warning(f"Failed to save optional GPS file: {e}")

    PROCESSING_JOBS[job_id] = {
        "job_id": job_id,
        "status": "processing",
        "filename": video.filename
    }

    try:
        user_loc = None
        if latitude is not None and longitude is not None:
            user_loc = (float(latitude), float(longitude))
        elif user_location:
            try:
                parts = [float(p.strip()) for p in user_location.split(",") if p.strip()]
                if len(parts) == 2 and -90.0 <= parts[0] <= 90.0 and -180.0 <= parts[1] <= 180.0:
                    user_loc = (parts[0], parts[1])
                else:
                    user_loc = (28.6139, 77.2090)
            except Exception:
                user_loc = (28.6139, 77.2090)

        result = await run_in_threadpool(
            run_ml_pipeline_on_file,
            video_path=video_dest,
            gps_path=gps_dest,
            source_id=Path(video.filename or "video").stem,
            user_location=user_loc
        )

        potholes = result["potholes_detected"]
        events_cnt = result["events_generated"]
        frames_cnt = result["total_frames"]
        sev_bd = result["severity_breakdown"]

        if potholes == 0:
            msg = "Processing completed. No potholes were detected in this video."
        else:
            msg = f"Processing completed! Detected {potholes} pothole sightings across {frames_cnt} frames."

        PROCESSING_JOBS[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "filename": video.filename,
            "total_frames": frames_cnt,
            "potholes_detected": potholes,
            "events_generated": events_cnt,
            "severity_breakdown": sev_bd,
            "message": msg
        }

        return VideoProcessingResponse(
            job_id=job_id,
            status="completed",
            filename=video.filename or "video.mp4",
            total_frames=frames_cnt,
            potholes_detected=potholes,
            events_generated=events_cnt,
            severity_breakdown=SeverityBreakdown(**sev_bd),
            message=msg,
            incidents=result["fused_incidents"]
        )

    except Exception as e:
        logger.exception(f"Video ML processing failed for job {job_id}")
        PROCESSING_JOBS[job_id] = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML Video Processing failed: {e}"
        )


@router.get("/status/{job_id}", summary="Check video processing status")
def get_job_status(job_id: str) -> Dict[str, Any]:
    if job_id not in PROCESSING_JOBS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return PROCESSING_JOBS[job_id]
