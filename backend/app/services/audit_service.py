"""Audit logging. Always writes via the service-role client: regular users
have no insert policy on `audit_logs` at all (see migration 0001), so the
audit trail cannot be tampered with even by an Admin acting through the
normal API — only backend code invoking this function can write to it.
"""
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_service_client


def log_audit(
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None,
    changes: dict[str, Any] | None = None,
) -> None:
    client = get_service_client()
    client.table("audit_logs").insert(
        {
            "actor_id": str(actor_id) if actor_id else None,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "changes": changes,
        }
    ).execute()


def log_ticket_history(ticket_id: UUID, changed_by: UUID, field_name: str, old_value, new_value) -> None:
    client = get_service_client()
    client.table("ticket_history").insert(
        {
            "ticket_id": str(ticket_id),
            "changed_by": str(changed_by),
            "field_name": field_name,
            "old_value": str(old_value) if old_value is not None else None,
            "new_value": str(new_value) if new_value is not None else None,
        }
    ).execute()
