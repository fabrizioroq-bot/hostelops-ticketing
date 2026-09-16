"""Weekly PDF summary report generation for the scheduled email digest."""
import io
from datetime import datetime, timedelta, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.db.supabase_client import get_service_client


def generate_weekly_pdf() -> bytes:
    """Builds a cross-hostel weekly summary. Runs with the service-role
    client since this is a backend-scheduled job with no single user
    context — the resulting PDF is only ever emailed to admins/supervisors.
    """
    client = get_service_client()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    date_args = {"p_date_from": week_ago.isoformat(), "p_date_to": now.isoformat()}

    overview = client.rpc(
        "fn_dashboard_overview",
        {"p_hostel_id": None, "p_assignee_id": None, "p_priority": None, "p_reason": None, **date_args},
    ).execute().data
    by_reason = client.rpc(
        "fn_dashboard_by_reason",
        {"p_hostel_id": None, "p_assignee_id": None, "p_priority": None, **date_args},
    ).execute().data
    hostel_perf = client.rpc("fn_hostel_performance", date_args).execute().data
    recontact = client.rpc("fn_dashboard_recontact_rate", {"p_hostel_id": None, **date_args}).execute().data

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Weekly Ticket Summary")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("HostelOps — Weekly Ticket Summary", styles["Title"]),
        Paragraph(f"{week_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}", styles["Normal"]),
        Spacer(1, 16),
        Paragraph("Overview", styles["Heading2"]),
        Table(
            [["Total", "Open", "In Progress", "Resolved", "Closed"]]
            + [[overview["total"], overview["open"], overview["in_progress"], overview["resolved"], overview["closed"]]],
            style=_table_style(),
        ),
        Spacer(1, 16),
        Paragraph("Top Reasons", styles["Heading2"]),
        Table([["Reason", "Count"]] + [[r["reason"], r["count"]] for r in by_reason], style=_table_style()),
        Spacer(1, 16),
        Paragraph("Hostel Performance", styles["Heading2"]),
        Table(
            [["Hostel", "Tickets", "Avg. Resolution (hrs)"]]
            + [[h["hostel_name"], h["ticket_count"], h["avg_resolution_hours"] or "—"] for h in hostel_perf],
            style=_table_style(),
        ),
        Spacer(1, 16),
        Paragraph(
            f"Recontact rate: {recontact['rate_pct']}% "
            f"({recontact['recontacted']} of {recontact['total_resolved']} resolved tickets)",
            styles["Normal"],
        ),
    ]
    doc.build(story)
    return buffer.getvalue()


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ]
    )
