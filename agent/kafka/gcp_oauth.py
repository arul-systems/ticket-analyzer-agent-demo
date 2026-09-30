"""OAUTHBEARER token provider for connecting kafka-python clients to Google
Cloud's Managed Service for Apache Kafka.

Managed Kafka's OAUTHBEARER implementation does NOT accept a bare Google
access token as the bearer credential (confirmed by reproducing a real
connection: the broker accepts SASL_SSL + the OAUTHBEARER handshake, then
silently drops the socket the instant a raw access token is sent as the
SaslAuthenticate payload - no error response, just a disconnect). It expects
a custom composite token: a fake 3-part "JWT" (header.payload.signature)
where the "signature" slot is actually the real access token, base64url
encoded, and the header/payload identify the principal. This mirrors
Google's own reference client:
https://github.com/googleapis/managedkafka/blob/main/kafka-auth-local-server/kafka_gcp_credentials_server.py

The "https://www.googleapis.com/auth/cloud-platform" scope is correct per
that same reference and per the "Authenticate to Kafka brokers" docs, which
also state the token's principal needs the managedkafka.clusters.connect
permission (roles/managedkafka.client) on the cluster's project.
"""

import base64
import datetime
import json
import os

import google.auth
import google.auth.transport.requests
from kafka.net.sasl.oauth import AbstractTokenProvider

_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_HEADER = json.dumps({"typ": "JWT", "alg": "GOOG_OAUTH2_TOKEN"})


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8").rstrip("=")


class GcpOAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, **config):
        super().__init__(**config)
        self._credentials, _ = google.auth.default(scopes=[_SCOPE])

    def token(self) -> str:
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())

        # Service account credentials expose this directly. User/ADC
        # credentials (e.g. `gcloud auth application-default login`) don't -
        # same gap Google's own reference client has, and it uses the same
        # env var as the documented workaround.
        subject = getattr(self._credentials, "service_account_email", None)
        if not subject:
            subject = os.environ.get("GOOGLE_MANAGED_KAFKA_AUTH_PRINCIPAL")
        if not subject:
            raise ValueError(
                "Unable to determine the Kafka auth principal from the current "
                "credentials. Set GOOGLE_MANAGED_KAFKA_AUTH_PRINCIPAL to the "
                "email of the principal these ADC credentials belong to."
            )

        payload = json.dumps(
            {
                "exp": self._credentials.expiry.replace(
                    tzinfo=datetime.timezone.utc
                ).timestamp(),
                "iss": "Google",
                "iat": datetime.datetime.now(datetime.timezone.utc).timestamp(),
                "sub": subject,
            }
        )
        return ".".join([_b64(_HEADER), _b64(payload), _b64(self._credentials.token)])
