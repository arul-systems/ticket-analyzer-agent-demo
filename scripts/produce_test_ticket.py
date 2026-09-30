"""Manual test helper: read the local tickets.json and publish every full
ticket record to the Kafka topic the agent listens on.

Works against either a local broker (KAFKA_SECURITY_PROTOCOL=PLAINTEXT, the
default) or a GCP Managed Service for Apache Kafka cluster
(KAFKA_SECURITY_PROTOCOL=SASL_SSL), which requires OAUTHBEARER auth using
Application Default Credentials instead of plaintext.

Usage:
    uv run python scripts/produce_test_ticket.py
"""

import json

from kafka import KafkaProducer

from agent.config import settings
from agent.kafka.gcp_oauth import GcpOAuthTokenProvider


def _build_producer() -> KafkaProducer:
    kwargs = {
        "bootstrap_servers": settings.kafka_bootstrap_servers,
        "security_protocol": settings.kafka_security_protocol,
        "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
    }
    if settings.kafka_security_protocol == "SASL_SSL":
        kwargs["sasl_mechanism"] = "OAUTHBEARER"
        kwargs["sasl_oauth_token_provider"] = GcpOAuthTokenProvider()
    return KafkaProducer(**kwargs)


def main() -> None:
    with settings.tickets_store_path.open("r") as f:
        tickets = json.load(f)

    producer = _build_producer()
    for ticket_id, ticket_data in tickets.items():
        producer.send(settings.kafka_topic, ticket_data)
        print(f"Published ticket_id={ticket_id} to topic={settings.kafka_topic}")
    producer.flush()


if __name__ == "__main__":
    main()
