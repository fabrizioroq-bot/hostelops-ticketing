"""Guest MDM: golden record ingestion at ticket-creation time.

Matching here is intentionally conservative — only EXACT signals (matching
reservation number, or an exact normalized-name match) auto-link a new
ticket to an existing golden record. Anything fuzzier is left for the
separate `dedup_service` review queue, per the business decision that guest
merges are manual-review-only, never silently automatic.

This runs with the service-role client because cross-hostel matching
requires visibility across the whole `guests` table, wider than any single
agent's RLS-scoped view — the matching itself is a backend-orchestrated MDM
process, not a direct user query.
"""
import re
from datetime import datetime, timezone
from uuid import UUID

from app.db.supabase_client import get_service_client
from app.models.schemas import TicketChannel, TicketReason


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def compute_data_quality_score(guest: dict) -> int:
    score = 0
    if guest.get("email"):
        score += 25
    if guest.get("phone"):
        score += 25
    if guest.get("linked_reservations"):
        score += 30
    if " " in (guest.get("full_name") or ""):  # first + last name present
        score += 20
    return min(score, 100)


def find_or_create_guest(guest_name: str, reservation_number: str | None) -> tuple[UUID, bool]:
    """Returns (guest_id, was_created)."""
    client = get_service_client()
    normalized = normalize_name(guest_name)

    # 1. Exact reservation number match wins first — the strongest possible
    #    signal that this is the same guest.
    if reservation_number:
        resp = (
            client.table("guests")
            .select("id")
            .contains("linked_reservations", [reservation_number])
            .is_("merged_into", "null")
            .limit(1)
            .execute()
        )
        if resp.data:
            return UUID(resp.data[0]["id"]), False

    # 2. Exact normalized-name match against existing golden records.
    resp = (
        client.table("guests")
        .select("id")
        .eq("name_normalized", normalized)
        .is_("merged_into", "null")
        .limit(1)
        .execute()
    )
    if resp.data:
        return UUID(resp.data[0]["id"]), False

    # 3. No confident match — create a new golden record.
    insert_resp = (
        client.table("guests")
        .insert({"full_name": guest_name.strip()})
        .execute()
    )
    return UUID(insert_resp.data[0]["id"]), True


def sync_guest_after_ticket(
    guest_id: UUID,
    channel: TicketChannel,
    reason: TicketReason,
    reservation_number: str | None,
    created_at: datetime | None = None,
) -> None:
    """Distribute the new ticket's info back onto the golden record —
    the "Data Distribution" step of the MDM flow."""
    client = get_service_client()
    guest_resp = client.table("guests").select("*").eq("id", str(guest_id)).single().execute()
    guest = guest_resp.data

    reservations = set(guest.get("linked_reservations") or [])
    if reservation_number:
        reservations.add(reservation_number)

    reasons = set(guest.get("common_reasons") or [])
    reasons.add(reason.value if isinstance(reason, TicketReason) else reason)

    # Preferred channel = most frequent channel across all of this guest's
    # tickets (not just the latest one).
    tickets_resp = client.table("tickets").select("channel").eq("guest_id", str(guest_id)).execute()
    channel_counts: dict[str, int] = {}
    for row in tickets_resp.data:
        channel_counts[row["channel"]] = channel_counts.get(row["channel"], 0) + 1
    new_channel = channel.value if isinstance(channel, TicketChannel) else channel
    channel_counts[new_channel] = channel_counts.get(new_channel, 0) + 1
    preferred_channel = max(channel_counts, key=channel_counts.get)

    updates = {
        "total_tickets": (guest.get("total_tickets") or 0) + 1,
        "last_contact_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        "linked_reservations": list(reservations),
        "common_reasons": list(reasons),
        "preferred_channel": preferred_channel,
    }
    merged = {**guest, **updates}
    updates["data_quality_score"] = compute_data_quality_score(merged)

    client.table("guests").update(updates).eq("id", str(guest_id)).execute()
