# ============================================================
# app/services/email_service.py — Email Notification Service
# Uses Flask-Mail + SMTP (Gmail / any SMTP provider)
# ============================================================
import logging
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail

logger = logging.getLogger(__name__)

# ── Email templates (inline; move to files in Phase 10) ─────

LOW_ATTENDANCE_TEMPLATE = """
<h2>Low Attendance Alert</h2>
<p>Dear <b>{{ name }}</b>,</p>
<p>Your attendance has dropped to <b>{{ pct }}%</b> in <b>{{ subject }}</b>.</p>
<p>Minimum required: <b>{{ threshold }}%</b>. Please attend classes regularly.</p>
<p>— Smart Campus System</p>
"""

HIGH_RISK_TEMPLATE = """
<h2>Academic Risk Alert</h2>
<p>Dear <b>{{ name }}</b>,</p>
<p>Our system has identified you as <b>HIGH RISK</b> this semester.</p>
<p>Attendance: {{ attend_pct }}% | Avg Marks: {{ avg_marks }}</p>
<p>Please meet your faculty advisor immediately.</p>
<p>— Smart Campus System</p>
"""


class EmailService:

    @staticmethod
    def send_low_attendance_alert(student, subject_name: str, pct: float, threshold: float):
        """Send a low attendance warning email to a student."""
        body = render_template_string(
            LOW_ATTENDANCE_TEMPLATE,
            name=student.name,
            pct=round(pct, 1),
            subject=subject_name,
            threshold=threshold,
        )
        EmailService._send(
            to=student.email,
            subject=f'⚠️ Low Attendance Alert – {subject_name}',
            html_body=body,
        )

    @staticmethod
    def send_high_risk_alert(student, attend_pct: float, avg_marks: float):
        """Send a high academic risk alert to a student."""
        body = render_template_string(
            HIGH_RISK_TEMPLATE,
            name=student.name,
            attend_pct=round(attend_pct, 1),
            avg_marks=round(avg_marks, 1),
        )
        EmailService._send(
            to=student.email,
            subject='🚨 Academic Risk Alert – Immediate Action Required',
            html_body=body,
        )

    @staticmethod
    def send_security_alert(admin_email: str, image_path: str, location: str):
        """Notify admin of an unknown face / security event."""
        EmailService._send(
            to=admin_email,
            subject='🔴 Campus Security Alert – Unknown Person Detected',
            html_body=f'<p>Unknown face detected at <b>{location}</b>.</p>'
                      f'<p>Image saved at: {image_path}</p>',
        )

    @staticmethod
    def _send(to: str, subject: str, html_body: str):
        """Internal helper — sends an HTML email."""
        try:
            msg = Message(
                subject=subject,
                recipients=[to],
                html=html_body,
            )
            mail.send(msg)
            logger.info(f'Email sent to {to}: {subject}')
        except Exception as e:
            logger.error(f'Failed to send email to {to}: {e}')
