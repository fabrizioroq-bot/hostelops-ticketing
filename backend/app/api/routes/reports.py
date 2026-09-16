"""On-demand version of the scheduled weekly report — lets an admin trigger
and download it immediately, without waiting for Monday morning."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.security import CurrentUser, require_roles
from app.services.report_service import generate_weekly_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/weekly.pdf")
async def download_weekly_report(user: CurrentUser = Depends(require_roles("admin", "supervisor"))):
    pdf_bytes = generate_weekly_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="weekly-ticket-summary.pdf"'},
    )
