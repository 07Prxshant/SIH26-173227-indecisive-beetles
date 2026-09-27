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


class VideoProcessingResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    total_frames: int
    potholes_detected: int
    events_generated: int
    message: str
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

    for evt in events:
        try:
            created = processor.process(evt)
            if created:
                outcome = fusion_service.fuse_raw_sighting(
                    uuid.UUID(str(evt["event_id"])),
                    resolver.resolve(evt)
                )
                if outcome.incident is not None:
                    fused_incidents.append({
                        "id": str(outcome.incident.id),
                        "status": outcome.incident.status,
                        "confidence": outcome.incident.confidence,
                        "latitude": outcome.incident.latitude,
                        "longitude": outcome.incident.longitude
                    })
        except Exception as e:
            logger.warning(f"Event ingestion exception: {e}")

    return {
        "total_frames": summary.get("total_frames", 0),
        "potholes_detected": summary.get("total_sightings", 0),
        "events_generated": summary.get("events_generated", 0),
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
    video: UploadFile = File(...),
    gps: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None)
) -> VideoProcessingResponse:
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
        if latitude is not None or longitude is not None:
            if latitude is None or longitude is None or not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid location coordinates. Latitude must be between -90 and 90, and Longitude between -180 and 180."
                )
            user_loc = (float(latitude), float(longitude))

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
            "message": msg
        }

        return VideoProcessingResponse(
            job_id=job_id,
            status="completed",
            filename=video.filename or "video.mp4",
            total_frames=frames_cnt,
            potholes_detected=potholes,
            events_generated=events_cnt,
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
