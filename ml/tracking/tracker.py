#!/usr/bin/env python3
"""
UrbanSense - ByteTrack Multi-Object Tracking Engine

Implements ByteTrack association logic for single-class pothole tracking across video frames.
Maintains stable track_ids for consecutive detections and recovers tracks across
temporary missed detections.
"""

from typing import Dict, List, Tuple, Any, Optional


def compute_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    if inter_area <= 0:
        return 0.0

    areaA = max(0.0, boxA[2] - boxA[0]) * max(0.0, boxA[3] - boxA[1])
    areaB = max(0.0, boxB[2] - boxB[0]) * max(0.0, boxB[3] - boxB[1])

    union_area = areaA + areaB - inter_area
    if union_area <= 0:
        return 0.0

    return inter_area / union_area


class TrackState:
    New = "New"
    Tracked = "Tracked"
    Lost = "Lost"
    Removed = "Removed"


class STrack:
    """Represents a single tracked pothole instance."""
    _count = 0

    def __init__(self, bbox: Tuple[float, float, float, float], confidence: float, class_name: str = "pothole"):
        STrack._count += 1
        self.track_id = str(STrack._count)
        self.bbox = bbox
        self.confidence = confidence
        self.class_name = class_name
        self.state = TrackState.New
        self.time_since_update = 0
        self.frame_id = 0
        self.hits = 1

    @classmethod
    def reset_counter(cls, start_id: int = 0) -> None:
        """Resets track ID counter for deterministic testing."""
        cls._count = start_id

    def update(self, new_bbox: Tuple[float, float, float, float], new_conf: float, frame_id: int) -> None:
        """Updates track state with new detection bounding box and confidence."""
        self.bbox = new_bbox
        self.confidence = new_conf
        self.frame_id = frame_id
        self.time_since_update = 0
        self.hits += 1
        self.state = TrackState.Tracked

    def mark_lost(self) -> None:
        """Marks track as temporarily lost when undetected in current frame."""
        self.state = TrackState.Lost

    def mark_removed(self) -> None:
        """Terminates track permanently."""
        self.state = TrackState.Removed


