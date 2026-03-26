from typing import Any, Dict

import requests

from app.config import settings


class TMSClient:
    def get_rate(
        self,
        origin_zip: str,
        destination_zip: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:
        if settings.tms_use_mock:
            return self._mock_rate(
                origin_zip=origin_zip,
                destination_zip=destination_zip,
                shipment=shipment,
            )

        if not settings.tms_base_url:
            raise RuntimeError("TMS_BASE_URL is missing.")
        if not settings.tms_username or not settings.tms_api_key:
            raise RuntimeError("TMS credentials are missing.")

        # Replace this payload with your real TMS rate request contract.
        payload = {
            "originZip": origin_zip,
            "destinationZip": destination_zip,
            "items": [
                {
                    "pieces": item["pieces"],
                    "length": item["length"],
                    "width": item["width"],
                    "height": item["height"],
                    "weight": item["weight"],
                    "freightClass": item["freight_class"],
                    "overlengthTier": item["overlength_tier"],
                }
                for item in shipment["items"]
            ],
        }

        url = f"{settings.tms_base_url}/quote"

        response = requests.post(
            url,
            json=payload,
            headers={
                "UserName": settings.tms_username,
                "ApiKey": settings.tms_api_key,
                "Accept": "application/json",
            },
            timeout=settings.tms_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        # Adjust mapping to your actual TMS response.
        return {
            "base_rate": float(data["base_rate"]),
            "carrier": data.get("carrier", ""),
            "service": data.get("service", ""),
            "transit_days": data.get("transit_days"),
            "raw": data,
        }

    def _mock_rate(
        self,
        origin_zip: str,
        destination_zip: str,
        shipment: Dict[str, Any],
    ) -> Dict[str, Any]:
        total_weight = float(shipment["total_weight"])
        total_pieces = int(shipment["total_pieces"])
        overlength_count = sum(1 for x in shipment["items"] if x.get("overlength_tier"))

        base_rate = 250 + (total_weight * 0.58) + (total_pieces * 35) + (overlength_count * 85)

        return {
            "base_rate": round(base_rate, 2),
            "carrier": "MOCK CARRIER",
            "service": "LTL",
            "transit_days": 3,
            "raw": {
                "origin_zip": origin_zip,
                "destination_zip": destination_zip,
                "total_weight": total_weight,
            },
        }


tms_client = TMSClient()
