import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# uv run python scripts/produce_test_ticket.py

@dataclass(frozen=True)
class Settings:
    kafka_bootstrap_servers: str
    kafka_topic: str
    kafka_group_id: str
    gcp_project_id: str
    gcp_location: str
    vertex_model_name: str
    tickets_store_path: Path


def load_settings() -> Settings:
    return Settings(
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic=os.getenv("KAFKA_TICKET_TOPIC", "support-tickets"),
        kafka_group_id=os.getenv("KAFKA_GROUP_ID", "ticket-analyzer-agent"),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
        gcp_location=os.getenv("GCP_LOCATION", "us-central1"),
        vertex_model_name=os.getenv("VERTEX_MODEL_NAME", "claude-sonnet-5-5"),
        tickets_store_path=Path(
            os.getenv("TICKETS_STORE_PATH", str(PROJECT_ROOT / "scripts" / "tickets.json"))
        ),
    )


settings = load_settings()
