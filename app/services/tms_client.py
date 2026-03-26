from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

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

        print("====== TMS RATE REQUEST PAYLOAD ======")
        print(json.dumps(payload, indent=2))
        print("======================================")

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

print("====== TMS RAW RESPONSE ======")
print(response.status_code)
print(response.text)
print("================================")
                
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"TMS rate request failed: {exc}") from exc

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
                f"TMS returned non-JSON response: "
                f"status_code={response.status_code}; "
                f"content_type={response.headers.get('Content-Type')!r}; "
                f"body={response.text!r}"
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
        drop_dt = (pickup_dt + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)

        pickup_date_str = pickup_dt.strftime("%m/%d/%Y %H:%M")
        drop_date_str = drop_dt.strftime("%m/%d/%Y %H:%M")

        items: List[Dict[str, Any]] = []

        for idx, item in enumerate(shipment.get("items", []), start=1):
            pieces_float = self._to_float(item.get("pieces")) or 1.0
            weight_float = self._to_float(item.get("weight")) or 0.0
            length = self._to_float(item.get("length"))
            width = self._to_float(item.get("width"))
            height = self._to_float(item.get("height"))

            pieces = int(round(pieces_float))
            if pieces < 1:
                pieces = 1

            weight = int(round(weight_float))
            if weight < 0:
                weight = 0

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
                    "QuantityUnits": "Unit",
                    "MonetaryValue": item.get("monetary_value"),
                    "Cube": item.get("cube"),
                }
            )

        total_weight_float = self._to_float(shipment.get("total_weight")) or 0.0
        total_weight = int(round(total_weight_float))
        if total_weight < 0:
            total_weight = 0

        payload: Dict[str, Any] = {
            "Constraints": {
                "Mode": shipment.get("mode"),
                "ContractType": shipment.get("contract_type"),
                "ContractName": shipment.get("contract_name"),
                "CarrierName": shipment.get("carrier_name"),
                "CarrierScac": shipment.get("carrier_scac"),
                "PaymentTerms": shipment.get("payment_terms"),
                "ServiceFlags": [],
                "Equipments": shipment.get("equipments"),
            },
            "Items": items,
            "PickupEvent": {
                "Date": pickup_date_str,
                "LocationCode": shipment.get("pickup_location_code"),
                "City": "PickCity",
                "State": "PickState",
                "Zip": origin_zip,
                "Country": shipment.get("origin_country", "US"),
            },
            "DropEvent": {
                "Date": drop_date_str,
                "LocationCode": shipment.get("drop_location_code"),
                "City": "DropCity",
                "State": "DropState",
                "Zip": destination_zip,
                "Country": shipment.get("destination_country", "US"),
            },
            "ReferenceNumbers": shipment.get("reference_numbers"),
            "RatingLevel": shipment.get("rating_level"),
            "RatingCount": shipment.get("rating_count"),
            "LinearFeet": shipment.get("linear_feet"),
            "ReturnAssociatedCarrierPricesheet": shipment.get(
                "return_associated_carrier_pricesheet"
            ),
            "MaxPriceSheet": shipment.get("max_price_sheet"),
            "ShowInsurance": shipment.get("show_insurance", True),
            "ShipmentValue": shipment.get("shipment_value"),
            "Weight": total_weight,
            "Stops": shipment.get("stops"),
        }

        return payload

    def _build_service_flags(self, shipment: Dict[str, Any]) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = [{"ServiceCode": "APPT"}]

        if shipment.get("residential"):
            flags.append({"ServiceCode": "RES1"})
        if shipment.get("liftgate"):
            flags.append({"ServiceCode": "LG1"})
        if shipment.get("limited_access"):
            flags.append({"ServiceCode": "LADDOCK"})

        ovl_candidates: List[int] = []
        for item in shipment.get("items", []):
            tier = item.get("overlength_tier")
            if tier in (None, "", 0, "0"):
                continue

            tier_str = str(tier).upper().replace("OVL", "").strip()
            if tier_str.isdigit():
                ovl_candidates.append(int(tier_str))

        if ovl_candidates:
            highest = max(ovl_candidates)
            flags.append({"ServiceCode": f"OVL{highest:02d}"})

        return flags

    def _select_best_rate(self, data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(data, list) or not data:
            return None

        explicitly_selected = [rate for rate in data if rate.get("IsSelected") is True]
        if explicitly_selected:
            return min(
                explicitly_selected,
                key=lambda rate: (
                    self._to_float(rate.get("Total"))
                    if self._to_float(rate.get("Total")) is not None
                    else float("inf"),
                    self._to_float(rate.get("ServiceDays"))
                    if self._to_float(rate.get("ServiceDays")) is not None
                    else float("inf"),
                ),
            )

        valid_rates = [rate for rate in data if self._to_float(rate.get("Total")) is not None]
        if not valid_rates:
            return None

        return min(
            valid_rates,
            key=lambda rate: (
                self._to_float(rate.get("Total"))
                if self._to_float(rate.get("Total")) is not None
                else float("inf"),
                self._to_float(rate.get("ServiceDays"))
                if self._to_float(rate.get("ServiceDays")) is not None
                else float("inf"),
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
