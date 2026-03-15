"""Email delivery service for legal notices.

Sends the PDF notice via email to either:
- The complainant (self-send tier, ₹199) — user gets PDF to forward/print/send
- The company + complainant copy (lawyer tier, ₹599) — sent from advocate's
  verified email address with read-receipt request

In production, wire this to a transactional email provider (AWS SES,
SendGrid, Postmark) for deliverability and tracking.
"""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_name: str
    from_email: str
    use_tls: bool = True


@dataclass
class DeliveryResult:
    success: bool
    message: str
    recipients: list[str]
    message_id: str | None = None


def _load_config() -> EmailConfig:
    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        from_name=os.getenv("NOTICE_FROM_NAME", "LegalNotice AI"),
        from_email=os.getenv("NOTICE_FROM_EMAIL", ""),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    )


def send_notice_email(
    *,
    to_email: str,
    to_name: str,
    cc_emails: list[str] | None = None,
    subject: str,
    body_text: str,
    pdf_bytes: bytes,
    pdf_filename: str = "Legal_Notice.pdf",
    request_read_receipt: bool = False,
) -> DeliveryResult:
    """Send a legal notice PDF as an email attachment.

    Args:
        to_email: Primary recipient email.
        to_name: Primary recipient display name.
        cc_emails: Optional CC recipients.
        subject: Email subject line.
        body_text: Plain text email body.
        pdf_bytes: The PDF file content.
        pdf_filename: Attachment filename.
        request_read_receipt: If True, adds Disposition-Notification-To header.

    Returns:
        DeliveryResult with success status.
    """
    config = _load_config()

    if not config.smtp_user or not config.from_email:
        return DeliveryResult(
            success=False,
            message="Email not configured. Set SMTP_USER, SMTP_PASSWORD, and NOTICE_FROM_EMAIL in .env",
            recipients=[to_email],
        )

    msg = EmailMessage()
    msg["From"] = formataddr((config.from_name, config.from_email))
    msg["To"] = formataddr((to_name, to_email))
    msg["Subject"] = subject

    if cc_emails:
        msg["Cc"] = ", ".join(cc_emails)

    if request_read_receipt:
        msg["Disposition-Notification-To"] = config.from_email
        msg["X-Confirm-Reading-To"] = config.from_email

    msg.set_content(body_text)
    if pdf_bytes and pdf_filename:
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=pdf_filename,
        )

    all_recipients = [to_email] + (cc_emails or [])

    try:
        if config.use_tls:
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)
                message_id = msg.get("Message-ID", "")
        else:
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)
                message_id = msg.get("Message-ID", "")

        return DeliveryResult(
            success=True,
            message=f"Notice delivered to {', '.join(all_recipients)}",
            recipients=all_recipients,
            message_id=message_id,
        )
    except smtplib.SMTPException as e:
        return DeliveryResult(
            success=False,
            message=f"SMTP error: {e}",
            recipients=all_recipients,
        )


def build_self_send_body(complainant_name: str, company_name: str) -> str:
    """Build email body for self-send (₹199) tier."""
    return (
        f"Dear {complainant_name},\n\n"
        f"Your legal notice regarding {company_name} is attached as a PDF.\n\n"
        f"Next steps:\n"
        f"1. Review the notice carefully and fill in any [placeholder] fields\n"
        f"2. Forward the attached PDF to the company's official grievance email\n"
        f"   with 'read receipt' / 'delivery receipt' enabled as proof of service\n"
        f"3. Also CC the notice to any regulatory stakeholders listed in the\n"
        f"   escalation strategy section of the notice\n"
        f"4. Save all sent-email confirmations and read receipts for your records\n"
        f"5. If no response within the cure period stated in the notice, you may file a\n"
        f"   consumer complaint via e-daakhil.nic.in\n\n"
        f"This notice was generated by an AI system and has NOT been reviewed by a lawyer.\n"
        f"For legal review, consider upgrading to the Lawyer-Assisted tier (₹599).\n\n"
        f"Regards,\n"
        f"LegalNotice AI"
    )


def build_lawyer_send_body(
    complainant_name: str,
    company_name: str,
    company_email: str,
) -> str:
    """Build email body for lawyer-assisted (₹599) tier — sent to company."""
    return (
        f"Dear Sir/Madam,\n\n"
        f"Under instructions from my client, {complainant_name}, I am serving upon you "
        f"the enclosed Legal Notice regarding your deficient service/product.\n\n"
        f"Please find the Legal Notice annexed hereto as a PDF attachment.\n\n"
        f"You are required to comply with the demands set forth therein within the cure "
        f"period specified in the notice, failing which my client shall be constrained to "
        f"initiate appropriate proceedings before the competent Consumer Disputes Redressal "
        f"Commission, at your risk, cost, and consequences.\n\n"
        f"This email constitutes valid electronic service of notice.\n\n"
        f"Kindly acknowledge receipt of this notice.\n\n"
        f"Yours faithfully,\n"
        f"[Advocate Name]\n"
        f"[Enrollment No.]\n"
        f"On behalf of: {complainant_name}"
    )
