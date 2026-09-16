from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.security import CurrentUser, require_roles, get_scoped_client
from app.services import export_service

router = APIRouter(prefix="/exports", tags=["exports"])

_MEDIA_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.get("/tickets")
async def export_tickets(
    fmt: str = Query("csv", pattern="^(csv|xlsx)$"),
    columns: str | None = None,
    status: str | None = None,
    hostel_id: UUID | None = None,
    priority: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
    scoped_client=Depends(get_scoped_client),
):
    col_list = columns.split(",") if columns else None
    filters = {
        "status": status,
        "hostel_id": str(hostel_id) if hostel_id else None,
        "priority": priority,
    }
    data = export_service.export_tickets(scoped_client, user.id, fmt, col_list, filters)
    filename = f"tickets_export.{fmt}"
    return Response(
        content=data,
        media_type=_MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/guests")
async def export_guests(
    fmt: str = Query("csv", pattern="^(csv|xlsx)$"),
    columns: str | None = None,
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
    scoped_client=Depends(get_scoped_client),
):
    col_list = columns.split(",") if columns else None
    data = export_service.export_guests(scoped_client, user.id, fmt, col_list)
    filename = f"guests_export.{fmt}"
    return Response(
        content=data,
        media_type=_MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
