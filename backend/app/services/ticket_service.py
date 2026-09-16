"""Ticket CRUD, orchestrating MDM guest linkage, change history, and audit
logging around the RLS-enforced reads/writes.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.security import CurrentUser
from app.models.schemas import TicketCreate, TicketFilters, TicketUpdate
from app.services.audit_service import log_audit, log_ticket_history
from app.services.guest_service import find_or_create_guest, sync_guest_after_ticket

_UPDATABLE_HISTORY_FIELDS = [
    "status", "priority", "resolution_notes", "recontacted", "recontacted_notes", "assignee_id",
]


def create_ticket(user: CurrentUser, scoped_client: Client, payload: TicketCreate) -> dict:
    if user.role == "agent" and str(payload.hostel_id) not in user.hostel_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create tickets for hostels you are assigned to.",
        )

    guest_id, _created = find_or_create_guest(payload.guest_name, payload.reservation_number)

    now = datetime.now(timezone.utc)
    insert_resp = (
        scoped_client.table("tickets")
        .insert(
            {
                "guest_name": payload.guest_name.strip(),
                "reservation_number": payload.reservation_number,
                "guest_id": str(guest_id),
                "hostel_id": str(payload.hostel_id),
                "channel": payload.channel.value,
                "reason": payload.reason.value,
                "priority": payload.priority.value,
                "description": payload.description,
                "assignee_id": str(user.id),
                "created_by": str(user.id),
            }
        )
        .execute()
    )
    ticket = insert_resp.data[0]

    sync_guest_after_ticket(guest_id, payload.channel, payload.reason, payload.reservation_number, now)
    log_audit(user.id, "ticket_created", "ticket", ticket["id"], {"hostel_id": str(payload.hostel_id)})
    return ticket


def list_tickets(scoped_client: Client, filters: TicketFilters) -> tuple[list[dict], int]:
    query = scoped_client.table("tickets").select("*", count="exact")

    if filters.status:
        query = query.eq("status", filters.status.value)
    if filters.priority:
        query = query.eq("priority", filters.priority.value)
    if filters.channel:
        query = query.eq("channel", filters.channel.value)
    if filters.reason:
        query = query.eq("reason", filters.reason.value)
    if filters.hostel_id:
        query = query.eq("hostel_id", str(filters.hostel_id))
    if filters.assignee_id:
        query = query.eq("assignee_id", str(filters.assignee_id))
    if filters.date_from:
        query = query.gte("created_at", filters.date_from.isoformat())
    if filters.date_to:
        query = query.lte("created_at", filters.date_to.isoformat())
    if filters.search:
        term = filters.search.replace("%", "")
        query = query.or_(f"guest_name.ilike.%{term}%,reservation_number.ilike.%{term}%")

    start = (filters.page - 1) * filters.page_size
    end = start + filters.page_size - 1
    resp = query.order("created_at", desc=True).range(start, end).execute()
    return resp.data, resp.count or 0


def get_ticket(scoped_client: Client, ticket_id: UUID) -> dict:
    resp = scoped_client.table("tickets").select("*").eq("id", str(ticket_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
    return resp.data[0]


def update_ticket(user: CurrentUser, scoped_client: Client, ticket_id: UUID, payload: TicketUpdate) -> dict:
    existing = get_ticket(scoped_client, ticket_id)

    if payload.assignee_id is not None and user.role == "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and supervisors can reassign tickets.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "assignee_id" in updates:
        updates["assignee_id"] = str(updates["assignee_id"])
    for enum_field in ("status", "priority"):
        if enum_field in updates and hasattr(updates[enum_field], "value"):
            updates[enum_field] = updates[enum_field].value

    if not updates:
        return existing

    update_resp = scoped_client.table("tickets").update(updates).eq("id", str(ticket_id)).execute()
    if not update_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found or not permitted.")
    updated = update_resp.data[0]

    for field in _UPDATABLE_HISTORY_FIELDS:
        if field in updates and str(existing.get(field)) != str(updated.get(field)):
            log_ticket_history(ticket_id, user.id, field, existing.get(field), updated.get(field))

    if "status" in updates and updates["status"] == "resolved" and existing["status"] != "resolved":
        action = "ticket_resolved"
        if existing.get("guest_id"):
            scoped_client.table("guests").update(
                {"last_contact_at": updated.get("resolved_at") or datetime.now(timezone.utc).isoformat()}
            ).eq("id", existing["guest_id"]).execute()
    elif "status" in updates and updates["status"] == "closed":
        action = "ticket_closed"
    elif "assignee_id" in updates:
        action = "ticket_reassigned"
    else:
        action = "ticket_updated"

    log_audit(user.id, action, "ticket", ticket_id, updates)
    return updated


def get_ticket_history(scoped_client: Client, ticket_id: UUID) -> list[dict]:
    resp = (
        scoped_client.table("ticket_history")
        .select("*")
        .eq("ticket_id", str(ticket_id))
        .order("created_at", desc=False)
        .execute()
    )
    return resp.data
