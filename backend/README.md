# UrbanSense Backend

This workstream owns FastAPI ingestion, fusion, persistence, REST, and WebSocket delivery. Only the FastAPI foundation and health endpoint are implemented at this stage.

## Local setup

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

Copy the repository `.env.example` to `.env` before running locally. Configuration is read from environment variables, with the `URBANSENSE_` prefix for application settings. `URBANSENSE_CORS_ORIGINS` accepts a JSON array, for example `['http://localhost:5173']` represented as valid JSON: `["http://localhost:5173"]`.

## PostgreSQL + PostGIS

Run PostgreSQL with the PostGIS extension locally. The backend reads the existing `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_PORT` values from the repository `.env`; `POSTGRES_HOST` defaults to `localhost`. Alternatively, set `URBANSENSE_DATABASE_URL` to a complete SQLAlchemy URL such as `postgresql+psycopg://urbansense:change-me@localhost:5432/urbansense`.

Initialize or upgrade the local schema from the repository root:

```bash
alembic -c backend/alembic.ini upgrade head
```

The migration enables PostGIS and creates `raw_sightings` and `verified_incidents`. To run the optional live database integration test, provide an isolated `URBANSENSE_TEST_DATABASE_URL` database and run `pytest backend/tests -m integration`.

## Kafka or Redpanda ingestion

Run Kafka or Redpanda locally and set `KAFKA_BROKERS` (default: `localhost:9092`) and `EVENT_TOPIC` (default: `pothole-events`) in `.env`. Start the consumer from the repository root after applying the database migration:

```bash
PYTHONPATH=backend python -m app.services.event_consumer
```

`PotholeEventProducer` is a reusable utility for local replay or ML integration. Both producer and consumer validate messages against `../contracts/event.schema.json`. Invalid records are logged and committed without persistence; database failures are not committed and are retried. `event_id` is unique in `raw_sightings`, so replayed records are idempotent.

## Run and test

```bash
uvicorn app.main:app --app-dir backend --reload
pytest backend/tests
```

The health check is available at `GET http://localhost:8000/health`.

## Shared contracts

Do not independently change the shared API shapes. The backend will consume ML event packets defined in `../contracts/event.schema.json` and eventually serve verified incidents described by `../contracts/incident.schema.json` and `../contracts/api.yaml`.
