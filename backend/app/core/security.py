"""Authentication and role-based access control (RBAC) dependencies.

Login itself happens client-side via the Supabase Auth JS SDK (email +
password against Supabase's GoTrue service, which stores bcrypt password
hashes and issues short-lived JWTs). The backend never sees a password — it
only ever verifies the resulting JWT on each request.
"""
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from app.core.config import get_settings
from app.db.supabase_client import get_service_client, get_user_client

_bearer_scheme = HTTPBearer(auto_error=True)


@dataclass
class CurrentUser:
    id: UUID
    email: str
    full_name: str
    role: str  # 'admin' | 'supervisor' | 'agent'
    is_active: bool
    hostel_ids: list[str]
    access_token: str


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentUser:
    payload = _decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed session token.")

    # Look up the authoritative profile/role/hostel assignments. Uses the
    # service client deliberately (RLS on app_users would otherwise require
    # a chicken-and-egg self-lookup); this is a read-only, narrowly-scoped
    # lookup keyed by the token's own verified subject.
    service = get_service_client()
    profile_resp = (
        service.table("app_users").select("*").eq("id", user_id).single().execute()
    )
    profile = profile_resp.data
    if not profile:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User profile not found.")
    if not profile["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated.")

    hostels_resp = service.table("user_hostels").select("hostel_id").eq("user_id", user_id).execute()
    hostel_ids = [row["hostel_id"] for row in hostels_resp.data]

    return CurrentUser(
        id=UUID(user_id),
        email=profile["email"],
        full_name=profile["full_name"],
        role=profile["role"],
        is_active=profile["is_active"],
        hostel_ids=hostel_ids,
        access_token=credentials.credentials,
    )


def require_roles(*allowed_roles: str):
    """Dependency factory enforcing least-privilege access per endpoint.

    This mirrors, but does not replace, the database's own RLS policies —
    it exists to fail fast with a clear 403 before any query is issued, and
    to gate operations (like audit log writes) that use the service-role
    client and therefore aren't subject to RLS at all.
    """

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(allowed_roles)}.",
            )
        return user

    return _checker


def get_scoped_client(user: CurrentUser = Depends(get_current_user)):
    """Return a Supabase client acting as the current user, RLS-enforced."""
    return get_user_client(user.access_token)
