# UrbanSense — Pothole Detection MVP

UrbanSense turns simulated public-bus video and GPS telemetry into reviewed pothole incidents. This repository is the shared foundation for the SIH 2026 prototype.

## Repository layout

| Directory | Responsibility |
| --- | --- |
| `backend/` | FastAPI ingestion, spatial/temporal gating, and incident APIs |
| `frontend/` | React map dashboard |
| `ml/` | YOLOv8 detection, ByteTrack, and event packet production |
| `contracts/` | Versioned cross-service event, incident, and HTTP contracts |
| `infra/` | Docker Compose and service configuration |
| `data/sample/` | Small, non-sensitive demo inputs only |
| `docs/` | Architecture and developer documentation |
| `scripts/` | Local developer utilities |

See [architecture documentation](docs/architecture.md) for the MVP flow and [development instructions](docs/development.md) to get started.

## Status

This initial commit establishes shared interfaces only. ML, backend, and frontend implementations intentionally have not been added yet.
