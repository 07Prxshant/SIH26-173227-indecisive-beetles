#!/usr/bin/env python3
"""
UrbanSense - GPS Data Synchronization Engine

Parses GPS track files (CSV/GPX), sorts and cleans out-of-order data,
handles timestamp drift and video/GPS offset, and synchronizes detection
timestamps with the nearest GPS sample or interpolated coordinates.
"""

import csv
import datetime
import math
import xml.etree.ElementTree as ET
from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Union, Dict, Any


@dataclass
class GPSSample:
    """Represents a single GPS data point."""
    timestamp: datetime.datetime  # UTC timezone-aware datetime
    latitude: float               # [-90.0, 90.0]
    longitude: float              # [-180.0, 180.0]
    altitude: Optional[float] = None


def parse_timestamp(ts_val: Union[str, float, int, datetime.datetime]) -> datetime.datetime:
    """
    Parses various timestamp formats (ISO 8601 string, UNIX epoch seconds/ms, datetime object)
    and returns a timezone-aware UTC datetime object.
    """
    if isinstance(ts_val, datetime.datetime):
        if ts_val.tzinfo is None:
            return ts_val.replace(tzinfo=datetime.timezone.utc)
        return ts_val.astimezone(datetime.timezone.utc)

    if isinstance(ts_val, (int, float)):
        # Epoch timestamp in seconds or milliseconds
        val = float(ts_val)
        if val > 1e11:  # Likely milliseconds
            val /= 1000.0
        return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)

    if isinstance(ts_val, str):
        cleaned = ts_val.strip()

        # Numeric string (epoch)
        try:
            val = float(cleaned)
            if val > 1e11:
                val /= 1000.0
            return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
        except ValueError:
            pass

        # ISO 8601 format variants
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"

        try:
            dt = datetime.datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            pass

        # Standard fallback format parsers
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                dt = datetime.datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                continue

    raise ValueError(f"Unable to parse timestamp: {ts_val}")


def parse_gps_csv(file_path: Path) -> List[GPSSample]:
    """
    Parses a CSV file containing GPS log data.
    Flexible header detection for timestamp, latitude, and longitude columns.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"GPS CSV file not found: {file_path}")

    samples: List[GPSSample] = []
    text = file_path.read_text(encoding="utf-8-sig")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return samples

    reader = csv.DictReader(lines)
    if not reader.fieldnames:
        return samples

    # Header mapping
    header_map = {name.lower().strip(): name for name in reader.fieldnames}

    ts_col = next((header_map[k] for k in header_map if k in ("timestamp", "time", "datetime", "date_time", "t")), None)
    lat_col = next((header_map[k] for k in header_map if k in ("latitude", "lat", "y")), None)
    lon_col = next((header_map[k] for k in header_map if k in ("longitude", "lon", "lng", "long", "x")), None)
    alt_col = next((header_map[k] for k in header_map if k in ("altitude", "alt", "elevation", "ele", "z")), None)

    if not ts_col or not lat_col or not lon_col:
        raise ValueError(
            f"CSV file '{file_path}' must contain timestamp, latitude, and longitude columns. Found: {reader.fieldnames}"
        )

    for row_idx, row in enumerate(reader, 1):
        ts_raw = row.get(ts_col)
        lat_raw = row.get(lat_col)
        lon_raw = row.get(lon_col)
        alt_raw = row.get(alt_col) if alt_col else None

        if not ts_raw or not lat_raw or not lon_raw:
            continue

        try:
            ts = parse_timestamp(ts_raw)
            lat = float(lat_raw)
            lon = float(lon_raw)
            alt = float(alt_raw) if alt_raw and alt_raw.strip() else None

            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                samples.append(GPSSample(timestamp=ts, latitude=lat, longitude=lon, altitude=alt))
        except (ValueError, TypeError):
            continue

    return samples


def parse_gpx(file_path: Path) -> List[GPSSample]:
    """
    Parses a GPX file containing track points (<trkpt> or <wpt>).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"GPX file not found: {file_path}")

    samples: List[GPSSample] = []
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Handle XML namespaces dynamically
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    for pt in root.iter(f"{ns}trkpt") if list(root.iter(f"{ns}trkpt")) else root.iter(f"{ns}wpt"):
        lat_str = pt.attrib.get("lat")
        lon_str = pt.attrib.get("lon")
        if not lat_str or not lon_str:
            continue

        time_elem = pt.find(f"{ns}time")
        if time_elem is None or not time_elem.text:
            continue

        ele_elem = pt.find(f"{ns}ele")
        alt = float(ele_elem.text.strip()) if ele_elem is not None and ele_elem.text else None

        try:
            ts = parse_timestamp(time_elem.text.strip())
            lat = float(lat_str)
            lon = float(lon_str)

            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                samples.append(GPSSample(timestamp=ts, latitude=lat, longitude=lon, altitude=alt))
        except (ValueError, TypeError):
            continue

    return samples


