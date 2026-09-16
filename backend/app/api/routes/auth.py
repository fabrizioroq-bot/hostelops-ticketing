"""Login/signup/password-reset happen client-side via the Supabase Auth JS
SDK — the backend never touches a password. This router only exposes the
authenticated caller's own profile, used by the frontend right after login
to know the user's role and hostel assignments for routing/UI purposes.
"""
from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def read_current_user(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "hostel_ids": user.hostel_ids,
    }
