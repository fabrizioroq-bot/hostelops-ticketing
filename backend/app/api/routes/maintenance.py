"""Maintenance module API — separate router, separate permission model from
the guest ticketing system. Agents have no access at all here; supervisors
are view-only; admin and the 'maintenance' role can create/update.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.security import CurrentUser, get_scoped_client, require_roles
from app.db.supabase_client import get_service_client
from app.models.schemas import (
    MaintenancePhotoOut, MaintenancePriority, MaintenanceStatus,
    MaintenanceTicketCreate, MaintenanceTicketFilters, MaintenanceTicketOut, MaintenanceTicketUpdate,
)
from app.services import maintenance_service

router = APIRouter(prefix="/maintenance-tickets", tags=["maintenance"])

_VIEW_ROLES = ("admin", "supervisor", "maintenance")
_WRITE_ROLES = ("admin", "maintenance")


@router.post("", response_model=MaintenanceTicketOut, status_code=201)
async def create_maintenance_ticket(
    payload: MaintenanceTicketCreate,
    user: CurrentUser = Depends(require_roles(*_WRITE_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    return maintenance_service.create_ticket(user, scoped_client, payload)


@router.get("", response_model=list[MaintenanceTicketOut])
async def list_maintenance_tickets(
    hostel_id: UUID | None = None,
    status_: MaintenanceStatus | None = None,
    priority: MaintenancePriority | None = None,
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    filters = MaintenanceTicketFilters(hostel_id=hostel_id, status=status_, priority=priority)
    return maintenance_service.list_tickets(scoped_client, filters)


@router.get("/{ticket_id}", response_model=MaintenanceTicketOut)
async def get_maintenance_ticket(
    ticket_id: UUID,
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    return maintenance_service.get_ticket(scoped_client, ticket_id)


@router.patch("/{ticket_id}", response_model=MaintenanceTicketOut)
async def update_maintenance_ticket(
    ticket_id: UUID,
    payload: MaintenanceTicketUpdate,
    user: CurrentUser = Depends(require_roles(*_WRITE_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    return maintenance_service.update_ticket(user, scoped_client, ticket_id, payload)


@router.post("/{ticket_id}/photos", response_model=MaintenancePhotoOut, status_code=201)
async def upload_maintenance_photo(
    ticket_id: UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_roles(*_WRITE_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    return await maintenance_service.upload_photo(user, scoped_client, get_service_client(), ticket_id, file)


@router.get("/{ticket_id}/photos", response_model=list[MaintenancePhotoOut])
async def list_maintenance_photos(
    ticket_id: UUID,
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    scoped_client=Depends(get_scoped_client),
):
    return maintenance_service.list_photos(scoped_client, get_service_client(), ticket_id)
