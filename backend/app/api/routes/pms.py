from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import CurrentUser, require_roles
from app.services import pms_service

router = APIRouter(prefix="/pms", tags=["pms"])


class PMSCredentialsIn(BaseModel):
    provider: str
    access_token: str
    external_id: str


@router.post("/{hostel_id}/credentials")
async def set_pms_credentials(
    hostel_id: UUID,
    payload: PMSCredentialsIn,
    user: CurrentUser = Depends(require_roles("admin")),
):
    pms_service.set_credentials(user.id, hostel_id, payload.provider, payload.access_token, payload.external_id)
    return {"status": "credentials_saved"}


@router.post("/{hostel_id}/sync")
async def sync_hostel(hostel_id: UUID, user: CurrentUser = Depends(require_roles("admin"))):
    return await pms_service.sync_hostel(user.id, hostel_id)
