# UrbanSense — SIH 2026 Prototype Demonstration Guide

This guide details how to run the zero-cost local demonstration of the **UrbanSense (SIH26124) Pothole Detection MVP**.

---

## 1. Demonstration Overview & Required Pipeline Stages

The UrbanSense SIH demonstration proves the complete 13-point target architecture:

1. **Road Video Replay**: Public-bus simulation video ([`data/sample/test_video.mp4`](../data/sample/test_video.mp4)) is replayed.
2. **YOLOv8 Detection**: Single-class detector identifies road pothole defects frame by frame.
3. **Bounding Box Visualization**: Bounding box pixel coordinates (`x1`, `y1`, `x2`, `y2`) are extracted.
4. **ByteTrack Association**: Multi-object tracker assigns persistent `track_id` values across frames.
5. **GPS Telemetry Sync**: Time-series GPS synchronizer associates latitude/longitude coordinates from bus telemetry (`data/sample/sample_gps.csv`).
6. **Kafka Event Streaming**: Schema-validated JSON events are published to Kafka/Redpanda topic `pothole-events`.
7. **FastAPI Ingestion**: Backend consumer validates events against [`contracts/event.schema.json`](../contracts/event.schema.json).
8. **Spatial & Temporal Fusion**: PostGIS spatial gate matches sightings within 15 meters on the same road segment across a rolling 14-day window.
9. **Confidence Scoring**: Confidence increases dynamically with corroborating sightings:
   $$\text{confidence} = \min(1.0, \text{base\_conf} + 0.10 \times (\text{sightings} - 1) + 0.05 \times \text{viewpoints})$$
10. **PostGIS Persistence**: Qualifying sightings are promoted to `status="verified"` and stored in PostgreSQL/PostGIS.
11. **WebSocket Broadcast**: Real-time push notification is emitted over `WS /api/v1/live-feed`.
12. **React Map Update**: Leaflet map automatically updates markers without requiring a page refresh.
13. **Incident Inspection Panel**: Displays full incident metadata:
    - **Confidence Score** (%)
    - **Sighting Count**
    - **First Seen Timestamp**
    - **Last Seen Timestamp**
    - **Location** (Latitude/Longitude & Road Segment ID)
    - **Representative Image Reference**

---

## 2. Prerequisites

- **Operating System**: macOS or Linux
- **Python**: Python 3.9+ with virtualenv support
- **Node.js**: Node.js 18+ and npm
- **Database (Local)**: PostgreSQL with PostGIS extension (Port 5432)
- **Message Broker (Local)**: Apache Kafka or Redpanda (Port 9092)

*Note: For standalone local evaluation environments where PostgreSQL or Kafka containers are stopped, the pipeline operates in clean deterministic fallback/mock mode with zero crashes.*

---

## 3. Startup & Environment Preparation

### Step 1: Environment File Setup
Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

### Step 2: Backend Database Migration & Services Startup
Run database migrations and start backend services:

```bash
# Terminal 1: Apply PostGIS schema migrations
alembic -c backend/alembic.ini upgrade head

# Terminal 1: Start FastAPI server (Port 8000)
uvicorn app.main:app --app-dir backend --reload --port 8000
```

```bash
# Terminal 2: Start Ingestion Consumer
PYTHONPATH=backend python3 -m app.services.event_consumer
```

### Step 3: Frontend Dashboard Startup
Start the React Leaflet dashboard:

```bash
# Terminal 3: Launch React Vite dev server (Port 5173)
cd frontend && npm install && npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 4. Single Demo Command

To run the complete deterministic route replay demonstration, open a terminal in the repository root and execute:

```bash
./scripts/replay.sh
```

---

## 5. Expected Output & Logs

### Terminal Log Output
Executing `./scripts/replay.sh` outputs step-by-step trace lines for each pipeline stage:

```text
==========================================================
      UrbanSense End-to-End Route Replay System           
==========================================================
[System Check] Verifying PostgreSQL / PostGIS database...
[System Check] Verifying Kafka / Redpanda broker at localhost:9092...
[Replay] Replaying simulated bus route video + GPS telemetry...

--- UrbanSense Deterministic Replay Pipeline ---
[ML] Starting YOLOv8 + ByteTrack inference on 'test_video.mp4'...
[ML] Processed 150 frames (5.0s). Tracked 20 sightings.
[ML] Synchronizing GPS track...
[ML] Loaded 6 GPS samples from 'sample_gps.csv'.
[ML] Generated 4 schema-compliant pothole event packets.

