from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, require_roles, get_scoped_client
from app.models.schemas import HostelCreate, HostelOut, HostelUpdate
from app.services import hostel_service

router = APIRouter(prefix="/hostels", tags=["hostels"])


@router.get("", response_model=list[HostelOut])
async def list_hostels(scoped_client=Depends(get_scoped_client)):
    return hostel_service.list_hostels(scoped_client)


@router.get("/{hostel_id}", response_model=HostelOut)
async def get_hostel(hostel_id: UUID, scoped_client=Depends(get_scoped_client)):
    return hostel_service.get_hostel(scoped_client, hostel_id)


@router.post("", response_model=HostelOut, status_code=201)
async def create_hostel(
    payload: HostelCreate,
    user: CurrentUser = Depends(require_roles("admin")),
    scoped_client=Depends(get_scoped_client),
):
    return hostel_service.create_hostel(user.id, scoped_client, payload)


@router.patch("/{hostel_id}", response_model=HostelOut)
async def update_hostel(
    hostel_id: UUID,
    payload: HostelUpdate,
    user: CurrentUser = Depends(require_roles("admin")),
    scoped_client=Depends(get_scoped_client),
):
    return hostel_service.update_hostel(user.id, scoped_client, hostel_id, payload)
