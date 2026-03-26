from pydantic import BaseModel, Field, field_validator


class QuoteRequest(BaseModel):
    company: str = Field(..., description="Brand/company column name from SKU_XREF, e.g. GameTime")
    sku: str = Field(..., description="Visible customer-facing SKU for the selected company")
    origin_zip: str = Field(..., min_length=3, max_length=10)
    destination_zip: str = Field(..., min_length=3, max_length=10)
    quantity: int = Field(default=1, ge=1)
    send_email: bool = Field(default=False)

    @field_validator("company", "sku", "origin_zip", "destination_zip")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()
