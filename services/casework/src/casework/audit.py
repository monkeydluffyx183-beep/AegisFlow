from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def append_audit(*, actor_id: str, role: str, action: str, resource_type: str, resource_id: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    """Serializable outbox event; the platform writer persists this atomically with changes."""
    return {"event_id": f"audit-{datetime.now(timezone.utc).timestamp()}", "actor_id": actor_id, "role": role, "action": action, "resource_type": resource_type, "resource_id": resource_id, "detail": detail or {}, "created_at": datetime.now(timezone.utc).isoformat()}
