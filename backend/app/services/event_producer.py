"""Utility for publishing valid pothole events to Kafka or Redpanda."""

from __future__ import annotations

import json
from typing import Any, Mapping

from kafka import KafkaProducer

from app.core.config import get_settings
from app.services.event_validation import EventContractValidator


class PotholeEventProducer:
    """Publish shared-contract event packets to the `pothole-events` topic."""

    def __init__(
        self,
        producer: KafkaProducer | None = None,
        validator: EventContractValidator | None = None,
    ) -> None:
        settings = get_settings()
        self._topic = settings.pothole_events_topic
        self._validator = validator or EventContractValidator()
        self._producer = producer or KafkaProducer(
            bootstrap_servers=settings.kafka_brokers.split(","),
            key_serializer=lambda value: value.encode("utf-8"),
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def publish(self, event: Mapping[str, Any]) -> Any:
        """Validate, publish, and return Kafka's delivery future."""
        payload = self._validator.validate(event)
        return self._producer.send(self._topic, key=payload["event_id"], value=payload)

    def close(self) -> None:
        """Flush buffered records before closing the Kafka/Redpanda client."""
        self._producer.flush()
        self._producer.close()
