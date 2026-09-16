"""Thin wrappers around the Postgres dashboard RPC functions (see migration
0004_dashboard_functions.sql). Each call goes through the user's own scoped
client, so results are automatically bounded by Row Level Security — an
agent calling these never sees data outside their assigned hostel(s), even
though the SQL itself applies no role-specific filtering.
"""
from uuid import UUID

from supabase import Client

from app.models.schemas import DashboardFilters


def _filters_payload(f: DashboardFilters) -> dict:
    return {
        "p_hostel_id": str(f.hostel_id) if f.hostel_id else None,
        "p_assignee_id": str(f.assignee_id) if f.assignee_id else None,
        "p_priority": f.priority.value if f.priority else None,
        "p_reason": f.reason.value if f.reason else None,
        "p_date_from": f.date_from.isoformat() if f.date_from else None,
        "p_date_to": f.date_to.isoformat() if f.date_to else None,
    }


def get_overview(client: Client, filters: DashboardFilters) -> dict:
    return client.rpc("fn_dashboard_overview", _filters_payload(filters)).execute().data


def get_trend(client: Client, filters: DashboardFilters) -> list[dict]:
    return client.rpc("fn_dashboard_trend", _filters_payload(filters)).execute().data


def get_by_reason(client: Client, filters: DashboardFilters) -> list[dict]:
    payload = _filters_payload(filters)
    payload.pop("p_reason")
    return client.rpc("fn_dashboard_by_reason", payload).execute().data


def get_by_channel(client: Client, filters: DashboardFilters) -> list[dict]:
    payload = {k: v for k, v in _filters_payload(filters).items() if k in ("p_hostel_id", "p_assignee_id", "p_date_from", "p_date_to")}
    return client.rpc("fn_dashboard_by_channel", payload).execute().data


def get_by_priority_status(client: Client, filters: DashboardFilters) -> list[dict]:
    payload = {
        "p_hostel_id": str(filters.hostel_id) if filters.hostel_id else None,
        "p_date_from": filters.date_from.isoformat() if filters.date_from else None,
        "p_date_to": filters.date_to.isoformat() if filters.date_to else None,
    }
    return client.rpc("fn_dashboard_by_priority_status", payload).execute().data


def get_resolution_time(client: Client, group_by: str, filters: DashboardFilters) -> list[dict]:
    payload = {
        "p_group_by": group_by,
        "p_date_from": filters.date_from.isoformat() if filters.date_from else None,
        "p_date_to": filters.date_to.isoformat() if filters.date_to else None,
    }
    return client.rpc("fn_dashboard_resolution_time", payload).execute().data


def get_recontact_rate(client: Client, filters: DashboardFilters) -> dict:
    payload = {
        "p_hostel_id": str(filters.hostel_id) if filters.hostel_id else None,
        "p_date_from": filters.date_from.isoformat() if filters.date_from else None,
        "p_date_to": filters.date_to.isoformat() if filters.date_to else None,
    }
    return client.rpc("fn_dashboard_recontact_rate", payload).execute().data


def get_hostel_performance(client: Client, filters: DashboardFilters) -> list[dict]:
    payload = {
        "p_date_from": filters.date_from.isoformat() if filters.date_from else None,
        "p_date_to": filters.date_to.isoformat() if filters.date_to else None,
    }
    return client.rpc("fn_hostel_performance", payload).execute().data


def get_hostel_top_issues(client: Client, hostel_id: UUID, limit: int = 3) -> list[dict]:
    return client.rpc("fn_hostel_top_issues", {"p_hostel_id": str(hostel_id), "p_limit": limit}).execute().data


def get_agent_workload(client: Client, hostel_id: UUID | None) -> list[dict]:
    return client.rpc("fn_agent_workload", {"p_hostel_id": str(hostel_id) if hostel_id else None}).execute().data


def get_agent_performance(client: Client, agent_id: UUID) -> dict:
    return client.rpc("fn_agent_performance", {"p_agent_id": str(agent_id)}).execute().data


def get_data_quality_summary(client: Client) -> dict:
    return client.rpc("fn_data_quality_summary", {}).execute().data


def get_incomplete_tickets(client: Client, limit: int = 50) -> list[dict]:
    return client.rpc("fn_incomplete_tickets", {"p_limit": limit}).execute().data
