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

        payload = self._build_rate_request(
            origin_zip=origin_zip,
            destination_zip=destination_zip,
            shipment=shipment,
        )

        url = f"{settings.tms_base_url.rstrip('/')}/api/v1/RateShop/RateRequest"

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

        data = response.json()
        selected_rate = self._select_best_rate(data)

        if not selected_rate:
            return {
                "base_rate": None,
                "carrier": "",
                "scac": "",
                "service": "",
                "transit_days": None,
                "raw": data,
            }

        return {
            "base_rate": self._to_float(selected_rate.get("Total")),
            "carrier": selected_rate.get("CarrierName", ""),
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
        items: List[Dict[str, Any]] = []

        for idx, item in enumerate(shipment.get("items", []), start=1):
            pieces = self._to_float(item.get("pieces")) or 1.0
            weight = self._to_float(item.get("weight")) or 0.0
            length = self._to_float(item.get("length"))
            width = self._to_float(item.get("width"))
            height = self._to_float(item.get("height"))

            item_payload: Dict[str, Any] = {
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
            items.append(item_payload)

        service_flags = self._build_service_flags(shipment)

        pickup_date = shipment.get("pickup_date")
        drop_date = shipment.get("drop_date")

        payload: Dict[str, Any] = {
            "Constraints": {
                "Mode": shipment.get("mode"),
                "ContractType": shipment.get("contract_type"),
                "ContractName": shipment.get("contract_name"),
                "CarrierName": shipment.get("carrier_name"),
                "CarrierScac": shipment.get("carrier_scac"),
                "PaymentTerms": shipment.get("payment_terms"),
                "ServiceFlags": service_flags,
                "Equipments": shipment.get("equipments"),
            },
            "Items": items,
            "PickupEvent": {
                "Date": pickup_date,
                "LocationCode": shipment.get("pickup_location_code"),
                "City": shipment.get("origin_city"),
                "State": shipment.get("origin_state"),
                "Zip": origin_zip,
                "Country": shipment.get("origin_country", "US"),
            },
            "DropEvent": {
                "Date": drop_date,
                "LocationCode": shipment.get("drop_location_code"),
                "City": shipment.get("destination_city"),
                "State": shipment.get("destination_state"),
                "Zip": destination_zip,
                "Country": shipment.get("destination_country", "US"),
            },
            "ReferenceNumbers": shipment.get("reference_numbers"),
            "RatingLevel": shipment.get("rating_level"),
            "RatingCount": shipment.get("rating_count"),
            "LinearFeet": shipment.get("linear_feet"),
            "ReturnAssociatedCarrierPricesheet": shipment.get("return_associated_carrier_pricesheet"),
            "MaxPriceSheet": shipment.get("max_price_sheet"),
            "ShowInsurance": shipment.get("show_insurance", True),
            "ShipmentValue": shipment.get("shipment_value"),
            "Weight": shipment.get("total_weight"),
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

        explicitly_selected = [r for r in data if r.get("IsSelected") is True]
        if explicitly_selected:
            return min(
                explicitly_selected,
                key=lambda r: (
                    self._to_float(r.get("Total")) if self._to_float(r.get("Total")) is not None else float("inf"),
                    self._to_float(r.get("ServiceDays")) if self._to_float(r.get("ServiceDays")) is not None else float("inf"),
                ),
            )

        valid_rates = [r for r in data if self._to_float(r.get("Total")) is not None]
        if not valid_rates:
            return None

        return min(
            valid_rates,
            key=lambda r: (
                self._to_float(r.get("Total")) if self._to_float(r.get("Total")) is not None else float("inf"),
                self._to_float(r.get("ServiceDays")) if self._to_float(r.get("ServiceDays")) is not None else float("inf"),
            ),
        )

    def _to_float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _mock_rate(
        self,
        origin_zip: str,
        destination_zip: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:
        total_weight = float(shipment.get("total_weight", 0))
        total_pieces = int(shipment.get("total_pieces", 0))
        overlength_count = sum(1 for x in shipment.get("items", []) if x.get("overlength_tier"))

        base_rate = 250 + (total_weight * 0.58) + (total_pieces * 35) + (overlength_count * 85)

        return {
            "base_rate": round(base_rate, 2),
            "carrier": "MOCK CARRIER",
            "scac": "MOCK",
            "service": "LTL",
            "transit_days": 3,
            "raw": {
                "origin_zip": origin_zip,
                "destination_zip": destination_zip,
                "total_weight": total_weight,
            },
        }


tms_client = TMSClient()
