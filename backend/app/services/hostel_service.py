"""Hostel directory (master data). Reads go through the user's scoped
client (RLS allows all authenticated users to read); writes are gated to
admins both by the API route dependency and by the `hostels_write_admin`
RLS policy.
"""
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.models.schemas import HostelCreate, HostelUpdate
from app.services.audit_service import log_audit


def list_hostels(scoped_client: Client) -> list[dict]:
    return scoped_client.table("hostels").select("*").order("name").execute().data


def get_hostel(scoped_client: Client, hostel_id: UUID) -> dict:
    resp = scoped_client.table("hostels").select("*").eq("id", str(hostel_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
    return resp.data[0]


def create_hostel(actor_id: UUID, scoped_client: Client, payload: HostelCreate) -> dict:
    resp = scoped_client.table("hostels").insert(payload.model_dump(exclude_none=True)).execute()
    hostel = resp.data[0]
    log_audit(actor_id, "hostel_created", "hostel", hostel["id"], {"created": payload.model_dump(exclude_none=True)})
    return hostel


def update_hostel(actor_id: UUID, scoped_client: Client, hostel_id: UUID, payload: HostelUpdate) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "pms_status" in updates and hasattr(updates["pms_status"], "value"):
        updates["pms_status"] = updates["pms_status"].value
    if not updates:
        return get_hostel(scoped_client, hostel_id)
    resp = scoped_client.table("hostels").update(updates).eq("id", str(hostel_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hostel not found.")
    log_audit(actor_id, "hostel_updated", "hostel", hostel_id, updates)
    return resp.data[0]
