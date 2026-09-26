# Architecture

UrbanSense (SIH26124) processes simulated road video with accompanying GPS telemetry to create confidence-scored pothole incidents.

```text
Simulated road video + GPS → YOLOv8 pothole detector → ByteTrack
→ Geo-tagged event packet → Kafka/Redpanda topic: pothole-events
→ FastAPI ingestion → Fusion engine → PostgreSQL + PostGIS
→ FastAPI REST + WebSocket → React dashboard → Leaflet/Mapbox map
```

## Shared contracts

The ML producer and backend consumer exchange detection packets according to [`contracts/event.schema.json`](../contracts/event.schema.json). The backend publishes API responses using [`contracts/incident.schema.json`](../contracts/incident.schema.json); the HTTP surface is described by [`contracts/api.yaml`](../contracts/api.yaml).

The event contract is intentionally single-class: `class` must be `pothole`. Bounding boxes use pixel `x1`, `y1`, `x2`, and `y2` values. Timestamps are UTC ISO 8601 date-times. `source_id` and `frame_id` make an event traceable to its video source; `image_ref` and `frame_ref` are optional stored-image references.

## Fusion logic

1. **Spatial gate:** snap/map each event to a road segment and match it only with events on the same segment within 15 metres, using PostGIS spatial distance.
2. **Temporal gate:** retain corroborating sightings in a rolling 14-day window.
3. **Confidence scorer:**

   ```text
   confidence = min(1.0, base_detector_conf
                    + 0.10 × (corroborating_sightings - 1)
                    + 0.05 × distinct_viewpoints)
   ```

4. **Dashboard threshold:** publish/surface an incident when `confidence >= 0.6` **or** `corroborating_sightings >= 2`.

Backend owns the fusion implementation; ML supplies the detector confidence and traceability fields needed to calculate and audit it. The backend determines distinct viewpoints from its available source metadata.
