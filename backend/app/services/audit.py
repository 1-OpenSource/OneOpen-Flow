from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        safe_details = dict(details or {})
        for key in list(safe_details.keys()):
            if "secret" in key.lower() or "password" in key.lower() or "token" in key.lower():
                safe_details[key] = "***"
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=safe_details,
        )
        self.db.add(entry)
        self.db.flush()
        return entry
