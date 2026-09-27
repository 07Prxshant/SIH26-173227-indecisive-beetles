"""Kafka/Redpanda consumer for idempotent pothole-event ingestion."""

from __future__ import annotations

import logging
import json
import time
from typing import Any, Mapping
from uuid import UUID

from kafka import KafkaConsumer, TopicPartition

from app.core.config import get_settings
from app.services.event_processor import EventProcessor
from app.services.event_validation import EventValidationError
from app.services.fusion.persistence import SqlAlchemyFusionService
from app.services.road_segment import GridRoadSegmentResolver

logger = logging.getLogger(__name__)


class PotholeEventConsumer:
    """Consume `pothole-events`, validate them, and persist raw sightings."""

    def __init__(
        self,
        consumer: KafkaConsumer | None = None,
        processor: EventProcessor | None = None,
        fusion_service: SqlAlchemyFusionService | None = None,
        road_segment_resolver: GridRoadSegmentResolver | None = None,
    ) -> None:
        settings = get_settings()
        self._processor = processor or EventProcessor()
        self._fusion_service = fusion_service or SqlAlchemyFusionService()
        self._road_segment_resolver = road_segment_resolver or GridRoadSegmentResolver()
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
                    created = self.process_event(message.value)
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

    def process_event(self, event: Mapping[str, Any]) -> bool:
        """Persist one ML packet and immediately route new sightings into fusion."""
        created = self._processor.process(event)
        if created:
            self._fusion_service.fuse_raw_sighting(
                UUID(str(event["event_id"])), self._road_segment_resolver.resolve(event)
            )
        return created


def run_consumer() -> None:
    """Run the configured local Kafka/Redpanda consumer process."""
    PotholeEventConsumer().consume_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_consumer()
