# UrbanSense — Pothole Detection MVP (SIH 2026)

UrbanSense (SIH26124) transforms public-bus video telemetry and synchronized GPS tracks into corroboration-scored pothole incidents displayed on an interactive real-time map.

---

## 1. Target Architecture

```text
Simulated Road Video + GPS Telemetry
               ↓
YOLOv8 Pothole Detector       (ml/inference/detect.py)
               ↓
ByteTrack Object Tracker       (ml/tracking/tracker.py)
               ↓
Event Packet Builder          (ml/event_builder/builder.py)
               ↓
Kafka / Redpanda Broker       (pothole-events topic)
               ↓
FastAPI Ingestion & Validation (backend/app/services/event_processor.py)
               ↓
PostGIS Spatial Gate (15m)     (backend/app/services/fusion/spatial.py)
               ↓
14-Day Temporal Gate          (backend/app/services/fusion/temporal.py)
               ↓
Confidence Scorer & Threshold (backend/app/services/fusion/confidence.py)
               ↓
PostgreSQL / PostGIS Storage   (backend/app/models/)
               ↓
FastAPI REST + WebSocket Feed (backend/app/api/routes/incidents.py)
               ↓
React + Leaflet Map Dashboard  (frontend/src/map/IncidentMap.tsx)
```

---

## 2. Workstream Ownership Boundaries

- **`ml/`**: Owning model training, dataset preparation, YOLOv8 inference, ByteTrack multi-object tracking, GPS synchronization, event building, and Kafka publishing.
- **`backend/`**: Owning FastAPI web server, Kafka consumer, PostGIS fusion engine (spatial/temporal gates), SQL models, REST endpoints, and WebSocket broadcasting.
- **`frontend/`**: Owning React dashboard (built with TanStack Start/Vite, Tailwind CSS, Leaflet maps) visualizing verified incidents and consuming WebSocket live feeds.
- **`contracts/`**: Shared machine-readable JSON Schemas ([`event.schema.json`](contracts/event.schema.json), [`incident.schema.json`](contracts/incident.schema.json)) and OpenAPI spec ([`api.yaml`](contracts/api.yaml)).

---

## 3. Environment Variables & Configuration

Copy `.env.example` to `.env` before running:

```ini
# PostgreSQL + PostGIS
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=urbansense
POSTGRES_PASSWORD=urbansense
POSTGRES_DB=urbansense

# Kafka / Redpanda
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=pothole-events
KAFKA_CONSUMER_GROUP=urbansense-backend-consumer

# Backend FastAPI
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Frontend React
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 4. Setup & Local Installation

### Prerequisites
- Python 3.9+
- Node.js 18+ and npm
- PostgreSQL with PostGIS extension (optional for dry-run/mock testing)
- Kafka or Redpanda broker (optional for dry-run/mock testing)

### Step-by-Step Installation

```bash
# 1. Clone repository
git clone https://github.com/07Prxshant/SIH26-indecisive-beetles.git
cd SIH26-indecisive-beetles

# 2. Python backend & ML setup
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 3. Frontend setup
cd frontend
npm install
cd ..
```

---

## 5. Model Training (ML)

To prepare datasets and train the single-class YOLOv8 pothole detector:

```bash
# Prepare single-class RDD2022 YOLO dataset
python3 -m ml.data.prepare_dataset --output-dir ml/datasets/rdd2022

# Validate dataset annotations
python3 ml/scripts/validate_dataset.py --dataset-dir ml/datasets/rdd2022

# Train YOLOv8 pothole detector
python3 -m ml.training.train \
    --data ml/config/train_config.yaml \
    --model yolov8n.pt \
    --epochs 50 \
    --imgsz 640

# Evaluate model performance
python3 -m ml.training.evaluate --weights ml/models/best.pt --data ml/config/train_config.yaml
```

---

## 6. Inference & Tracking (ML)

Run standalone video inference with ByteTrack multi-object tracking:

```bash
python3 -m ml.inference.detect \
    --video data/sample/test_video.mp4 \
    --model ml/models/best.pt \
    --conf 0.25 \
    --output-json ml/runs/detect/detections.json \
    --output-video ml/runs/detect/annotated.mp4
```

---

## 7. Replay System

Execute the end-to-end deterministic route replay:

```bash
# Executable replay runner script
./scripts/replay.sh
```

Or via direct module invocation:

```bash
python3 -m ml.inference.replay \
    --video data/sample/test_video.mp4 \
    --gps data/sample/sample_gps.csv \
    --broker localhost:9092 \
    --topic pothole-events \
    --conf 0.25
```

---

## 8. Backend API & WebSocket Specifications

### REST Endpoints
- `GET /api/v1/health`: Returns service health status (`{"status": "ok"}`).
- `GET /api/v1/incidents`: Retrieves list of candidate or verified incidents. Supports query filters: `status` (`candidate`|`verified`), `min_lat`, `max_lat`, `min_lon`, `max_lon`.
- `GET /api/v1/incidents/{incident_id}`: Fetches details for a specific incident by UUID.

### Real-Time WebSocket Endpoint
- `GET /api/v1/live-feed`: Upgrades to WebSocket. Pushes live `incident_created` messages whenever a candidate incident is promoted to `verified` by the fusion engine:
  ```json
  {
    "type": "incident_created",
    "incident": {
      "incident_id": "79af17b5-f0ea-42ec-a708-df9e55ace4e0",
      "latitude": 12.9754,
      "longitude": 77.6022,
      "road_segment_id": "local-grid:12.9754:77.6022",
      "confidence": 0.85,
      "sighting_count": 2,
      "first_seen": "2026-09-26T08:42:00Z",
      "last_seen": "2026-09-26T08:43:00Z",
      "status": "verified"
    }
  }
  ```

---

## 9. Frontend Dashboard

Run the React Leaflet dashboard locally:

```bash
cd frontend
npm run dev
```

The application opens at `http://localhost:5173`. Key dashboard features:
- **Interactive Leaflet Map**: Displays color-coded markers for verified incidents (green/amber/red based on confidence & severity).
- **Auto-Reconnecting WebSocket Feed**: Instantly updates map markers without manual refresh when new incidents are verified.
- **Incident Inspector Sidebar**: Displays sighting details, timestamps, and road segment identifiers.

---

## 10. End-to-End Demo Instructions

Follow these steps for a complete live demonstration:

1. **Start PostGIS & Kafka**:
   Ensure local PostgreSQL with PostGIS extension and Kafka/Redpanda broker are running on ports `5432` and `9092`.
2. **Apply Database Migrations**:
   ```bash
   alembic -c backend/alembic.ini upgrade head
   ```
3. **Start FastAPI Backend**:
   ```bash
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
4. **Start Ingestion Consumer**:
   ```bash
   PYTHONPATH=backend python3 -m app.services.event_consumer
   ```
5. **Start React Frontend**:
   ```bash
   cd frontend && npm run dev
   ```
6. **Trigger Deterministic Replay**:
   ```bash
   ./scripts/replay.sh
   ```
7. **Observe Live Output**:
   - Terminal logs display step-by-step `[ML]`, `[Kafka]`, `[Backend]`, `[Fusion]`, and `[WebSocket]` trace lines.
   - Frontend map at `http://localhost:5173` dynamically adds live verified incident markers without page reloading.
