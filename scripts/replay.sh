#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

echo "=========================================================="
echo "      UrbanSense End-to-End Route Replay System           "
echo "=========================================================="

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-urbansense}"
KAFKA_BROKER="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

PYTHON_CMD="python3"
if [ -x "/Users/prashantkumargupta/.gemini/antigravity-ide/scratch/venv/bin/python3" ]; then
    PYTHON_CMD="/Users/prashantkumargupta/.gemini/antigravity-ide/scratch/venv/bin/python3"
fi

# 1. Check PostgreSQL/PostGIS status
echo "[System Check] Verifying PostgreSQL / PostGIS database..."
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -d "$POSTGRES_DB" >/dev/null 2>&1; then
        echo "[System Check] PostgreSQL is ACTIVE at $POSTGRES_HOST:$POSTGRES_PORT."
    else
        echo "[System Check] PostgreSQL is offline on port $POSTGRES_PORT. Using local memory mock/fallback mode."
    fi
else
    echo "[System Check] pg_isready client not found. Operating with fallback memory gate."
fi

# 2. Check Kafka/Redpanda broker status
echo "[System Check] Verifying Kafka / Redpanda broker at $KAFKA_BROKER..."
PYTHONPATH=backend "$PYTHON_CMD" - <<PY || echo "[System Check] Kafka broker offline or unreachable. Producer operating in dry-run mode."
from kafka import KafkaAdminClient
import sys

try:
    admin = KafkaAdminClient(bootstrap_servers="$KAFKA_BROKER", request_timeout_ms=2000)
    topics = admin.list_topics()
    admin.close()
    print(f"[System Check] Kafka is ACTIVE. Connected to broker $KAFKA_BROKER (topics: {len(topics)}).")
except Exception as e:
    sys.exit(1)
PY

# 3. Trigger Deterministic ML Replay Pipeline
VIDEO_INPUT="${1:-data/sample/test_video.mp4}"
GPS_INPUT="${2:-data/sample/sample_gps.csv}"

echo "[Replay] Replaying simulated bus route video + GPS telemetry..."
echo "[Replay] Input Video: $VIDEO_INPUT"
echo "[Replay] Input GPS  : $GPS_INPUT"

PYTHONPATH=. "$PYTHON_CMD" -m ml.inference.replay \
    --video "$VIDEO_INPUT" \
    --gps "$GPS_INPUT" \
    --broker "$KAFKA_BROKER" \
    --topic "pothole-events" \
    --conf 0.25 \
    --mock-inference

echo "=========================================================="
echo "       UrbanSense End-to-End Route Replay Complete        "
echo "=========================================================="
