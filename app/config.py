import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "dev")
    google_sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")
    google_service_account_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    google_service_account_file: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    catalog_refresh_ttl_seconds: int = int(os.getenv("CATALOG_REFRESH_TTL_SECONDS", "3600"))

    # TMS
    tms_base_url: str = os.getenv("TMS_BASE_URL", "").rstrip("/")
    tms_username: str = os.getenv("TMS_USERNAME", "")
    tms_api_key: str = os.getenv("TMS_API_KEY", "")
    tms_timeout_seconds: int = int(os.getenv("TMS_TIMEOUT_SECONDS", "30"))

    # Email
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    email_from: str = os.getenv("EMAIL_FROM", "")

    # Sheet tabs
    tab_sku_xref: str = os.getenv("TAB_SKU_XREF", "SKU_XREF")
    tab_rc_master: str = os.getenv("TAB_RC_MASTER", "RC_MASTER")
    tab_inputs: str = os.getenv("TAB_INPUTS", "INPUTS")

    def service_account_info(self) -> Optional[dict]:
        if self.google_service_account_json:
            return json.loads(self.google_service_account_json)
        return None


settings = Settings()
