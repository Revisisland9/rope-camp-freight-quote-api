import smtplib
from email.mime.text import MIMEText
from typing import Any, Dict, List

from app.config import settings
from app.util.helpers import parse_email_list


class EmailService:
    def get_recipients_from_inputs(self, inputs_map: Dict[str, Any]) -> List[str]:
        raw = inputs_map.get("Quote Email Recipients", "")
        return parse_email_list(raw)

    def send_quote_email(
        self,
        recipients: List[str],
        company: str,
        sku: str,
        destination_zip: str,
        origin_zip: str,
        rc_product_number: str,
        shipment: Dict[str, Any],
        priced_result: Dict[str, Any],
    ) -> None:
        if not recipients:
            return

        if not settings.smtp_host or not settings.email_from:
            raise RuntimeError(
                "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM."
            )

        subject = f"Rope Camp Freight Quote — {company} {sku} → {destination_zip}"

        body = (
            f"Origin ZIP: {origin_zip}\n"
            f"Destination ZIP: {destination_zip}\n\n"
            f"Company: {company}\n"
            f"SKU: {sku}\n"
            f"RC Product Number: {rc_product_number}\n\n"
            f"Shipment Pieces: {shipment['total_pieces']}\n"
            f"Total Weight: {shipment['total_weight']} lbs\n"
            f"Carrier: {priced_result.get('carrier', '')}\n"
            f"Service: {priced_result.get('service', '')}\n"
            f"Transit Days: {priced_result.get('transit_days', '')}\n\n"
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
