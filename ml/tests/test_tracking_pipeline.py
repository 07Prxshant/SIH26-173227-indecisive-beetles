#!/usr/bin/env python3
"""
Unit tests for UrbanSense ByteTrack Pothole Tracking Engine.
Verifies:
  1. Track Creation
  2. Track Persistence across consecutive frames
  3. Track Termination after max_time_lost frames
  4. Multiple Pothole tracking (distinct track_ids)
  5. Recovery during temporary missed detections
"""

import unittest
from ml.tracking.tracker import ByteTracker, STrack


class TestTrackingPipeline(unittest.TestCase):

    def setUp(self):
        self.tracker = ByteTracker(
            track_thresh=0.5,
            low_thresh=0.1,
            match_iou_thresh=0.2,
            max_time_lost=3
        )
        self.tracker.reset()

    def test_track_creation(self):
        """Verifies that a high-confidence detection creates a new track_id."""
        frame_0_dets = [
            {"bbox": {"x1": 100.0, "y1": 200.0, "x2": 200.0, "y2": 300.0}, "confidence": 0.85, "class": "pothole"}
        ]
        tracked = self.tracker.update(frame_0_dets, frame_id=0)

        self.assertEqual(len(tracked), 1)
        self.assertIn("track_id", tracked[0])
        self.assertEqual(tracked[0]["track_id"], "1")
        self.assertEqual(tracked[0]["frame_id"], 0)

    def test_track_persistence(self):
        """Verifies that consecutive frames with slight motion maintain stable track_id."""
        initial_track_id = None

        for fid in range(5):
            # Move box slightly to simulate camera/vehicle movement
            dets = [
                {"bbox": {"x1": 100.0 + fid * 2.0, "y1": 200.0, "x2": 200.0 + fid * 2.0, "y2": 300.0}, "confidence": 0.80, "class": "pothole"}
            ]
            tracked = self.tracker.update(dets, frame_id=fid)
            self.assertEqual(len(tracked), 1)

            if fid == 0:
                initial_track_id = tracked[0]["track_id"]
            else:
                self.assertEqual(tracked[0]["track_id"], initial_track_id)

    def test_multiple_potholes(self):
        """Verifies that two distinct potholes receive separate stable track_ids."""
        frame_dets = [
            {"bbox": {"x1": 50.0, "y1": 100.0, "x2": 150.0, "y2": 200.0}, "confidence": 0.90, "class": "pothole"},
            {"bbox": {"x1": 400.0, "y1": 300.0, "x2": 500.0, "y2": 400.0}, "confidence": 0.88, "class": "pothole"}
        ]
        tracked = self.tracker.update(frame_dets, frame_id=0)

        self.assertEqual(len(tracked), 2)
        track_ids = {t["track_id"] for t in tracked}
        self.assertEqual(len(track_ids), 2)

    def test_temporary_missed_detection_recovery(self):
        """
        Verifies that a track is recovered and maintains its track_id
        when a detection dips in confidence or is temporarily missing for a frame.
        """
        # Frame 0: High confidence -> creates track_id "1"
        tracked_0 = self.tracker.update([
            {"bbox": {"x1": 100.0, "y1": 200.0, "x2": 200.0, "y2": 300.0}, "confidence": 0.85, "class": "pothole"}
        ], frame_id=0)
        track_id_0 = tracked_0[0]["track_id"]

        # Frame 1: Low confidence (0.2) -> matched in second stage
        tracked_1 = self.tracker.update([
            {"bbox": {"x1": 102.0, "y1": 201.0, "x2": 202.0, "y2": 301.0}, "confidence": 0.20, "class": "pothole"}
        ], frame_id=1)
        self.assertEqual(len(tracked_1), 1)
        self.assertEqual(tracked_1[0]["track_id"], track_id_0)

        # Frame 2: Missed detection (0 detections in frame 2)
        tracked_2 = self.tracker.update([], frame_id=2)
        self.assertEqual(len(tracked_2), 0)  # No active detection emitted in frame 2

        # Frame 3: Pothole reappears with high confidence -> recovers track_id "1"
        tracked_3 = self.tracker.update([
            {"bbox": {"x1": 105.0, "y1": 203.0, "x2": 205.0, "y2": 303.0}, "confidence": 0.82, "class": "pothole"}
        ], frame_id=3)
        self.assertEqual(len(tracked_3), 1)
        self.assertEqual(tracked_3[0]["track_id"], track_id_0)

    def test_track_termination(self):
        """Verifies that a track is terminated after max_time_lost frames of absence."""
        # Frame 0: Track created
        tracked_0 = self.tracker.update([
            {"bbox": {"x1": 100.0, "y1": 200.0, "x2": 200.0, "y2": 300.0}, "confidence": 0.85, "class": "pothole"}
        ], frame_id=0)
        old_track_id = tracked_0[0]["track_id"]

        # Frames 1, 2, 3, 4: No detections (max_time_lost = 3)
        for fid in range(1, 5):
            self.tracker.update([], frame_id=fid)

        # Frame 5: New detection at far away location (or after track termination)
        tracked_5 = self.tracker.update([
            {"bbox": {"x1": 500.0, "y1": 500.0, "x2": 600.0, "y2": 600.0}, "confidence": 0.90, "class": "pothole"}
        ], frame_id=5)

        self.assertEqual(len(tracked_5), 1)
        self.assertNotEqual(tracked_5[0]["track_id"], old_track_id)


if __name__ == "__main__":
    unittest.main()
