# API Contract

This document defines the shared boundary between the ML and Backend workstreams and the verified-incident boundary consumed by Frontend. Contract changes require coordination between affected workstreams.

## ML → Backend event packet

ML publishes a JSON message for each ByteTrack pothole detection to the Kafka/Redpanda topic `pothole-events`.

```json
{
  "event_id": "0d2aeae0-d453-4d48-a2d3-30b3bf50b28a",
  "class": "pothole",
  "bbox": {
    "x1": 0,
    "y1": 0,
    "x2": 0,
    "y2": 0
  },
  "confidence": 0.0,
  "gps_lat": 0.0,
  "gps_lon": 0.0,
  "timestamp": "2026-09-26T12:00:00Z",
  "track_id": "track-001",
  "viewpoint_id": "bus-12-front"
}
```

| Field | Type | Rules |
| --- | --- | --- |
| `event_id` | UUID string | Unique per emitted detection event. |
| `class` | string | Always `pothole` in this MVP. |
| `bbox` | object | Pixel coordinates: `x1`, `y1`, `x2`, `y2`. |
| `confidence` | number | Detector confidence in the inclusive range 0–1. |
| `gps_lat`, `gps_lon` | number | WGS84 latitude/longitude. |
| `timestamp` | RFC 3339 date-time | UTC capture/detection time. |
| `track_id` | string | ByteTrack identity within the stream. |
| `viewpoint_id` | string | Independent camera, bus, or capture-pass identity. |

The canonical machine-readable schema is [`../contracts/event.schema.json`](../contracts/event.schema.json).

## Backend → Frontend verified incident API

Backend exposes dashboard-visible incidents through `GET /incidents`, `GET /incidents/{incident_id}`, and WebSocket `GET /ws/incidents` (upgraded to WebSocket). The same incident object is returned by REST and sent as one WebSocket message.

```json
{
  "incident_id": "79af17b5-f0ea-42ec-a708-df9e55ace4e0",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "road_segment_id": "road-segment-42",
  "confidence": 0.7,
  "sighting_count": 2,
  "distinct_viewpoints": 1,
  "first_seen": "2026-09-20T08:30:00Z",
  "last_seen": "2026-09-21T09:00:00Z",
  "status": "published",
  "representative_image": "optional-image-reference"
}
```

`representative_image` is optional. A `published` incident must satisfy `confidence >= 0.6` or `sighting_count >= 2`; the latter is the corroborating-sightings count from the fusion engine. The canonical machine-readable schema is [`../contracts/incident.schema.json`](../contracts/incident.schema.json), and the OpenAPI document is [`../contracts/api.yaml`](../contracts/api.yaml).
