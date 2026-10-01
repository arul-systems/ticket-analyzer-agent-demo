import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    pubsub_topic: str
    results_bucket: str
    gcp_project_id: str
    gcp_location: str
    vertex_model_name: str
    tickets_store_path: Path


def load_settings() -> Settings:
    return Settings(
        pubsub_topic=os.getenv("PUBSUB_TICKET_TOPIC", "support-tickets"),
        results_bucket=os.getenv("RESULTS_BUCKET", ""),
        gcp_project_id=os.getenv("GCP_PROJECT_ID", ""),
        gcp_location=os.getenv("GCP_LOCATION", "us-central1"),
        vertex_model_name=os.getenv("VERTEX_MODEL_NAME", "gemini-2.5-pro"),
        tickets_store_path=Path(
            os.getenv("TICKETS_STORE_PATH", str(PROJECT_ROOT / "scripts" / "tickets.json"))
        ),
    )


settings = load_settings()
