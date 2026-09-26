#!/usr/bin/env python3
"""
Unit tests for UrbanSense Kafka Producer (ml/producer).
"""

import os
import unittest
import uuid

from ml.producer.kafka_producer import PotholeKafkaProducer, KafkaProducerConfig


class TestKafkaProducer(unittest.TestCase):

    def setUp(self):
        self.valid_event = {
            "event_id": str(uuid.uuid4()),
            "class": "pothole",
            "bbox": {"x1": 100.0, "y1": 250.0, "x2": 220.0, "y2": 330.0},
            "confidence": 0.87,
            "gps_lat": 37.7749,
            "gps_lon": -122.4194,
            "timestamp": "2026-09-27T10:00:00Z",
            "track_id": "1",
            "source_id": "bus_42",
            "frame_id": 15
        }

    def test_config_defaults_and_env_overrides(self):
        config = KafkaProducerConfig.from_env_or_args(
            broker="test-broker:9092",
            topic="custom-topic"
        )
        self.assertEqual(config.bootstrap_servers, "test-broker:9092")
        self.assertEqual(config.topic, "custom-topic")

        # Test env variable fallbacks
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "env-broker:9092"
        os.environ["KAFKA_TOPIC"] = "env-topic"
        try:
            config_env = KafkaProducerConfig.from_env_or_args()
            self.assertEqual(config_env.bootstrap_servers, "env-broker:9092")
            self.assertEqual(config_env.topic, "env-topic")
        finally:
            del os.environ["KAFKA_BOOTSTRAP_SERVERS"]
            del os.environ["KAFKA_TOPIC"]

    def test_publish_valid_event_dry_run(self):
        producer = PotholeKafkaProducer(
            bootstrap_servers="localhost:9092",
            topic="pothole-events",
            dry_run=True
        )

        success = producer.publish_event(self.valid_event)
        self.assertTrue(success)
        self.assertEqual(len(producer.published_events), 1)
        self.assertEqual(producer.published_events[0]["event_id"], self.valid_event["event_id"])
        producer.close()

    def test_publish_invalid_event_rejection(self):
        producer = PotholeKafkaProducer(dry_run=True)

        invalid_event = self.valid_event.copy()
        invalid_event["class"] = "invalid_class"

        with self.assertRaises(ValueError):
            producer.publish_event(invalid_event)

        producer.close()

    def test_context_manager_and_batch_publish(self):
        evt1 = self.valid_event.copy()
        evt1["event_id"] = str(uuid.uuid4())
        evt2 = self.valid_event.copy()
        evt2["event_id"] = str(uuid.uuid4())
        evt2["track_id"] = "2"

        with PotholeKafkaProducer(dry_run=True) as producer:
            count = producer.publish_events_batch([evt1, evt2])
            self.assertEqual(count, 2)
            self.assertEqual(len(producer.published_events), 2)

        # Producer closed cleanly upon exiting context manager
        self.assertTrue(producer._closed)


if __name__ == "__main__":
    unittest.main()
