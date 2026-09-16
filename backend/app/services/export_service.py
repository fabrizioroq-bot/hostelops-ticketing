"""CSV/Excel export for tickets and the guest master list, with custom
column selection. Every export call is audit-logged (who exported what,
when, and with which filters/columns) per the audit requirement.
"""
import csv
import io
from uuid import UUID

from openpyxl import Workbook
from supabase import Client

from app.services.audit_service import log_audit

TICKET_EXPORT_COLUMNS = [
    "id", "reservation_number", "guest_name", "hostel_id", "channel", "reason",
    "priority", "description", "status", "assignee_id", "resolution_notes",
    "recontacted", "recontacted_notes", "created_at", "resolved_at",
]

GUEST_EXPORT_COLUMNS = [
    "id", "full_name", "email", "phone", "total_tickets", "last_contact_at",
    "common_reasons", "preferred_channel", "linked_reservations", "data_quality_score",
]


def _rows_to_csv(rows: list[dict], columns: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({col: row.get(col) for col in columns})
    return buffer.getvalue().encode("utf-8")


def _rows_to_xlsx(rows: list[dict], columns: list[str]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([str(row.get(col)) if row.get(col) is not None else "" for col in columns])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def export_tickets(
    scoped_client: Client,
    actor_id: UUID,
    fmt: str,
    columns: list[str] | None,
    filters: dict,
) -> bytes:
    cols = [c for c in (columns or TICKET_EXPORT_COLUMNS) if c in TICKET_EXPORT_COLUMNS]
    query = scoped_client.table("tickets").select("*")
    for key, value in filters.items():
        if value is not None:
            query = query.eq(key, value)
    rows = query.execute().data

    log_audit(actor_id, "export_performed", "export", None, {"type": "tickets", "format": fmt, "rows": len(rows), "filters": filters})
    return _rows_to_csv(rows, cols) if fmt == "csv" else _rows_to_xlsx(rows, cols)


def export_guests(scoped_client: Client, actor_id: UUID, fmt: str, columns: list[str] | None) -> bytes:
    cols = [c for c in (columns or GUEST_EXPORT_COLUMNS) if c in GUEST_EXPORT_COLUMNS]
    rows = scoped_client.table("guests").select("*").is_("merged_into", "null").execute().data

    log_audit(actor_id, "export_performed", "export", None, {"type": "guests", "format": fmt, "rows": len(rows)})
    return _rows_to_csv(rows, cols) if fmt == "csv" else _rows_to_xlsx(rows, cols)
