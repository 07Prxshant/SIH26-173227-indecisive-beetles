# Architecture

UrbanSense processes simulated public-bus video with accompanying GPS telemetry to create confidence-scored pothole incidents.

```text
Video + GPS → YOLOv8 detector → ByteTrack → Event packet builder
          → Redpanda/Kafka → FastAPI ingestion → PostGIS spatial gate
          → 14-day temporal gate → confidence scorer → verified incidents
          → REST + WebSocket → React + Leaflet/Mapbox dashboard
```

## Shared contracts

The ML producer and backend consumer exchange detection packets according to [`contracts/event.schema.json`](../contracts/event.schema.json). The backend publishes API responses using [`contracts/incident.schema.json`](../contracts/incident.schema.json); the HTTP surface is described by [`contracts/api.yaml`](../contracts/api.yaml).

The event contract is intentionally single-class: `class` must be `pothole`. Bounding boxes use pixel `x`, `y`, `width`, and `height` values. Timestamps are UTC ISO 8601 date-times. Optional image and frame references are opaque URI or object-store-key strings.

## Verification flow

1. The ML pipeline emits one event per tracked detection.
2. The backend groups geographically close events using PostGIS and checks supporting sightings over a 14-day interval.
3. The confidence scorer combines supporting evidence and emits an incident lifecycle state.
4. The dashboard consumes verified incidents via REST and live updates via WebSocket.

Spatial thresholds, temporal thresholds, and confidence weighting are backend implementation details; this foundation does not prescribe their exact values.
