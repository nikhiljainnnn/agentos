"""
Kafka producer for agent event streaming.
Events are published asynchronously — never blocks the main flow.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Lazy import kafka to avoid startup failures if Kafka is not available
_producer = None
_kafka_available = True


def _get_producer():
    global _producer, _kafka_available
    if not _kafka_available:
        return None
    if _producer is None:
        try:
            from kafka import KafkaProducer
            from gateway.config import get_settings
            settings = get_settings()
            _producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                acks="all",
                retries=3,
                request_timeout_ms=5000,
            )
        except Exception as e:
            logger.warning("kafka_unavailable", error=str(e))
            _kafka_available = False
            return None
    return _producer


async def publish_event(topic: str, payload: Dict[str, Any]) -> bool:
    """
    Publish event to Kafka topic. Non-blocking — failures are logged, not raised.
    """
    enriched = {
        **payload,
        "timestamp": datetime.utcnow().isoformat(),
    }

    def _send():
        producer = _get_producer()
        if producer is None:
            return False
        try:
            producer.send(topic, value=enriched)
            producer.flush(timeout=2)
            return True
        except Exception as e:
            logger.error("kafka_publish_failed", topic=topic, error=str(e))
            return False

    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send)
