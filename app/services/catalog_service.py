from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings
from app.util.helpers import (
    clean_header,
    normalize_bool,
    parse_currency,
    parse_float,
    parse_percentage,
    require_value,
)


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


class CatalogService:
    def __init__(self) -> None:
        self._catalog: Optional[Dict[str, Any]] = None
        self._last_refresh: Optional[datetime] = None

    def is_loaded(self) -> bool:
        return self._catalog is not None

    def last_refresh_iso(self) -> Optional[str]:
        if not self._last_refresh:
            return None
        return self._last_refresh.astimezone(timezone.utc).isoformat()

    def get_catalog(self) -> Dict[str, Any]:
        self.refresh(force=False)
        if self._catalog is None:
            raise RuntimeError("Catalog failed to load.")
        return self._catalog

    def refresh(self, force: bool = False) -> None:
        now = datetime.now(timezone.utc)
        if (
            not force
            and self._catalog is not None
            and self._last_refresh is not None
            and (now - self._last_refresh).total_seconds() < settings.catalog_refresh_ttl_seconds
        ):
            return

        client = self._build_gspread_client()
        spreadsheet = client.open_by_key(settings.google_sheet_id)

        sku_xref_rows = self._load_sku_xref(spreadsheet.worksheet(settings.tab_sku_xref))
        rc_master_rows = self._load_rc_master(spreadsheet.worksheet(settings.tab_rc_master))
        inputs_map = self._load_inputs(spreadsheet.worksheet(settings.tab_inputs))

        self._catalog = {
            "sku_xref_rows": sku_xref_rows,
            "rc_master_rows": rc_master_rows,
            "inputs_map": inputs_map,
        }
        self._last_refresh = now

    def _build_gspread_client(self) -> gspread.Client:
        service_account_info = settings.service_account_info()
        if service_account_info:
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=GOOGLE_SCOPES,
            )
            return gspread.authorize(creds)

        if settings.google_service_account_file:
            creds = Credentials.from_service_account_file(
                settings.google_service_account_file,
                scopes=GOOGLE_SCOPES,
            )
            return gspread.authorize(creds)

        raise RuntimeError(
            "Google credentials missing. Set GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE."
        )

    def _load_sku_xref(self, worksheet: gspread.Worksheet) -> List[Dict[str, Any]]:
        raw = worksheet.get_all_records(default_blank="")
        rows: List[Dict[str, Any]] = []

        for row in raw:
            normalized = {clean_header(k): v for k, v in row.items()}
            rc_product_number = str(normalized.get("RC Product Number", "")).strip()
            if not rc_product_number:
                continue

            rows.append(
                {
                    "rc_product_number": rc_product_number,
                    "gametime": str(normalized.get("GameTime", "")).strip(),
                    "park_and_play_structures": str(normalized.get("Park and Play Structures", "")).strip(),
                    "superior_recreational_products": str(normalized.get("Superior Recreational Products", "")).strip(),
                    "playcraft": str(normalized.get("Playcraft", "")).strip(),
                    "msrp": parse_currency(normalized.get("MSRP", 0)),
                    "active": normalize_bool(normalized.get("Active", True)),
                }
            )

        return rows

    def _load_rc_master(self, worksheet: gspread.Worksheet) -> List[Dict[str, Any]]:
        raw = worksheet.get_all_records(default_blank="")
        rows: List[Dict[str, Any]] = []

        for row in raw:
            normalized = {clean_header(k): v for k, v in row.items()}
            rc_product_number = str(normalized.get("RC Product Number", "")).strip()
            if not rc_product_number:
                continue

            rows.append(
                {
                    "rc_product_number": rc_product_number,
                    "component": str(normalized.get("Component", "")).strip(),
                    "pieces": int(parse_float(normalized.get("Pieces", 0))),
                    "length": parse_float(normalized.get("Length", 0)),
                    "width": parse_float(normalized.get("Width", 0)),
                    "height": parse_float(normalized.get("Height", 0)),
                    "weight": parse_float(normalized.get("Weight", 0)),
                    "density": parse_float(normalized.get("Density", 0)),
                    "freight_class": str(normalized.get("Freight Class", "")).strip(),
                    "overlength_tier": str(normalized.get("Overlength Tier", "")).strip(),
                    "active": normalize_bool(normalized.get("Active", True)),
                }
            )

        return rows

    def _load_inputs(self, worksheet: gspread.Worksheet) -> Dict[str, Any]:
        raw = worksheet.get_all_records(default_blank="")
        inputs_map: Dict[str, Any] = {}

        for row in raw:
            normalized = {clean_header(k): v for k, v in row.items()}
            setting = str(normalized.get("Setting", "") or normalized.get("Settings", "")).strip()
            value = normalized.get("Value", "")

            if not setting:
                continue

            inputs_map[setting] = value

        require_value(inputs_map, "Uplift Percentage")
        require_value(inputs_map, "Flat Min. y/n")
        require_value(inputs_map, "Flat Min Value")
        require_value(inputs_map, "Min % MSRP")

        inputs_map["_parsed"] = {
            "uplift_percentage": parse_percentage(inputs_map["Uplift Percentage"]),
            "flat_min_enabled": normalize_bool(inputs_map["Flat Min. y/n"]),
            "flat_min_value": parse_currency(inputs_map["Flat Min Value"]),
            "min_pct_msrp": parse_percentage(inputs_map["Min % MSRP"]),
        }

        return inputs_map


catalog_service = CatalogService()
