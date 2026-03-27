from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from app.config import settings


class TMSClient:

    def get_rate(
        self,
        origin_zip: str,
        destination_zip: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:

        if not settings.tms_base_url:
            raise RuntimeError("TMS_BASE_URL is missing.")

        if not settings.tms_username or not settings.tms_api_key:
            raise RuntimeError("TMS credentials are missing.")

        if not shipment.get("items"):
            raise RuntimeError("Shipment must contain at least one item.")

        payload = self._build_rate_request(
            origin_zip=origin_zip,
            destination_zip=destination_zip,
            shipment=shipment,
        )

        url = f"{settings.tms_base_url}/api/v1/RateShop/RateRequest"

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

            response.raise_for_status()

        except requests.RequestException as exc:
            raise RuntimeError(f"TMS rate request failed: {exc}") from exc

        # Handle empty responses
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
        origin_zip: str,
        destination_zip: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:

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
                    "Name": item.get("name") or f"Item {idx}",
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

        payload: Dict[str, Any] = {
            "Items": items,
            "PickupEvent": {
                "Date": pickup_date_str,
                "City": "PickCity",
                "State": "PickState",
                "Zip": origin_zip,
                "Country": "US",
            },
            "DropEvent": {
                "Date": drop_date_str,
                "City": "DropCity",
                "State": "DropState",
                "Zip": destination_zip,
                "Country": "US",
            },
            "Weight": total_weight,
        }

        return payload

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
