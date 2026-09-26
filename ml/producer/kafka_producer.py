#!/usr/bin/env python3
"""
UrbanSense - Kafka / Redpanda Producer for Pothole Events

Publishes schema-validated pothole sighting event packets to the 'pothole-events' topic.
Features:
  - Configurable broker URL & topic
  - JSON serialization & contract schema validation
  - Retries & backoff configuration
  - Structured producer logging
  - Graceful shutdown & automatic flushing on exit
  - Seamless fallback / dry-run mode for offline testing
"""

import atexit
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.event_builder.validator import validate_event

# Configure module logger
logger = logging.getLogger("UrbanSenseKafkaProducer")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class KafkaProducerConfig:
    """Configuration settings for Kafka/Redpanda event producer."""
    bootstrap_servers: str = "localhost:9092"
    topic: str = "pothole-events"
    retries: int = 3
    retry_backoff_ms: int = 1000
    client_id: str = "urbansense-ml-producer"
    dry_run: bool = False

    @classmethod
    def from_env_or_args(
        cls,
        broker: Optional[str] = None,
        topic: Optional[str] = None,
        retries: Optional[int] = None,
        dry_run: bool = False
    ) -> "KafkaProducerConfig":
        """Builds configuration from explicit arguments or environment variable fallbacks."""
        env_broker = os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or os.environ.get("KAFKA_BROKER")
        env_topic = os.environ.get("KAFKA_TOPIC")

        servers = broker or env_broker or "localhost:9092"
        target_topic = topic or env_topic or "pothole-events"
        retry_cnt = retries if retries is not None else int(os.environ.get("KAFKA_RETRIES", "3"))

        return cls(
            bootstrap_servers=servers,
            topic=target_topic,
            retries=retry_cnt,
            dry_run=dry_run
        )


