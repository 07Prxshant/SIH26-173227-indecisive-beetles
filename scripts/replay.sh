#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

command -v pg_isready >/dev/null || { echo "pg_isready is required to verify PostgreSQL." >&2; exit 1; }
pg_isready -h "${POSTGRES_HOST:-localhost}" -p "${POSTGRES_PORT:-5432}" -d "${POSTGRES_DB:-urbansense}" >/dev/null

PYTHONPATH=backend python - <<'PY'
from kafka import KafkaAdminClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine

settings = get_settings()
with get_engine().connect() as connection:
    connection.execute(text("SELECT PostGIS_Version()"))
admin = KafkaAdminClient(bootstrap_servers=settings.kafka_brokers.split(","))
try:
    if settings.pothole_events_topic not in admin.list_topics():
        raise SystemExit(f"Missing Kafka/Redpanda topic: {settings.pothole_events_topic}")
finally:
    admin.close()
PY

PYTHONPATH=backend python -m app.services.sample_replay