def parse_gps_file(file_path: Path) -> List[GPSSample]:
    """Auto-detects file extension and parses CSV or GPX GPS trace files."""
    suffix = file_path.suffix.lower()
    if suffix in (".gpx", ".xml"):
        return parse_gpx(file_path)
    return parse_gps_csv(file_path)


class GPSSynchronizer:
    """
    Synchronizes arbitrary timestamps against a set of GPS track samples.
    
    Handles:
      - Out-of-order GPS samples (sorts chronologically)
      - Timestamp drift & video/GPS offset (supports offset_seconds adjustment)
      - Missing GPS samples (returns nearest/interpolated sample or fallback default coordinates)
      - Linear interpolation between surrounding GPS fixes
    """

    def __init__(self, samples: List[GPSSample]):
        # Filter and sort samples chronologically (handles out-of-order inputs)
        valid_samples = [
            s for s in samples
            if -90.0 <= s.latitude <= 90.0 and -180.0 <= s.longitude <= 180.0
        ]
        self.samples: List[GPSSample] = sorted(valid_samples, key=lambda x: x.timestamp)
        self.timestamps: List[float] = [s.timestamp.timestamp() for s in self.samples]

    @classmethod
    def from_file(cls, file_path: Path) -> "GPSSynchronizer":
        return cls(parse_gps_file(file_path))

    def is_empty(self) -> bool:
        return len(self.samples) == 0

    def get_gps_at_time(
        self,
        target_time: Union[datetime.datetime, str, float],
        offset_seconds: float = 0.0,
        max_gap_seconds: float = 10.0,
        interpolate: bool = True,
        default_coords: Tuple[float, float] = (0.0, 0.0)
    ) -> Tuple[float, float]:
        """
        Retrieves (latitude, longitude) synchronized to target_time.

        :param target_time: Target timestamp (ISO string, epoch seconds, or datetime)
        :param offset_seconds: Video-to-GPS time offset in seconds (adjusted_time = target_time + offset)
        :param max_gap_seconds: Maximum allowed time gap between target and GPS sample before falling back
        :param interpolate: Whether to linearly interpolate between closest surrounding samples
        :param default_coords: Default (lat, lon) to return if GPS data is missing or out of bounds
        :return: Tuple of (latitude, longitude)
        """
        if self.is_empty():
            return default_coords

        target_dt = parse_timestamp(target_time)
        adjusted_dt = target_dt + datetime.timedelta(seconds=offset_seconds)
        target_ts = adjusted_dt.timestamp()

        # Binary search for closest index
        idx = bisect_left(self.timestamps, target_ts)

        # Boundary cases
        if idx == 0:
            sample = self.samples[0]
            if abs(sample.timestamp.timestamp() - target_ts) <= max_gap_seconds:
                return round(sample.latitude, 6), round(sample.longitude, 6)
            return default_coords

        if idx >= len(self.samples):
            sample = self.samples[-1]
            if abs(sample.timestamp.timestamp() - target_ts) <= max_gap_seconds:
                return round(sample.latitude, 6), round(sample.longitude, 6)
            return default_coords

        # Surrounding samples
        s_prev = self.samples[idx - 1]
        s_next = self.samples[idx]

        t_prev = s_prev.timestamp.timestamp()
        t_next = s_next.timestamp.timestamp()

        diff_prev = abs(target_ts - t_prev)
        diff_next = abs(t_next - target_ts)

        # Check if interpolation is possible and requested
        if interpolate and t_next > t_prev:
            total_span = t_next - t_prev
            if total_span <= max_gap_seconds:
                alpha = (target_ts - t_prev) / total_span
                interp_lat = s_prev.latitude + alpha * (s_next.latitude - s_prev.latitude)
                interp_lon = s_prev.longitude + alpha * (s_next.longitude - s_prev.longitude)
                return round(interp_lat, 6), round(interp_lon, 6)

        # Nearest neighbor check
        closest_sample = s_prev if diff_prev <= diff_next else s_next
        min_diff = min(diff_prev, diff_next)

        if min_diff <= max_gap_seconds:
            return round(closest_sample.latitude, 6), round(closest_sample.longitude, 6)

        return default_coords
