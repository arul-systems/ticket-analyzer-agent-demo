"""Manual test helper: read the local tickets.json and publish every full
ticket record to the support-tickets Pub/Sub topic the agent's Cloud Run
function is triggered off of via Eventarc.

Auth is Application Default Credentials (`gcloud auth application-default
login`), same as the rest of this project's GCP access.

Usage:
    uv run python scripts/produce_test_ticket.py
"""

import json

from google.cloud import pubsub_v1

from agent.config import settings


def main() -> None:
    with settings.tickets_store_path.open("r") as f:
        tickets = json.load(f)

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic)

    futures = []
    for ticket_id, ticket_data in tickets.items():
        futures.append(publisher.publish(topic_path, json.dumps(ticket_data).encode("utf-8")))
        print(f"Published ticket_id={ticket_id} to topic={settings.pubsub_topic}")

    for future in futures:
        future.result()


if __name__ == "__main__":
    main()
