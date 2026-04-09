from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class QuoteResponse(BaseModel):
    ok: bool

    company: str

    skus: List[str]
    rc_product_numbers: List[str]

    destination_zip: str
    origin_zip: str

    shipment: Dict[str, Any]
    tms: Dict[str, Any]
    pricing: Dict[str, Any]

    emailed_to: List[str] = []

    quote_number: Optional[str] = None
    email_error: Optional[str] = None
