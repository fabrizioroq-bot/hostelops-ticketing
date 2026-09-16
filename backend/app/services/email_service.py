"""Transactional email via Resend. Swappable: any provider with a simple
HTTP send-email endpoint can replace this module without touching callers.
"""
import base64

import httpx

from app.core.config import get_settings


def send_email_with_attachment(
    to: list[str], subject: str, html: str, attachment_filename: str, attachment_bytes: bytes
) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is not configured — cannot send email.")
    if not to:
        return

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.resend_from_email,
            "to": to,
            "subject": subject,
            "html": html,
            "attachments": [
                {
                    "filename": attachment_filename,
                    "content": base64.b64encode(attachment_bytes).decode("ascii"),
                }
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
