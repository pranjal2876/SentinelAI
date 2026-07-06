"""
Alert dispatch — Email (SMTP) and Telegram, plus the dashboard WebSocket push
(handled by the threat handler). All senders are async and best-effort: a
failed channel logs a warning but never breaks threat processing.
"""
from __future__ import annotations

from email.message import EmailMessage
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.vision.types import ThreatEvent


async def send_email_alert(event: ThreatEvent,
                           snapshot_path: Optional[str] = None) -> bool:
    """Send an email alert via SMTP (async). Returns success flag."""
    if not (settings.SMTP_HOST and settings.ALERT_EMAIL_TO):
        return False
    try:
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = settings.SMTP_USER or "sentinelai@localhost"
        msg["To"] = settings.ALERT_EMAIL_TO
        msg["Subject"] = (
            f"[SentinelAI] {event.severity.value.upper()} — "
            f"{event.category.value} @ {event.camera_id}"
        )
        msg.set_content(
            f"Threat: {event.category.value}\n"
            f"Severity: {event.severity.value}\n"
            f"Score: {event.score:.2f}\n"
            f"Camera: {event.camera_id}\n"
            f"Message: {event.message}\n"
            f"Metadata: {event.metadata}\n"
        )
        if snapshot_path:
            try:
                with open(snapshot_path, "rb") as f:
                    msg.add_attachment(f.read(), maintype="image",
                                       subtype="jpeg",
                                       filename="snapshot.jpg")
            except OSError:
                pass

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_PORT == 587,
        )
        logger.info(f"Email alert sent for {event.category.value}")
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Email alert failed: {exc}")
        return False


async def send_telegram_alert(event: ThreatEvent,
                              snapshot_path: Optional[str] = None) -> bool:
    """Send a Telegram alert (photo if snapshot available, else text)."""
    token, chat = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID
    if not (token and chat):
        return False
    caption = (
        f"🚨 *{event.severity.value.upper()}* — {event.category.value}\n"
        f"Camera: {event.camera_id}\n{event.message}\nScore: {event.score:.2f}"
    )
    base = f"https://api.telegram.org/bot{token}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if snapshot_path:
                with open(snapshot_path, "rb") as f:
                    resp = await client.post(
                        f"{base}/sendPhoto",
                        data={"chat_id": chat, "caption": caption,
                              "parse_mode": "Markdown"},
                        files={"photo": ("snapshot.jpg", f, "image/jpeg")},
                    )
            else:
                resp = await client.post(
                    f"{base}/sendMessage",
                    data={"chat_id": chat, "text": caption,
                          "parse_mode": "Markdown"},
                )
        resp.raise_for_status()
        logger.info(f"Telegram alert sent for {event.category.value}")
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Telegram alert failed: {exc}")
        return False


async def dispatch_alerts(event: ThreatEvent,
                          snapshot_path: Optional[str] = None) -> None:
    """Fan out an event to all configured alert channels."""
    if not settings.ALERTS_ENABLED:
        return
    # Only escalate email/telegram for HIGH+ to avoid noise.
    if event.severity.value in ("high", "critical"):
        await send_email_alert(event, snapshot_path)
        await send_telegram_alert(event, snapshot_path)
