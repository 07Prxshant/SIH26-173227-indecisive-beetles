"""Kafka/Redpanda consumer for idempotent pothole-event ingestion."""

from __future__ import annotations

import logging
import json
import time
from typing import Any

from kafka import KafkaConsumer, TopicPartition

from app.core.config import get_settings
from app.services.event_processor import EventProcessor
from app.services.event_validation import EventValidationError

logger = logging.getLogger(__name__)


class PotholeEventConsumer:
    """Consume `pothole-events`, validate them, and persist raw sightings."""

    def __init__(self, consumer: KafkaConsumer | None = None, processor: EventProcessor | None = None) -> None:
        settings = get_settings()
        self._processor = processor or EventProcessor()
        self._consumer = consumer or KafkaConsumer(
            settings.pothole_events_topic,
            bootstrap_servers=settings.kafka_brokers.split(","),
            group_id=settings.kafka_consumer_group,
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )

    def consume_forever(self) -> None:
        """Process records; invalid records are committed, transient failures are retried."""
        while True:
            for message in self._consumer:
                try:
                    created = self._processor.process(message.value)
                except EventValidationError as error:
                    logger.warning(
                        "Discarding invalid pothole event at %s:%s:%s: %s",
                        message.topic,
                        message.partition,
                        message.offset,
                        error,
                    )
                    self._consumer.commit()
                    continue
                except Exception:
                    logger.exception(
                        "Pothole event processing failed at %s:%s:%s; retrying without commit",
                        message.topic,
                        message.partition,
                        message.offset,
                    )
                    self._consumer.seek(TopicPartition(message.topic, message.partition), message.offset)
                    time.sleep(1)
                    break

                logger.info(
                    "Processed pothole event %s at %s:%s:%s (%s)",
                    message.value["event_id"],
                    message.topic,
                    message.partition,
                    message.offset,
                    "created" if created else "duplicate",
                )
                self._consumer.commit()


def run_consumer() -> None:
    """Run the configured local Kafka/Redpanda consumer process."""
    PotholeEventConsumer().consume_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_consumer()
