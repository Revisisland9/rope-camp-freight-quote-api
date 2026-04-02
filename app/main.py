from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.request_models import QuoteRequest
from app.models.response_models import QuoteResponse
from app.services.catalog_service import catalog_service
from app.services.sku_lookup import resolve_rc_product
from app.services.shipment_builder import build_shipment
from app.services.tms_client import tms_client
from app.services.pricing_engine import apply_pricing_logic
from app.services.email_service import email_service

app = FastAPI(
    title="Freight Quote Engine",
    version="1.0.0"
)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "freight-quote-engine",
        "catalog_loaded": catalog_service.is_loaded(),
        "catalog_last_refresh_utc": catalog_service.last_refresh_iso(),
        "refresh_ttl_seconds": settings.catalog_refresh_ttl_seconds,
    }


@app.post("/admin/refresh")
def refresh_catalog() -> dict:
    catalog_service.refresh(force=True)
    return {
        "ok": True,
        "catalog_last_refresh_utc": catalog_service.last_refresh_iso(),
    }


@app.post("/quote", response_model=QuoteResponse)
def quote(request: QuoteRequest) -> QuoteResponse:
    try:
        catalog = catalog_service.get_catalog()

        sku_row = resolve_rc_product(
            sku_xref_rows=catalog["sku_xref_rows"],
            company=request.company,
            sku=request.sku,
        )

        if not sku_row["active"]:
            raise HTTPException(status_code=400, detail="Selected SKU is inactive.")

        shipment = build_shipment(
            rc_master_rows=catalog["rc_master_rows"],
            rc_product_number=sku_row["rc_product_number"],
            quantity=request.quantity,
        )

        tms_result = tms_client.get_rate(
            origin_zip=request.origin_zip,
            destination_zip=request.destination_zip,
            shipment=shipment,
        )

        priced = apply_pricing_logic(
            tms_result=tms_result,
            msrp=sku_row["msrp"],
            inputs_map=catalog["inputs_map"],
        )

        recipients = []
        email_error = None

        # New behavior:
        # 1. Use entered email_to from the frontend
        # 2. Fall back to catalog inputs if needed
        recipients = email_service.get_recipients(
            email_to=request.email_to,
            inputs_map=catalog["inputs_map"],
        )

        if recipients:
            try:
                email_service.send_quote_email(
                    recipients=recipients,
                    quote_number=request.quote_number,
                    company=request.company,
                    sku=request.sku,
                    destination_zip=request.destination_zip,
                    origin_zip=request.origin_zip,
                    rc_product_number=sku_row["rc_product_number"],
                    shipment=shipment,
                    priced_result=priced,
                    customer_name=request.customer_name,
                    rep_name=request.rep_name,
                    project_name=request.project_name,
                )
            except Exception as exc:
                email_error = str(exc)

        return QuoteResponse(
            ok=True,
            company=request.company,
            sku=request.sku,
            rc_product_number=sku_row["rc_product_number"],
            destination_zip=request.destination_zip,
            origin_zip=request.origin_zip,
            quantity=request.quantity,
            shipment=shipment,
            tms=tms_result,
            pricing=priced,
            emailed_to=recipients,
            quote_number=request.quote_number,
            email_error=email_error,
        )

    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
            },
        )