class PotholeKafkaProducer:
    """
    Kafka / Redpanda producer client for streaming UrbanSense pothole events.
    Validates each event against contracts/event.schema.json prior to publishing.
    """

    def __init__(
        self,
        config: Optional[KafkaProducerConfig] = None,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        dry_run: bool = False
    ):
        if config is None:
            self.config = KafkaProducerConfig.from_env_or_args(
                broker=bootstrap_servers,
                topic=topic,
                dry_run=dry_run
            )
        else:
            self.config = config

        self.producer = None
        self.is_mock = False
        self.published_events: List[Dict[str, Any]] = []
        self._closed = False

        self._init_producer()
        atexit.register(self.close)

    def _init_producer(self) -> None:
        """Initializes live Kafka producer driver if available and enabled."""
        if self.config.dry_run:
            logger.info("Kafka producer initialized in DRY-RUN mode.")
            self.is_mock = True
            return

        # Attempt importing confluent_kafka or kafka-python
        try:
            from kafka import KafkaProducer  # type: ignore

            servers = self.config.bootstrap_servers.split(",")
            self.producer = KafkaProducer(
                bootstrap_servers=servers,
                client_id=self.config.client_id,
                retries=self.config.retries,
                retry_backoff_ms=self.config.retry_backoff_ms,
                key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
                value_serializer=lambda v: json.dumps(v).encode("utf-8") if isinstance(v, dict) else v,
            )
            logger.info(f"Connected to Kafka broker(s) '{self.config.bootstrap_servers}' using kafka-python.")
            self.is_mock = False
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Unable to connect to Kafka brokers '{self.config.bootstrap_servers}': {e}. Falling back to mock/dry-run mode.")

        try:
            import confluent_kafka  # type: ignore

            conf = {
                "bootstrap.servers": self.config.bootstrap_servers,
                "client.id": self.config.client_id,
                "retries": self.config.retries,
                "retry.backoff.ms": self.config.retry_backoff_ms,
            }
            self.producer = confluent_kafka.Producer(conf)
            logger.info(f"Connected to Kafka broker(s) '{self.config.bootstrap_servers}' using confluent-kafka.")
            self.is_mock = False
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Unable to initialize confluent-kafka producer: {e}.")

        # Fallback to mock producer
        logger.info(f"Kafka client libraries not connected to live broker. Operating in fallback mock mode for topic '{self.config.topic}'.")
        self.is_mock = True

    def publish_event(
        self,
        event: Dict[str, Any],
        topic: Optional[str] = None
    ) -> bool:
        """
        Validates event against schema contract and publishes it to Kafka/Redpanda.

        :param event: Pothole event dictionary
        :param topic: Optional topic override (defaults to configured topic)
        :return: True if successfully published or queued
        """
        if self._closed:
            raise RuntimeError("Cannot publish event using a closed Kafka producer.")

        target_topic = topic or self.config.topic

        # 1. Schema contract validation
        is_valid, errors = validate_event(event)
        if not is_valid:
            logger.error(f"Event packet validation failed against contracts/event.schema.json: {errors}")
            raise ValueError(f"Event packet failed schema contract validation: {errors}")

        # 2. Key selection (use track_id or event_id as partition key)
        key_str = str(event.get("track_id") or event.get("event_id"))

        # 3. Publish with retry mechanism
        max_attempts = max(1, self.config.retries)
        backoff_sec = self.config.retry_backoff_ms / 1000.0

        for attempt in range(1, max_attempts + 1):
            try:
                if self.is_mock or self.producer is None:
                    # Mock / Dry-run publishing
                    self.published_events.append(event)
                    logger.info(
                        f"[KAFKA MOCK] Published event '{event['event_id']}' (track_id: '{event['track_id']}', "
                        f"lat: {event['gps_lat']}, lon: {event['gps_lon']}) to topic '{target_topic}'"
                    )
                    return True
                else:
                    # Live Kafka publish
                    if hasattr(self.producer, "send"):  # kafka-python
                        future = self.producer.send(target_topic, key=key_str, value=event)
                        record_metadata = future.get(timeout=10.0)
                        logger.info(
                            f"[KAFKA PRODUCER] Published event '{event['event_id']}' to topic '{record_metadata.topic}' "
                            f"[partition {record_metadata.partition} @ offset {record_metadata.offset}]"
                        )
                    else:  # confluent-kafka
                        payload = json.dumps(event).encode("utf-8")
                        key_bytes = key_str.encode("utf-8")
                        self.producer.produce(target_topic, key=key_bytes, value=payload)
                        self.producer.poll(0)
                        logger.info(f"[KAFKA PRODUCER] Queued event '{event['event_id']}' to topic '{target_topic}'")

                    self.published_events.append(event)
                    return True

            except Exception as e:
                logger.warning(f"Publish attempt {attempt}/{max_attempts} failed for event '{event['event_id']}': {e}")
                if attempt < max_attempts:
                    time.sleep(backoff_sec)
                else:
                    logger.error(f"Failed to publish event '{event['event_id']}' after {max_attempts} attempts.")
                    raise e

        return False

    def publish_events_batch(
        self,
        events: List[Dict[str, Any]],
        topic: Optional[str] = None
    ) -> int:
        """Publishes a batch of pothole events and returns the number of successfully published events."""
        count = 0
        for evt in events:
            if self.publish_event(evt, topic=topic):
                count += 1
        self.flush()
        return count

    def flush(self) -> None:
        """Flushes any buffered messages to the Kafka cluster."""
        if self.producer is not None:
            try:
                if hasattr(self.producer, "flush"):
                    self.producer.flush()
            except Exception as e:
                logger.warning(f"Error flushing Kafka producer: {e}")

    def close(self) -> None:
        """Flushes and closes the producer cleanly."""
        if not self._closed:
            self.flush()
            if self.producer is not None:
                try:
                    if hasattr(self.producer, "close"):
                        self.producer.close()
                except Exception as e:
                    logger.warning(f"Error closing Kafka producer: {e}")
            self._closed = True
            logger.info("Kafka producer shutdown cleanly.")

    def __enter__(self) -> "PotholeKafkaProducer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
