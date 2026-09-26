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

## Run and test

```bash
uvicorn app.main:app --app-dir backend --reload
pytest backend/tests
```

The health check is available at `GET http://localhost:8000/health`.

## Shared contracts

Do not independently change the shared API shapes. The backend will consume ML event packets defined in `../contracts/event.schema.json` and eventually serve verified incidents described by `../contracts/incident.schema.json` and `../contracts/api.yaml`.
