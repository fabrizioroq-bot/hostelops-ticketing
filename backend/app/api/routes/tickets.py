from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.security import CurrentUser, get_current_user, get_scoped_client
from app.models.schemas import (
    TicketChannel, TicketCreate, TicketFilters, TicketHistoryEntry, TicketOut,
    TicketPriority, TicketReason, TicketStatus, TicketUpdate,
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(
    payload: TicketCreate,
    user: CurrentUser = Depends(get_current_user),
    scoped_client=Depends(get_scoped_client),
):
    return ticket_service.create_ticket(user, scoped_client, payload)


@router.get("")
async def list_tickets(
    status_: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    channel: TicketChannel | None = None,
    reason: TicketReason | None = None,
    hostel_id: UUID | None = None,
    assignee_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    scoped_client=Depends(get_scoped_client),
):
    filters = TicketFilters(
        status=status_, priority=priority, channel=channel, reason=reason,
        hostel_id=hostel_id, assignee_id=assignee_id, date_from=date_from,
        date_to=date_to, search=search, page=page, page_size=page_size,
    )
    items, total = ticket_service.list_tickets(scoped_client, filters)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(ticket_id: UUID, scoped_client=Depends(get_scoped_client)):
    return ticket_service.get_ticket(scoped_client, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: UUID,
    payload: TicketUpdate,
    user: CurrentUser = Depends(get_current_user),
    scoped_client=Depends(get_scoped_client),
):
    return ticket_service.update_ticket(user, scoped_client, ticket_id, payload)


@router.get("/{ticket_id}/history", response_model=list[TicketHistoryEntry])
async def get_ticket_history(ticket_id: UUID, scoped_client=Depends(get_scoped_client)):
    return ticket_service.get_ticket_history(scoped_client, ticket_id)
