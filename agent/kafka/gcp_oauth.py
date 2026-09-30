"""OAUTHBEARER token provider for connecting kafka-python clients to Google
Cloud's Managed Service for Apache Kafka, which requires SASL_SSL/OAUTHBEARER
auth (an Application Default Credentials-issued OAuth token) rather than
plaintext or SASL/PLAIN.

NOTE: the "https://www.googleapis.com/auth/cloud-platform" scope below is
Google's documented scope for Managed Kafka client auth - verify against the
current "Connect a client" docs before relying on it in production.
"""

import google.auth
import google.auth.transport.requests
from kafka.net.sasl.oauth import AbstractTokenProvider

_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GcpOAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, **config):
        super().__init__(**config)
        self._credentials, _ = google.auth.default(scopes=[_SCOPE])

    def token(self) -> str:
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return self._credentials.token
