"""User directory management (Admin only). Provisions accounts through the
Supabase Auth Admin API — passwords are hashed by GoTrue itself (bcrypt),
the backend never stores or handles raw passwords beyond this one call.
"""
from uuid import UUID

from fastapi import HTTPException, status

from app.db.supabase_client import get_service_client
from app.models.schemas import UserCreate, UserUpdate
from app.services.audit_service import log_audit


def _attach_hostel_ids(users: list[dict]) -> list[dict]:
    client = get_service_client()
    if not users:
        return users
    ids = [u["id"] for u in users]
    resp = client.table("user_hostels").select("user_id, hostel_id").in_("user_id", ids).execute()
    by_user: dict[str, list[str]] = {}
    for row in resp.data:
        by_user.setdefault(row["user_id"], []).append(row["hostel_id"])
    for u in users:
        u["hostel_ids"] = by_user.get(u["id"], [])
    return users


def list_users() -> list[dict]:
    client = get_service_client()
    resp = client.table("app_users").select("*").order("created_at", desc=False).execute()
    return _attach_hostel_ids(resp.data)


def create_user(actor_id: UUID, payload: UserCreate) -> dict:
    client = get_service_client()
    try:
        auth_resp = client.auth.admin.create_user(
            {
                "email": payload.email,
                "password": payload.temporary_password,
                "email_confirm": True,
                "user_metadata": {"full_name": payload.full_name, "role": payload.role.value},
            }
        )
    except Exception as exc:  # supabase-py raises its own AuthApiError subtype
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not create user: {exc}") from exc

    new_user_id = auth_resp.user.id
    if payload.hostel_ids:
        client.table("user_hostels").insert(
            [{"user_id": new_user_id, "hostel_id": str(h)} for h in payload.hostel_ids]
        ).execute()

    log_audit(actor_id, "user_created", "user", new_user_id, {"email": payload.email, "role": payload.role.value})

    profile = client.table("app_users").select("*").eq("id", new_user_id).single().execute().data
    return _attach_hostel_ids([profile])[0]


def update_user(actor_id: UUID, user_id: UUID, payload: UserUpdate) -> dict:
    client = get_service_client()
    updates = payload.model_dump(exclude_unset=True, exclude={"hostel_ids"})
    if "role" in updates and hasattr(updates["role"], "value"):
        updates["role"] = updates["role"].value

    if updates:
        resp = client.table("app_users").update(updates).eq("id", str(user_id)).execute()
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        # Keep auth metadata in sync (used if a custom-claims JWT hook is added later).
        if "role" in updates or "full_name" in updates:
            client.auth.admin.update_user_by_id(
                str(user_id),
                {"user_metadata": {"full_name": updates.get("full_name"), "role": updates.get("role")}},
            )

    if payload.hostel_ids is not None:
        client.table("user_hostels").delete().eq("user_id", str(user_id)).execute()
        if payload.hostel_ids:
            client.table("user_hostels").insert(
                [{"user_id": str(user_id), "hostel_id": str(h)} for h in payload.hostel_ids]
            ).execute()

    action = "user_deactivated" if updates.get("is_active") is False else "user_updated"
    log_audit(actor_id, action, "user", user_id, updates)

    profile = client.table("app_users").select("*").eq("id", str(user_id)).single().execute().data
    return _attach_hostel_ids([profile])[0]
