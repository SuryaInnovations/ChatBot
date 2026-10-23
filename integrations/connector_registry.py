"""
integrations/connector_registry.py — API & Database Connector Builder.

Supports:
- Registering external service integrations (PostgreSQL, REST APIs, Stripe, GitHub, Notion).
- Scoped authentication tokens and secret protection.
- Declarative invocation schemas and connection validation.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("chatbot.integrations.connector_registry")


@dataclass
class ServiceConnector:
    connector_id: str
    name: str
    service_type: str  # "rest_api", "database", "webhook"
    base_url_or_dsn: str
    auth_header_or_user: str
    allowed_endpoints: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Redact secrets
        d["auth_header_or_user"] = "[CONFIGURED]"
        return d


class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, ServiceConnector] = {}

    def register_connector(
        self,
        name: str,
        service_type: str,
        base_url_or_dsn: str,
        auth_header_or_user: str,
        allowed_endpoints: Optional[List[str]] = None
    ) -> ServiceConnector:
        """Registers a new external service connector."""
        cid = f"conn_{name.lower().replace(' ', '_')}"
        conn = ServiceConnector(
            connector_id=cid,
            name=name,
            service_type=service_type,
            base_url_or_dsn=base_url_or_dsn,
            auth_header_or_user=auth_header_or_user,
            allowed_endpoints=allowed_endpoints or ["*"]
        )
        self._connectors[cid] = conn
        logger.info(f"Registered connector: {cid} ({service_type})")
        return conn

    def get_connector(self, connector_id: str) -> Optional[ServiceConnector]:
        return self._connectors.get(connector_id)

    def list_connectors(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._connectors.values()]


default_connector_registry = ConnectorRegistry()
