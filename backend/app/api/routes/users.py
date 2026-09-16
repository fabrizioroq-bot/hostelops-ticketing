from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, require_roles
from app.models.schemas import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(user: CurrentUser = Depends(require_roles("admin", "supervisor"))):
    return user_service.list_users()


@router.post("", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, user: CurrentUser = Depends(require_roles("admin"))):
    return user_service.create_user(user.id, payload)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: UUID, payload: UserUpdate, user: CurrentUser = Depends(require_roles("admin"))):
    return user_service.update_user(user.id, user_id, payload)


@router.post("/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(user_id: UUID, user: CurrentUser = Depends(require_roles("admin"))):
    return user_service.update_user(user.id, user_id, UserUpdate(is_active=False))
