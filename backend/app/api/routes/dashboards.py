from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user, get_scoped_client, require_roles
from app.models.schemas import DashboardFilters, TicketPriority, TicketReason
from app.services import dashboard_service

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


def _filters(
    hostel_id: UUID | None = None,
    assignee_id: UUID | None = None,
    priority: TicketPriority | None = None,
    reason: TicketReason | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> DashboardFilters:
    return DashboardFilters(
        hostel_id=hostel_id, assignee_id=assignee_id, priority=priority,
        reason=reason, date_from=date_from, date_to=date_to,
    )


@router.get("/executive")
async def executive_dashboard(
    filters: DashboardFilters = Depends(_filters),
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
    scoped_client=Depends(get_scoped_client),
):
    return {
        "overview": dashboard_service.get_overview(scoped_client, filters),
        "trend": dashboard_service.get_trend(scoped_client, filters),
        "by_reason": dashboard_service.get_by_reason(scoped_client, filters),
        "by_channel": dashboard_service.get_by_channel(scoped_client, filters),
        "by_priority_status": dashboard_service.get_by_priority_status(scoped_client, filters),
        "resolution_time_by_hostel": dashboard_service.get_resolution_time(scoped_client, "hostel", filters),
        "resolution_time_by_agent": dashboard_service.get_resolution_time(scoped_client, "agent", filters),
        "recontact_rate": dashboard_service.get_recontact_rate(scoped_client, filters),
    }


@router.get("/agent")
async def agent_dashboard(
    agent_id: UUID | None = None,
    user: CurrentUser = Depends(get_current_user),
    scoped_client=Depends(get_scoped_client),
):
    # Agents may only ever view their own performance; admins/supervisors
    # may inspect any agent's by passing agent_id explicitly.
    target_id = user.id
    if agent_id and user.role in ("admin", "supervisor"):
        target_id = agent_id
    return dashboard_service.get_agent_performance(scoped_client, target_id)


@router.get("/data-quality")
async def data_quality_dashboard(
    user: CurrentUser = Depends(require_roles("admin")),
    scoped_client=Depends(get_scoped_client),
):
    return {
        "summary": dashboard_service.get_data_quality_summary(scoped_client),
        "incomplete_tickets": dashboard_service.get_incomplete_tickets(scoped_client),
    }


@router.get("/hostel-performance")
async def hostel_performance_dashboard(
    filters: DashboardFilters = Depends(_filters),
    user: CurrentUser = Depends(require_roles("admin", "supervisor")),
    scoped_client=Depends(get_scoped_client),
):
    performance = dashboard_service.get_hostel_performance(scoped_client, filters)
    top_issues = {
        row["hostel_id"]: dashboard_service.get_hostel_top_issues(scoped_client, row["hostel_id"])
        for row in performance
    }
    workload = dashboard_service.get_agent_workload(scoped_client, filters.hostel_id)
    return {"performance": performance, "top_issues_by_hostel": top_issues, "agent_workload": workload}
