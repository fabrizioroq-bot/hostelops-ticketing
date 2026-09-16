"""Guest deduplication review queue. Admin/supervisor only — merges are
manual-review-only by design (see services/dedup_service.py)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import CurrentUser, require_roles
from app.models.schemas import MergeCandidateOut
from app.services import dedup_service

router = APIRouter(prefix="/dedup", tags=["dedup"])


@router.post("/scan")
async def scan_for_duplicates(user: CurrentUser = Depends(require_roles("admin", "supervisor"))):
    new_candidates = dedup_service.scan_for_duplicates()
    return {"new_candidates_found": len(new_candidates)}


@router.get("/candidates", response_model=list[MergeCandidateOut])
async def list_candidates(
    status: str | None = "pending",
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
):
    return dedup_service.list_candidates(status)


@router.post("/candidates/{candidate_id}/approve")
async def approve_merge(candidate_id: UUID, user: CurrentUser = Depends(require_roles("admin", "supervisor"))):
    try:
        return dedup_service.approve_merge(candidate_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/candidates/{candidate_id}/reject")
async def reject_merge(candidate_id: UUID, user: CurrentUser = Depends(require_roles("admin", "supervisor"))):
    dedup_service.reject_candidate(candidate_id, user.id)
    return {"status": "rejected"}
