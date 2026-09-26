# UrbanSense — Pothole Detection MVP

UrbanSense (SIH26124) turns simulated road video plus GPS into corroborated pothole incidents that can be explored on a map. It is a practical SIH 2026 prototype: the repository currently defines the shared boundaries only, not the ML, backend, or dashboard implementation.

## Architecture

```text
Simulated road video + GPS
  → YOLOv8 pothole detector → ByteTrack → geo-tagged event packet
  → Kafka/Redpanda topic: pothole-events → FastAPI ingestion → fusion engine
  → PostgreSQL + PostGIS → FastAPI REST + WebSocket → React dashboard
  → Leaflet/Mapbox map
```

The fusion engine snaps events to road segments, matches sightings within 15 metres on the same segment, evaluates a rolling 14-day window, and publishes an incident at the documented dashboard threshold. See [the architecture](docs/architecture.md).

## Three workstreams

- **ML** owns `/ml`: detector, ByteTrack, GPS association, and publishing conforming event packets.
- **Backend** owns `/backend`: FastAPI ingestion, Kafka/Redpanda consumption, PostGIS fusion, REST, and WebSocket delivery.
- **Frontend** owns `/frontend`: React dashboard and Leaflet/Mapbox incident visualization.

`/contracts` is shared. ML and Backend must coordinate contract changes there; Frontend consumes the verified incident API defined in the API contract.

## Local development

Copy `.env.example` to `.env`, then configure local PostgreSQL with PostGIS and Kafka or Redpanda. Each workstream will add its own runtime dependencies and commands. Read [development instructions](docs/development.md) before starting work.

## Repository structure

```text
backend/       FastAPI and fusion implementation (future)
frontend/      React dashboard implementation (future)
ml/            Detection and tracking implementation (future)
data/sample/   Small simulated demo inputs only
contracts/     Machine-readable event, incident, and REST contracts
docs/          Architecture, API, and development documentation
scripts/       Shared developer utilities
```

## Communication contracts

ML publishes one JSON event per tracked detection to `pothole-events`, following [the API contract](docs/api-contract.md). Backend validates and fuses those events, persists incidents in PostgreSQL/PostGIS, then exposes qualifying incidents through REST and WebSocket. Frontend reads only those verified incident payloads; it does not consume ML events directly.
