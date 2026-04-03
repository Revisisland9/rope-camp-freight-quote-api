import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List

from app.config import settings
from app.util.helpers import parse_email_list


class EmailService:
    def get_recipients_from_inputs(self, inputs_map: Dict[str, Any]) -> List[str]:
        raw = inputs_map.get("Quote Email Recipients", "")
        return parse_email_list(raw)

    def get_recipients(
        self,
        email_to: str = "",
        inputs_map: Dict[str, Any] | None = None,
    ) -> List[str]:
        explicit = parse_email_list(email_to)

        fallback: List[str] = []
        if inputs_map:
            fallback = self.get_recipients_from_inputs(inputs_map)

        recipients: List[str] = []
        seen = set()

        for email in explicit + fallback:
            key = email.strip().lower()
            if key and key not in seen:
                seen.add(key)
                recipients.append(email.strip())

        return recipients

    def send_quote_email(
        self,
        recipients: List[str],
        quote_number: str,
        company: str,
        sku: str,
        destination_zip: str,
        origin_zip: str,
        rc_product_number: str,
        shipment: Dict[str, Any],
        priced_result: Dict[str, Any],
        customer_name: str = "",
        rep_name: str = "",
        project_name: str = "",
    ) -> None:
        if not recipients:
            return

        if not settings.smtp_host or not settings.email_from:
            raise RuntimeError(
                "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM."
            )

        subject = f"Rope Camp Freight Quote {quote_number} — {company} {sku} → {destination_zip}"

        body = (
            f"Quote Number: {quote_number}\n\n"
            f"Customer Name: {customer_name}\n"
            f"Rep Name: {rep_name}\n"
            f"Project Name: {project_name}\n\n"
            f"Origin ZIP: {origin_zip}\n"
            f"Destination ZIP: {destination_zip}\n\n"
            f"Company: {company}\n"
            f"SKU: {sku}\n"
            f"RC Product Number: {rc_product_number}\n\n"
            f"Pieces per Unit: {shipment.get('pieces_per_unit', '')}\n"
            f"Shipment Pieces: {shipment.get('total_pieces', '')}\n"
            f"Total Weight: {shipment.get('total_weight', '')} lbs\n\n"
            f"Quoted Freight: ${priced_result['final_quote']:.2f}\n"
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = ", ".join(recipients)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.email_from, recipients, msg.as_string())


email_service = EmailService()
