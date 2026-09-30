import logging

from kafka import KafkaConsumer

from agent.config import settings
from agent.kafka.parsing import extract_ticket_data_from_bytes
from agent.processor import process_ticket

logger = logging.getLogger(__name__)


def run() -> None:
    consumer = KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    logger.info(
        "Listening for ticket events on topic '%s' at %s",
        settings.kafka_topic,
        settings.kafka_bootstrap_servers,
    )
    for message in consumer:
        ticket_data = extract_ticket_data_from_bytes(message.value)
        if not ticket_data:
            logger.warning("Skipping message with no parseable ticket data: %r", message.value)
            continue
        ticket_id = ticket_data.get("id")
        logger.info("Received ticket: %s", ticket_id)
        try:
            process_ticket(ticket_data)
        except Exception:
            logger.exception("Failed to process ticket %s", ticket_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
