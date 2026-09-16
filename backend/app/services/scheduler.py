"""Weekly scheduled job: generate the PDF summary and email it to every
active admin/supervisor. Registered on FastAPI startup (see app/main.py).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.db.supabase_client import get_service_client
from app.services.email_service import send_email_with_attachment
from app.services.report_service import generate_weekly_pdf

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()


def _weekly_report_job() -> None:
    settings = get_settings()
    client = get_service_client()
    resp = (
        client.table("app_users")
        .select("email")
        .in_("role", ["admin", "supervisor"])
        .eq("is_active", True)
        .execute()
    )
    recipients = list({row["email"] for row in resp.data} | set(settings.report_recipient_list))
    if not recipients:
        logger.warning("Weekly report job: no admin/supervisor recipients found, skipping send.")
        return

    try:
        pdf_bytes = generate_weekly_pdf()
        send_email_with_attachment(
            to=recipients,
            subject="HostelOps — Weekly Ticket Summary",
            html="<p>Attached is the weekly ticket summary across all hostels.</p>",
            attachment_filename="weekly-ticket-summary.pdf",
            attachment_bytes=pdf_bytes,
        )
        logger.info("Weekly report sent to %d recipients.", len(recipients))
    except Exception:
        logger.exception("Failed to generate/send the weekly report.")


def start_scheduler() -> None:
    if not get_settings().resend_api_key:
        logger.warning("RESEND_API_KEY not set — weekly report emails will fail when the job runs.")
    if not _scheduler.running:
        _scheduler.add_job(
            _weekly_report_job,
            trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
            id="weekly_report",
            replace_existing=True,
        )
        _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
