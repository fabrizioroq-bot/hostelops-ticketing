"""Maintenance module: internal property-maintenance tickets (leaks,
broken fixtures, etc.), fully separate from the guest-facing ticketing
system — separate table, separate storage bucket for photos, separate
audit actions. See supabase/migrations/0006_maintenance_module.sql for the
schema and RLS policies this mirrors.
"""
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from supabase import Client

from app.core.security import CurrentUser
from app.models.schemas import MaintenanceTicketCreate, MaintenanceTicketFilters, MaintenanceTicketUpdate
from app.services.audit_service import log_audit

_PHOTO_BUCKET = "maintenance-photos"
_SIGNED_URL_TTL_SECONDS = 3600
_MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}


def create_ticket(user: CurrentUser, scoped_client: Client, payload: MaintenanceTicketCreate) -> dict:
    if user.role != "admin" and str(payload.hostel_id) not in user.hostel_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only report maintenance issues for hostels you are assigned to.",
        )

    resp = (
        scoped_client.table("maintenance_tickets")
        .insert(
            {
                "hostel_id": str(payload.hostel_id),
                "title": payload.title.strip(),
                "description": payload.description.strip(),
                "priority": payload.priority.value,
                "created_by": str(user.id),
            }
        )
        .execute()
    )
    ticket = resp.data[0]
    log_audit(user.id, "maintenance_ticket_created", "maintenance_ticket", ticket["id"], {"hostel_id": str(payload.hostel_id)})
    return ticket


def list_tickets(scoped_client: Client, filters: MaintenanceTicketFilters) -> list[dict]:
    query = scoped_client.table("maintenance_tickets").select("*")
    if filters.hostel_id:
        query = query.eq("hostel_id", str(filters.hostel_id))
    if filters.status:
        query = query.eq("status", filters.status.value)
    if filters.priority:
        query = query.eq("priority", filters.priority.value)
    return query.order("created_at", desc=True).execute().data


def get_ticket(scoped_client: Client, ticket_id: UUID) -> dict:
    resp = scoped_client.table("maintenance_tickets").select("*").eq("id", str(ticket_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance ticket not found.")
    return resp.data[0]


def update_ticket(user: CurrentUser, scoped_client: Client, ticket_id: UUID, payload: MaintenanceTicketUpdate) -> dict:
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    for enum_field in ("status", "priority"):
        if enum_field in updates and hasattr(updates[enum_field], "value"):
            updates[enum_field] = updates[enum_field].value
    if not updates:
        return get_ticket(scoped_client, ticket_id)

    resp = scoped_client.table("maintenance_tickets").update(updates).eq("id", str(ticket_id)).execute()
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance ticket not found or not permitted."
        )
    log_audit(user.id, "maintenance_ticket_updated", "maintenance_ticket", ticket_id, updates)
    return resp.data[0]


async def upload_photo(
    user: CurrentUser, scoped_client: Client, service_client: Client, ticket_id: UUID, file: UploadFile
) -> dict:
    # Confirms the caller can see this ticket (RLS-enforced) before anything
    # touches storage — a 404 here means "not your hostel", not "no such id".
    get_ticket(scoped_client, ticket_id)

    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, WebP, or HEIC photos are allowed.",
        )
    contents = await file.read()
    if len(contents) > _MAX_PHOTO_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo must be smaller than 10 MB.")

    filename = file.filename or "photo"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    storage_path = f"{ticket_id}/{uuid4()}.{extension}"

    # Uploaded via the service-role client deliberately: the bucket is
    # private with no storage.objects RLS policy at all, so only backend
    # code that has already re-checked the caller's role/hostel access
    # (via the RLS-enforced get_ticket() call above) can ever write to it.
    service_client.storage.from_(_PHOTO_BUCKET).upload(
        storage_path, contents, {"content-type": file.content_type}
    )

    photo_resp = (
        scoped_client.table("maintenance_ticket_photos")
        .insert(
            {"maintenance_ticket_id": str(ticket_id), "storage_path": storage_path, "uploaded_by": str(user.id)}
        )
        .execute()
    )
    photo = photo_resp.data[0]
    photo["url"] = _signed_url(service_client, storage_path)
    return photo


def list_photos(scoped_client: Client, service_client: Client, ticket_id: UUID) -> list[dict]:
    rows = (
        scoped_client.table("maintenance_ticket_photos")
        .select("*")
        .eq("maintenance_ticket_id", str(ticket_id))
        .order("created_at")
        .execute()
        .data
    )
    for row in rows:
        row["url"] = _signed_url(service_client, row["storage_path"])
    return rows


def _signed_url(service_client: Client, storage_path: str) -> str:
    result = service_client.storage.from_(_PHOTO_BUCKET).create_signed_url(storage_path, _SIGNED_URL_TTL_SECONDS)
    return result["signedURL"]
