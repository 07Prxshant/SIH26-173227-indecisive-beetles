#!/usr/bin/env python3
"""
Unit tests for UrbanSense GPS Synchronization Engine (ml/gps).
"""

import datetime
import tempfile
import unittest
from pathlib import Path

from ml.gps.synchronizer import (
    GPSSample,
    GPSSynchronizer,
    parse_gps_csv,
    parse_gpx,
    parse_gps_file,
    parse_timestamp,
)


class TestGPSSync(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_time = datetime.datetime(2026, 9, 27, 10, 0, 0, tzinfo=datetime.timezone.utc)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_timestamp_variants(self):
        # ISO string with Z
        dt1 = parse_timestamp("2026-09-27T10:00:00Z")
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.hour, 10)
        self.assertEqual(dt1.tzinfo, datetime.timezone.utc)

        # Space separated
        dt2 = parse_timestamp("2026-09-27 10:00:00")
        self.assertEqual(dt2, dt1)

        # Epoch seconds
        ts = self.base_time.timestamp()
        dt3 = parse_timestamp(ts)
        self.assertEqual(dt3, dt1)

    def test_csv_parser(self):
        csv_path = Path(self.temp_dir.name) / "gps.csv"
        csv_path.write_text(
            "timestamp,latitude,longitude,altitude\n"
            "2026-09-27T10:00:00Z,37.7749,-122.4194,15.2\n"
            "2026-09-27T10:00:10Z,37.7750,-122.4190,15.5\n"
            "invalid_row,999.0,999.0,0.0\n",
            encoding="utf-8"
        )

        samples = parse_gps_csv(csv_path)
        self.assertEqual(len(samples), 2)
        self.assertAlmostEqual(samples[0].latitude, 37.7749)
        self.assertAlmostEqual(samples[0].longitude, -122.4194)
        self.assertEqual(samples[0].altitude, 15.2)

    def test_gpx_parser(self):
        gpx_path = Path(self.temp_dir.name) / "gps.gpx"
        gpx_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="test">\n'
            '  <trk><trkseg>\n'
            '    <trkpt lat="37.7749" lon="-122.4194">\n'
            '      <time>2026-09-27T10:00:00Z</time>\n'
            '      <ele>10.0</ele>\n'
            '    </trkpt>\n'
            '    <trkpt lat="37.7755" lon="-122.4180">\n'
            '      <time>2026-09-27T10:00:10Z</time>\n'
            '      <ele>12.0</ele>\n'
            '    </trkpt>\n'
            '  </trkseg></trk>\n'
            '</gpx>',
            encoding="utf-8"
        )

        samples = parse_gpx(gpx_path)
        self.assertEqual(len(samples), 2)
        self.assertAlmostEqual(samples[1].latitude, 37.7755)
        self.assertAlmostEqual(samples[1].longitude, -122.4180)

    def test_out_of_order_samples_handling(self):
        # Create samples out of chronological order
        s1 = GPSSample(timestamp=self.base_time, latitude=37.7749, longitude=-122.4194)
        s2 = GPSSample(timestamp=self.base_time + datetime.timedelta(seconds=10), latitude=37.7750, longitude=-122.4190)
        s3 = GPSSample(timestamp=self.base_time + datetime.timedelta(seconds=5), latitude=37.77495, longitude=-122.4192)

        sync = GPSSynchronizer([s2, s1, s3])  # Unsorted input

        # Verify sorted internally
        self.assertEqual(sync.samples[0].timestamp, s1.timestamp)
        self.assertEqual(sync.samples[1].timestamp, s3.timestamp)
        self.assertEqual(sync.samples[2].timestamp, s2.timestamp)

    def test_interpolation_and_sync(self):
        s1 = GPSSample(timestamp=self.base_time, latitude=37.7700, longitude=-122.4000)
        s2 = GPSSample(timestamp=self.base_time + datetime.timedelta(seconds=10), latitude=37.7710, longitude=-122.4010)

        sync = GPSSynchronizer([s1, s2])

        # Exact match at t=0
        lat0, lon0 = sync.get_gps_at_time(self.base_time)
        self.assertAlmostEqual(lat0, 37.7700)
        self.assertAlmostEqual(lon0, -122.4000)

        # Midpoint interpolation at t=5s (50% alpha)
        mid_time = self.base_time + datetime.timedelta(seconds=5)
        lat_mid, lon_mid = sync.get_gps_at_time(mid_time, interpolate=True)
        self.assertAlmostEqual(lat_mid, 37.7705)
        self.assertAlmostEqual(lon_mid, -122.4005)

    def test_video_gps_offset_and_drift(self):
        s1 = GPSSample(timestamp=self.base_time, latitude=37.7700, longitude=-122.4000)
        sync = GPSSynchronizer([s1])

        # Video time is 2 seconds behind GPS time (offset = +2.0s)
        video_time = self.base_time - datetime.timedelta(seconds=2)
        lat, lon = sync.get_gps_at_time(video_time, offset_seconds=2.0)
        self.assertAlmostEqual(lat, 37.7700)
        self.assertAlmostEqual(lon, -122.4000)

    def test_missing_gps_sample_and_max_gap(self):
        s1 = GPSSample(timestamp=self.base_time, latitude=37.7700, longitude=-122.4000)
        sync = GPSSynchronizer([s1])

        # Target time is 60 seconds after last sample (max gap 10s)
        far_time = self.base_time + datetime.timedelta(seconds=60)
        lat, lon = sync.get_gps_at_time(far_time, max_gap_seconds=10.0, default_coords=(0.0, 0.0))
        self.assertEqual(lat, 0.0)
        self.assertEqual(lon, 0.0)

    def test_empty_gps(self):
        sync = GPSSynchronizer([])
        self.assertTrue(sync.is_empty())
        lat, lon = sync.get_gps_at_time("2026-09-27T10:00:00Z", default_coords=(-1.0, -1.0))
        self.assertEqual((lat, lon), (-1.0, -1.0))


if __name__ == "__main__":
    unittest.main()
