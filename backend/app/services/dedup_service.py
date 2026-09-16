"""Guest deduplication: fuzzy-match scan + manual-review merge queue.

Per business decision, merges are MANUAL REVIEW ONLY — this module never
merges anything on its own. `scan_for_duplicates` only ever proposes
candidates into `guest_merge_candidates`; an admin/supervisor must call
`approve_merge` explicitly.

Scale note: pairwise comparison here is O(n^2) in the number of golden
records, in Python (via rapidfuzz), which is appropriate at the small
scale this deployment targets (hundreds of guests). At larger scale this
should move to a database-side query using the `pg_trgm` index already
defined on `guests.name_normalized` (e.g. `similarity(a.name_normalized,
b.name_normalized) > 0.4` as a pre-filter) to avoid loading the whole table.
"""
from uuid import UUID

from rapidfuzz import fuzz

from app.db.supabase_client import get_service_client
from app.services.audit_service import log_audit
from app.services.guest_service import compute_data_quality_score

NAME_MATCH_THRESHOLD = 85.0


def scan_for_duplicates() -> list[dict]:
    client = get_service_client()
    guests_resp = (
        client.table("guests").select("*").is_("merged_into", "null").execute()
    )
    guests = guests_resp.data

    existing_resp = client.table("guest_merge_candidates").select("guest_id_a, guest_id_b").execute()
    existing_pairs = {frozenset((row["guest_id_a"], row["guest_id_b"])) for row in existing_resp.data}

    new_candidates = []
    for i in range(len(guests)):
        for j in range(i + 1, len(guests)):
            a, b = guests[i], guests[j]
            pair_key = frozenset((a["id"], b["id"]))
            if pair_key in existing_pairs:
                continue

            name_score = fuzz.token_sort_ratio(a["name_normalized"], b["name_normalized"])
            phone_match = bool(a.get("phone")) and a.get("phone") == b.get("phone")
            reservation_overlap = bool(
                set(a.get("linked_reservations") or []) & set(b.get("linked_reservations") or [])
            )

            score = name_score
            reasons = [f"name similarity {name_score:.0f}%"]
            if phone_match:
                score = max(score, 97)
                reasons.append("matching phone number")
            if reservation_overlap:
                score = max(score, 99)
                reasons.append("overlapping reservation number")

            if score >= NAME_MATCH_THRESHOLD:
                new_candidates.append(
                    {
                        "guest_id_a": a["id"],
                        "guest_id_b": b["id"],
                        "match_score": round(score, 2),
                        "match_reason": ", ".join(reasons),
                        "status": "pending",
                    }
                )
                existing_pairs.add(pair_key)

    if new_candidates:
        client.table("guest_merge_candidates").insert(new_candidates).execute()
    return new_candidates


def list_candidates(status: str | None = None) -> list[dict]:
    client = get_service_client()
    query = client.table("guest_merge_candidates").select("*").order("match_score", desc=True)
    if status:
        query = query.eq("status", status)
    return query.execute().data


def reject_candidate(candidate_id: UUID, reviewer_id: UUID) -> None:
    client = get_service_client()
    client.table("guest_merge_candidates").update(
        {"status": "rejected", "reviewed_by": str(reviewer_id), "reviewed_at": "now()"}
    ).eq("id", str(candidate_id)).execute()


def approve_merge(candidate_id: UUID, reviewer_id: UUID) -> dict:
    client = get_service_client()
    candidate_resp = (
        client.table("guest_merge_candidates").select("*").eq("id", str(candidate_id)).single().execute()
    )
    candidate = candidate_resp.data
    if candidate["status"] != "pending":
        raise ValueError("This merge candidate has already been reviewed.")

    guest_a = client.table("guests").select("*").eq("id", candidate["guest_id_a"]).single().execute().data
    guest_b = client.table("guests").select("*").eq("id", candidate["guest_id_b"]).single().execute().data

    # Survivor = the more complete/older golden record; the other is merged away.
    def _rank(g: dict) -> tuple:
        return (g["data_quality_score"], g["total_tickets"], g["created_at"])

    survivor, loser = (guest_a, guest_b) if _rank(guest_a) >= _rank(guest_b) else (guest_b, guest_a)

    merged_fields = {
        "email": survivor.get("email") or loser.get("email"),
        "phone": survivor.get("phone") or loser.get("phone"),
        "total_tickets": (survivor.get("total_tickets") or 0) + (loser.get("total_tickets") or 0),
        "linked_reservations": list(
            set(survivor.get("linked_reservations") or []) | set(loser.get("linked_reservations") or [])
        ),
        "common_reasons": list(
            set(survivor.get("common_reasons") or []) | set(loser.get("common_reasons") or [])
        ),
        "last_contact_at": max(
            filter(None, [survivor.get("last_contact_at"), loser.get("last_contact_at")]),
            default=None,
        ),
    }
    merged_fields["data_quality_score"] = compute_data_quality_score({**survivor, **merged_fields})

    client.table("guests").update(merged_fields).eq("id", survivor["id"]).execute()
    client.table("tickets").update({"guest_id": survivor["id"]}).eq("guest_id", loser["id"]).execute()
    client.table("guests").update({"merged_into": survivor["id"]}).eq("id", loser["id"]).execute()
    client.table("guest_merge_candidates").update(
        {"status": "approved", "reviewed_by": str(reviewer_id), "reviewed_at": "now()"}
    ).eq("id", str(candidate_id)).execute()

    log_audit(reviewer_id, "guest_merged", "guest", survivor["id"], {"merged_from": loser["id"]})
    return {"survivor_id": survivor["id"], "merged_id": loser["id"]}