[ML] Frame 15
[ML] Pothole detected confidence=0.90 track=1
[ML] GPS=(12.975401, 77.602201)
[Kafka] Event published event_id=edb3d521-0779-45c6-9b85-741934bbe5b9
[Backend] Event consumed event_id=edb3d521-0779-45c6-9b85-741934bbe5b9
[Fusion] New candidate incident created at (12.975401, 77.602201)
[Fusion] Sightings=1 confidence=0.90

[ML] Frame 45
[ML] Pothole detected confidence=0.70 track=2
[ML] GPS=(12.975403, 77.602203)
[Kafka] Event published event_id=2f2802da-cf63-4c25-b8e4-314f960e4a8a
[Backend] Event consumed event_id=2f2802da-cf63-4c25-b8e4-314f960e4a8a
[Fusion] Existing incident found within 15m
[Fusion] Sightings=2 confidence=0.85
[Fusion] Incident verified
[WebSocket] Incident broadcast
[Frontend] Incident displayed

==========================================================
       UrbanSense End-to-End Route Replay Complete        
==========================================================
```

### Dashboard UI Output
- A new marker pops up on the Leaflet map at coordinates `12.9754, 77.6022` (MG Road / Central Bengaluru).
- Clicking the marker opens the **Incident Inspector Panel** displaying:
  - **Status**: Verified
  - **Confidence**: 85%
  - **Sightings**: 2 detections
  - **First seen**: 26 Sep 2026, 08:42
  - **Last seen**: 26 Sep 2026, 08:43
  - **Coordinates**: 12.9754, 77.6022
  - **Representative image**: Reference pothole evidence frame.

---

## 6. Architecture Explanation

The UrbanSense pipeline transforms unstructured, noisy street-view video into clean spatial intelligence:

1. **Ingestion & Perception (`ml/`)**: Bus-mounted video streams are evaluated by a YOLOv8 single-class detector trained on road damage datasets. ByteTrack assigns track IDs to avoid counting the same pothole multiple times in consecutive frames of the same bus pass.
2. **Spatial Alignment (`ml/gps/`)**: Video frame timestamps are synchronized against bus GPS logs using linear interpolation.
3. **Kafka Event Streaming**: Detections are emitted as strict JSON packets to the `pothole-events` broker topic.
4. **Spatial-Temporal Fusion (`backend/app/services/fusion/`)**:
   - **Spatial Gate**: Uses PostGIS `ST_DWithin` to snap sightings on the same road segment within a 15-meter radius.
   - **Temporal Gate**: Retains corroborating sightings within a rolling 14-day window.
   - **Confidence Engine**: Dynamically calculates confidence scores based on sighting frequency and camera viewpoints.
5. **Real-time Map Delivery (`frontend/`)**: Qualifying verified incidents ($\text{confidence} \ge 0.6$ or $\text{sightings} \ge 2$) are pushed over WebSockets to update the dashboard instantly.

---

## 7. Optional Public Showcase (Vercel Free Tier)

While the core SIH demonstration runs 100% locally with zero paid infrastructure dependencies, the React frontend can optionally be deployed to Vercel's free tier for public showcase presentations.

### Steps for Vercel Free Tier Showcase
1. Install Vercel CLI or connect your GitHub repository to [Vercel](https://vercel.com).
2. Configure project root directory to `frontend/`.
3. Set environment variable:
   - `VITE_API_BASE_URL=https://your-public-backend-url/api/v1`
4. Deploy:
   ```bash
   cd frontend
   npx vercel --prod
   ```
*Note: Public deployment is strictly optional for showcase presentations and is not required for the core SIH evaluation demo.*

---

## 8. Troubleshooting

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| `Kafka broker offline` warning | Local Kafka/Redpanda service stopped. | Replay automatically falls back to dry-run mode. To start Kafka: `docker-compose up -d kafka` or start Redpanda locally. |
| `pg_isready not found` | PostgreSQL client CLI missing from system PATH. | Safe to ignore; replay runs with local in-memory gate fallback. |
| Map not showing markers | `VITE_API_BASE_URL` mismatch. | Ensure FastAPI backend is running on `http://localhost:8000` and `VITE_API_BASE_URL` is set accordingly in `frontend/.env`. |
| Python import errors | Missing virtual environment packages. | Activate virtual environment (`source venv/bin/activate`) and run `pip install -r backend/requirements.txt`. |
