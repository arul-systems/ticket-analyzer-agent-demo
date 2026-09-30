"""Manual test helper: read data/tickets.json and publish every full ticket
record to the Kafka topic the agent listens on.

Usage:
    uv run python scripts/produce_test_ticket.py
"""

import json

from kafka import KafkaProducer

from agent.config import settings


def main() -> None:
    with settings.tickets_store_path.open("r") as f:
        tickets = json.load(f)

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    for ticket_id, ticket_data in tickets.items():
        producer.send(settings.kafka_topic, ticket_data)
        print(f"Published ticket_id={ticket_id} to topic={settings.kafka_topic}")
    producer.flush()


if __name__ == "__main__":
    main()
