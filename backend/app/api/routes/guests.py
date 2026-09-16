from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, require_roles, get_scoped_client
from app.models.schemas import GuestOut, GuestUpdate
from app.services.audit_service import log_audit

router = APIRouter(prefix="/guests", tags=["guests"])


@router.get("", response_model=list[GuestOut])
async def list_guests(
    search: str | None = None,
    scoped_client=Depends(get_scoped_client),
):
    query = scoped_client.table("guests").select("*").is_("merged_into", "null")
    if search:
        query = query.ilike("full_name", f"%{search}%")
    return query.order("last_contact_at", desc=True).limit(200).execute().data


@router.get("/{guest_id}", response_model=GuestOut)
async def get_guest(guest_id: UUID, scoped_client=Depends(get_scoped_client)):
    resp = scoped_client.table("guests").select("*").eq("id", str(guest_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found.")
    return resp.data[0]


@router.get("/{guest_id}/tickets")
async def get_guest_tickets(guest_id: UUID, scoped_client=Depends(get_scoped_client)):
    return scoped_client.table("tickets").select("*").eq("guest_id", str(guest_id)).order(
        "created_at", desc=True
    ).execute().data


@router.patch("/{guest_id}", response_model=GuestOut)
async def update_guest(
    guest_id: UUID,
    payload: GuestUpdate,
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
    scoped_client=Depends(get_scoped_client),
):
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return await get_guest(guest_id, scoped_client)
    resp = scoped_client.table("guests").update(updates).eq("id", str(guest_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest not found.")
    log_audit(user.id, "guest_updated", "guest", guest_id, updates)
    return resp.data[0]
