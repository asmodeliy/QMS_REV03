"""
Help and Feedback Routes

Provides help documentation, FAQ, and feedback submission system.
"""

import json
import smtplib
import time
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import BASE_DIR, OUTLOOK_EMAIL, OUTLOOK_PASSWORD, ADMIN_NOTIFICATION_EMAIL
from core.i18n import get_locale, t

router = APIRouter()

templates = None


def set_templates(tmpl):
    """Set Jinja2 templates engine"""
    global templates
    templates = tmpl


# Feedback file configuration
FEEDBACK_DIR = BASE_DIR / "data"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_FILE = FEEDBACK_DIR / "feedback.json"


def load_feedbacks() -> list:
    """Load all feedbacks from JSON file"""
    if not FEEDBACK_FILE.exists():
        return []
    try:
        content = FEEDBACK_FILE.read_text(encoding="utf-8")
        return json.loads(content) if content else []
    except Exception:
        return []


def save_feedbacks(feedbacks: list) -> None:
    """Save feedbacks to JSON file"""
    try:
        content = json.dumps(feedbacks, ensure_ascii=False, indent=2)
        FEEDBACK_FILE.write_text(content, encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to save feedbacks: {e}")


def send_admin_notification(feedback: dict) -> None:
    """Send admin notification email about new feedback"""
    if not OUTLOOK_EMAIL or not OUTLOOK_PASSWORD:
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = OUTLOOK_EMAIL
        msg['To'] = ADMIN_NOTIFICATION_EMAIL
        msg['Subject'] = f"[QMS] New Feedback: {feedback.get('type', 'Other')}"

        body = (
            f"New feedback received.\n\n"
            f"Type: {feedback.get('type', 'Other')}\n"
            f"From: {feedback.get('email') or '(Anonymous)'}\n"
            f"Message: {feedback.get('message', '')}\n"
            f"Page: {feedback.get('url') or '(Unknown)'}\n"
            f"Time: {feedback.get('timestamp', '')}\n\n"
            f"Review: http://localhost:8000/admin/feedback"
        )

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[ERROR] Failed to send admin notification: {e}")


def send_reply_email(feedback_id: int, reply_message: str) -> None:
    """Send reply email to feedback submitter"""
    feedbacks = load_feedbacks()
    feedback = next((f for f in feedbacks if f.get('id') == feedback_id), None)

    if not feedback or not feedback.get('email'):
        return

    if not OUTLOOK_EMAIL or not OUTLOOK_PASSWORD:
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = OUTLOOK_EMAIL
        msg['To'] = feedback['email']
        msg['Subject'] = '[QMS] Feedback Response'

        body = (
            f"Hello,\n\n"
            f"Thank you for your feedback.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Your message:\n{feedback.get('message', '')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Our response:\n{reply_message}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Thank you.\nQMS Support Team"
        )

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(OUTLOOK_EMAIL, OUTLOOK_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[ERROR] Failed to send reply email: {e}")


# ============================================================================
# ROUTES
# ============================================================================

@router.get("/help", response_class=HTMLResponse)
def help_page(request: Request):
    """Display help page with documentation"""
    locale = get_locale(request)
    return templates.TemplateResponse(
        "shared/help.html",
        {
            "request": request,
            "locale": locale,
            "page_title": t("common.help", locale)
        }
    )


@router.post("/api/help/feedback")
def submit_feedback(request: Request):
    """Submit new feedback"""
    try:
        form_data = dict(request.form)
        new_feedback = {
            "id": int(time.time() * 1000),
            "type": form_data.get("type", "Bug"),
            "email": form_data.get("email", ""),
            "message": form_data.get("message", ""),
            "url": str(request.url.path),
            "timestamp": datetime.now().isoformat(),
            "status": "Unread"
        }

        feedbacks = load_feedbacks()
        feedbacks.append(new_feedback)
        save_feedbacks(feedbacks)
        send_admin_notification(new_feedback)

        return JSONResponse({"success": True, "id": new_feedback["id"]})
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("/api/help/feedback")
def get_feedbacks(request: Request):
    """Get all feedbacks (admin only)"""
    session = getattr(request, 'session', {})
    if not session.get('is_authenticated') or session.get('role') != 'admin':
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    return JSONResponse(load_feedbacks())


@router.post("/api/help/feedback/{feedback_id}/reply")
def reply_feedback(feedback_id: int, request: Request):
    """Reply to a feedback (admin only)"""
    session = getattr(request, 'session', {})
    if not session.get('is_authenticated') or session.get('role') != 'admin':
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    try:
        form_data = dict(request.form)
        reply_message = form_data.get("reply_message", "")

        feedbacks = load_feedbacks()
        feedback = next((f for f in feedbacks if f.get('id') == feedback_id), None)

        if feedback:
            feedback['status'] = 'Resolved'
            feedback['reply'] = reply_message
            feedback['reply_date'] = datetime.now().isoformat()
            save_feedbacks(feedbacks)
            send_reply_email(feedback_id, reply_message)
            return JSONResponse({"success": True})

        return JSONResponse({"error": "Feedback not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