class ByteTracker:
    """
    ByteTrack association engine.
    Splits detections into high-confidence and low-confidence pools, performing
    two-stage IoU association to maintain stable track identities.
    """

    def __init__(
        self,
        track_thresh: float = 0.5,
        low_thresh: float = 0.1,
        match_iou_thresh: float = 0.2,
        max_time_lost: int = 30
    ):
        self.track_thresh = track_thresh
        self.low_thresh = low_thresh
        self.match_iou_thresh = match_iou_thresh
        self.max_time_lost = max_time_lost

        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []
        self.frame_id = 0

    def reset(self) -> None:
        """Resets tracker state."""
        self.tracked_stracks = []
        self.lost_stracks = []
        self.removed_stracks = []
        self.frame_id = 0
        STrack.reset_counter(0)

    def _greedy_match(
        self,
        tracks: List[STrack],
        detections: List[Dict[str, Any]],
        iou_thresh: float
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Performs greedy IoU matching between tracks and detection dicts."""
        if not tracks or not detections:
            return [], list(range(len(tracks))), list(range(len(detections)))

        # Build IoU matrix
        iou_matrix = []
        for trk in tracks:
            row = []
            for det in detections:
                box_det = (
                    det["bbox"]["x1"],
                    det["bbox"]["y1"],
                    det["bbox"]["x2"],
                    det["bbox"]["y2"]
                ) if isinstance(det["bbox"], dict) else det["bbox"]
                row.append(compute_iou(trk.bbox, box_det))
            iou_matrix.append(row)

        matches = []
        unmatched_tracks = set(range(len(tracks)))
        unmatched_dets = set(range(len(detections)))

        # Find best matches above IoU threshold
        candidates = []
        for t_idx in range(len(tracks)):
            for d_idx in range(len(detections)):
                iou = iou_matrix[t_idx][d_idx]
                if iou >= iou_thresh:
                    candidates.append((iou, t_idx, d_idx))

        candidates.sort(key=lambda x: x[0], reverse=True)

        for iou, t_idx, d_idx in candidates:
            if t_idx in unmatched_tracks and d_idx in unmatched_dets:
                matches.append((t_idx, d_idx))
                unmatched_tracks.remove(t_idx)
                unmatched_dets.remove(d_idx)

        return matches, sorted(list(unmatched_tracks)), sorted(list(unmatched_dets))

    def update(self, detections: List[Dict[str, Any]], frame_id: int) -> List[Dict[str, Any]]:
        """
        Updates tracking state for current frame detections.
        Returns list of detection dictionaries enriched with track_id.
        """
        self.frame_id = frame_id

        # 1. Separate detections into high-confidence and low-confidence pools
        high_dets = []
        low_dets = []

        for det in detections:
            conf = det.get("confidence", 0.0)
            if conf >= self.track_thresh:
                high_dets.append(det)
            elif conf >= self.low_thresh:
                low_dets.append(det)

        # Active tracks pool = tracked + lost
        active_tracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked]
        lost_tracks = [t for t in self.tracked_stracks if t.state == TrackState.Lost] + self.lost_stracks

        # 2. First association: match active tracks with high-confidence detections
        matches_1, u_track_1, u_det_high = self._greedy_match(active_tracks, high_dets, self.match_iou_thresh)

        # Update matched tracks
        for t_idx, d_idx in matches_1:
            det = high_dets[d_idx]
            box_det = (
                det["bbox"]["x1"],
                det["bbox"]["y1"],
                det["bbox"]["x2"],
                det["bbox"]["y2"]
            ) if isinstance(det["bbox"], dict) else det["bbox"]
            active_tracks[t_idx].update(box_det, det["confidence"], frame_id)

        # 3. Second association: match remaining unmatched active tracks with low-confidence detections
        unmatched_active = [active_tracks[i] for i in u_track_1]
        matches_2, u_track_2, u_det_low = self._greedy_match(unmatched_active, low_dets, self.match_iou_thresh)

        for t_idx, d_idx in matches_2:
            det = low_dets[d_idx]
            box_det = (
                det["bbox"]["x1"],
                det["bbox"]["y1"],
                det["bbox"]["x2"],
                det["bbox"]["y2"]
            ) if isinstance(det["bbox"], dict) else det["bbox"]
            unmatched_active[t_idx].update(box_det, det["confidence"], frame_id)

        # 4. Third association: match remaining lost tracks with unmatched high-confidence detections
        rem_high_dets = [high_dets[i] for i in u_det_high]
        matches_3, u_lost_track, u_det_rem = self._greedy_match(lost_tracks, rem_high_dets, self.match_iou_thresh)

        for t_idx, d_idx in matches_3:
            det = rem_high_dets[d_idx]
            box_det = (
                det["bbox"]["x1"],
                det["bbox"]["y1"],
                det["bbox"]["x2"],
                det["bbox"]["y2"]
            ) if isinstance(det["bbox"], dict) else det["bbox"]
            lost_tracks[t_idx].update(box_det, det["confidence"], frame_id)

        # 5. Create new tracks for unmatched high-confidence detections
        new_high_dets = [rem_high_dets[i] for i in u_det_rem]
        new_tracks = []
        for det in new_high_dets:
            box_det = (
                det["bbox"]["x1"],
                det["bbox"]["y1"],
                det["bbox"]["x2"],
                det["bbox"]["y2"]
            ) if isinstance(det["bbox"], dict) else det["bbox"]
            strack = STrack(box_det, det["confidence"], det.get("class", "pothole"))
            strack.frame_id = frame_id
            strack.state = TrackState.Tracked
            new_tracks.append(strack)

        # 6. Update lost tracks and handle track termination
        still_unmatched_active = [unmatched_active[i] for i in u_track_2]
        for trk in still_unmatched_active:
            trk.time_since_update += 1
            trk.mark_lost()

        still_unmatched_lost = [lost_tracks[i] for i in u_lost_track]
        for trk in still_unmatched_lost:
            trk.time_since_update += 1

        # Consolidate all tracks
        all_tracks = []
        for trk in active_tracks + lost_tracks + new_tracks:
            if trk.time_since_update > self.max_time_lost:
                trk.mark_removed()
                self.removed_stracks.append(trk)
            else:
                all_tracks.append(trk)

        # Remove duplicate tracks
        unique_tracks = {}
        for trk in all_tracks:
            unique_tracks[trk.track_id] = trk
        self.tracked_stracks = list(unique_tracks.values())

        # 7. Formulate tracked output detections for current frame
        output_detections = []
        for trk in self.tracked_stracks:
            if trk.frame_id == frame_id and trk.state == TrackState.Tracked:
                x1, y1, x2, y2 = trk.bbox
                det_record = {
                    "frame_id": frame_id,
                    "timestamp": "",  # To be filled by video pipeline
                    "bbox": {"x1": round(x1, 1), "y1": round(y1, 1), "x2": round(x2, 1), "y2": round(y2, 1)},
                    "confidence": round(trk.confidence, 4),
                    "class": trk.class_name,
                    "track_id": trk.track_id
                }
                output_detections.append(det_record)

        return output_detections
