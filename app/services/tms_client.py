from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import json
import logging
import requests

from app.config import settings

logger = logging.getLogger(__name__)

ORIGIN_MAP = {
    "US": {
        "zip": "90810",
        "country": "US",
        "city": "PickCity",
        "state": "PickState",
    },
    "CAN": {
        "zip": "V6C3T4",
        "country": "Canada",
        "city": "PickCity",
        "state": "PickState",
    },
}


class TMSClient:
    def get_rate(
        self,
        origin_mode: str,
        destination_code: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not settings.tms_base_url:
            raise RuntimeError("TMS_BASE_URL is missing.")

        if not settings.tms_username or not settings.tms_api_key:
            raise RuntimeError("TMS credentials are missing.")

        if not shipment.get("items"):
            raise RuntimeError("Shipment must contain at least one item.")

        payload = self._build_rate_request(
            origin_mode=origin_mode,
            destination_code=destination_code,
            shipment=shipment,
        )

        url = f"{settings.tms_base_url}/api/v1/RateShop/RateRequest"

        logger.info("TMS RATE REQUEST URL: %s", url)
        logger.info("TMS RATE REQUEST PAYLOAD: %s", json.dumps(payload))

        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    "ApiKey": settings.tms_api_key,
                    "UserName": settings.tms_username,
                    "Accept": "application/json",
                },
                timeout=settings.tms_timeout_seconds,
            )

            logger.info("TMS RATE RESPONSE STATUS: %s", response.status_code)
            logger.info("TMS RATE RESPONSE BODY: %s", response.text)

            response.raise_for_status()

        except requests.RequestException as exc:
            response_text = ""
            response_status = None
            if getattr(exc, "response", None) is not None:
                response_status = exc.response.status_code
                response_text = exc.response.text

            logger.exception(
                "TMS rate request failed. status=%s body=%s",
                response_status,
                response_text,
            )
            raise RuntimeError(
                f"TMS rate request failed: status={response_status}; body={response_text or str(exc)}"
            ) from exc

        if response.status_code == 204 or not response.text or not response.text.strip():
            return {
                "quote_id": None,
                "base_rate": None,
                "carrier": "",
                "contract_name": "",
                "scac": "",
                "service": "",
                "transit_days": None,
                "raw": [],
            }

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"TMS returned non-JSON response: {response.text}"
            ) from exc

        selected_rate = self._select_best_rate(data)

        if not selected_rate:
            return {
                "quote_id": None,
                "base_rate": None,
                "carrier": "",
                "contract_name": "",
                "scac": "",
                "service": "",
                "transit_days": None,
                "raw": data,
            }

        return {
            "quote_id": selected_rate.get("Id"),
            "base_rate": self._to_float(selected_rate.get("Total")),
            "carrier": selected_rate.get("CarrierName", ""),
            "contract_name": selected_rate.get("ContractName", ""),
            "scac": selected_rate.get("Scac", ""),
            "service": selected_rate.get("Service", ""),
            "transit_days": self._to_float(selected_rate.get("ServiceDays")),
            "raw": data,
        }

    def _build_rate_request(
        self,
        origin_mode: str,
        destination_code: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:
        origin = self._get_origin(origin_mode)
        destination_zip = self._normalize_location_code(destination_code)
        destination_country = self._detect_country_from_code(destination_zip)

        now = datetime.now()
        pickup_dt = now.replace(hour=8, minute=0, second=0, microsecond=0)
        drop_dt = pickup_dt + timedelta(days=1)

        pickup_date_str = pickup_dt.strftime("%m/%d/%Y %H:%M")
        drop_date_str = drop_dt.strftime("%m/%d/%Y %H:%M")

        items: List[Dict[str, Any]] = []

        for idx, item in enumerate(shipment.get("items", []), start=1):
            pieces = int(round(self._to_float(item.get("pieces")) or 1))
            weight = int(round(self._to_float(item.get("weight")) or 0))

            length = self._to_float(item.get("length"))
            width = self._to_float(item.get("width"))
            height = self._to_float(item.get("height"))

            items.append(
                {
                    "Name": item.get("component") or f"Item {idx}",
                    "FreightClass": str(item.get("freight_class", "")),
                    "Weight": weight,
                    "WeightUnits": "lb",
                    "Width": width,
                    "Length": length,
                    "Height": height,
                    "DimensionUnits": "in",
                    "Quantity": pieces,
                    "QuantityUnits": "PLT",
                }
            )

        total_weight = int(round(self._to_float(shipment.get("total_weight")) or 0))

        destination_city = str(
            shipment.get("destination_city")
            or shipment.get("drop_city")
            or "DropCity"
        ).strip()

        destination_state = str(
            shipment.get("destination_state")
            or shipment.get("destination_province")
            or shipment.get("drop_state")
            or "DropState"
        ).strip()

        payload: Dict[str, Any] = {
            "Items": items,
            "PickupEvent": {
                "Date": pickup_date_str,
                "City": origin["city"],
                "State": origin["state"],
                "Zip": origin["zip"],
                "Country": origin["country"],
            },
            "DropEvent": {
                "Date": drop_date_str,
                "City": destination_city,
                "State": destination_state,
                "Zip": destination_zip,
                "Country": destination_country,
            },
            "Weight": total_weight,
        }

        return payload

    def _get_origin(self, origin_mode: str) -> Dict[str, str]:
        mode = str(origin_mode or "").strip().upper()

        if mode not in ORIGIN_MAP:
            allowed = ", ".join(ORIGIN_MAP.keys())
            raise RuntimeError(f"Unsupported origin mode '{origin_mode}'. Allowed values: {allowed}")

        return ORIGIN_MAP[mode]

    def _normalize_location_code(self, code: str) -> str:
        cleaned = str(code or "").strip().upper().replace(" ", "")
        if not cleaned:
            raise RuntimeError("Destination code is required.")
        return cleaned

    def _detect_country_from_code(self, code: str) -> str:
        first_char = code[0]

        if first_char.isalpha():
            return "Canada"

        if first_char.isdigit():
            return "US"

        raise RuntimeError(
            f"Could not determine destination country from destination code '{code}'."
        )

    def _select_best_rate(self, data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(data, list) or not data:
            return None

        valid_rates = [
            rate for rate in data
            if self._to_float(rate.get("Total")) is not None
        ]

        if not valid_rates:
            return None

        return min(
            valid_rates,
            key=lambda rate: (
                self._to_float(rate.get("Total")),
                self._to_float(rate.get("ServiceDays")) or float("inf"),
            ),
        )

    def _to_float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None


tms_client = TMSClient()
