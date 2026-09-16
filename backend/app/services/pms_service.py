"""Orchestrates PMS/channel-manager sync: pulls reservations from the
configured adapter and enriches the guest MDM golden records with
authoritative contact info (email/phone), which agent-entered tickets
often lack. Always invoked from an admin-gated route — this module itself
does not re-check roles.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.db.supabase_client import get_service_client
from app.services.audit_service import log_audit
from app.services.guest_service import find_or_create_guest
from app.services.pms.mews_adapter import MewsAdapter

ADAPTERS = {
    "mews": MewsAdapter(),
}


def set_credentials(actor_id: UUID, hostel_id: UUID, provider: str, access_token: str, external_id: str) -> None:
    if provider not in ADAPTERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported PMS provider '{provider}'.")

    client = get_service_client()
    client.table("hostels").update(
        {"pms_provider": provider, "pms_external_id": external_id, "pms_status": "pending"}
    ).eq("id", str(hostel_id)).execute()
    client.table("hostel_pms_credentials").upsert(
        {"hostel_id": str(hostel_id), "access_token": access_token}
    ).execute()
    log_audit(actor_id, "hostel_updated", "hostel", hostel_id, {"pms_provider": provider, "action": "credentials_set"})


async def sync_hostel(actor_id: UUID, hostel_id: UUID) -> dict:
    client = get_service_client()
    hostel = client.table("hostels").select("*").eq("id", str(hostel_id)).single().execute().data
    if not hostel or not hostel.get("pms_provider"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This hostel has no PMS provider configured.")

    creds = client.table("hostel_pms_credentials").select("*").eq("hostel_id", str(hostel_id)).execute().data
    if not creds:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No PMS credentials stored for this hostel.")

    adapter = ADAPTERS[hostel["pms_provider"]]
    now = datetime.now(timezone.utc)

    try:
        reservations = await adapter.fetch_reservations(
            property_external_id=hostel["pms_external_id"],
            access_token=creds[0]["access_token"],
            start=now - timedelta(days=2),
            end=now + timedelta(days=30),
        )
    except Exception as exc:
        client.table("hostels").update({"pms_status": "error"}).eq("id", str(hostel_id)).execute()
        log_audit(actor_id, "hostel_updated", "hostel", hostel_id, {"pms_sync": "error", "detail": str(exc)})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"PMS sync failed: {exc}") from exc

    enriched = 0
    for reservation in reservations:
        guest_id, _created = find_or_create_guest(reservation["guest_name"], reservation["reservation_number"])
        guest = client.table("guests").select("email, phone").eq("id", str(guest_id)).single().execute().data
        patch = {}
        if reservation.get("guest_email") and not guest.get("email"):
            patch["email"] = reservation["guest_email"]
        if reservation.get("guest_phone") and not guest.get("phone"):
            patch["phone"] = reservation["guest_phone"]
        if patch:
            client.table("guests").update(patch).eq("id", str(guest_id)).execute()
            enriched += 1

    client.table("hostels").update({"pms_status": "synced"}).eq("id", str(hostel_id)).execute()
    log_audit(actor_id, "hostel_updated", "hostel", hostel_id, {"pms_sync": "success", "reservations_processed": len(reservations)})
    return {"reservations_processed": len(reservations), "guests_enriched": enriched}
