from typing import Any, Dict, List


COMPANY_TO_FIELD = {
    "GameTime": "gametime",
    "Park and Play Structures": "park_and_play_structures",
    "Superior Recreational Products": "superior_recreational_products",
    "Playcraft": "playcraft",
}


def _get_company_field(company: str) -> str:
    if company not in COMPANY_TO_FIELD:
        allowed = ", ".join(COMPANY_TO_FIELD.keys())
        raise ValueError(f"Unsupported company '{company}'. Allowed values: {allowed}")
    return COMPANY_TO_FIELD[company]


def _normalize_skus(skus: List[str]) -> List[str]:
    cleaned = [str(sku).strip() for sku in skus if str(sku).strip()]

    if not cleaned:
        raise ValueError("At least one SKU is required.")

    if len(cleaned) > 5:
        raise ValueError("A maximum of 5 SKUs is allowed.")

    seen = set()
    duplicates = []
    unique_skus: List[str] = []

    for sku in cleaned:
        key = sku.lower()
        if key in seen:
            duplicates.append(sku)
        else:
            seen.add(key)
            unique_skus.append(sku)

    if duplicates:
        raise ValueError(f"Duplicate SKUs are not allowed: {', '.join(duplicates)}")

    return unique_skus


def resolve_rc_product(
    sku_xref_rows: List[Dict[str, Any]],
    company: str,
    sku: str,
) -> Dict[str, Any]:
    company_field = _get_company_field(company)
    needle = sku.strip().lower()

    for row in sku_xref_rows:
        if not row.get("active", True):
            continue

        candidate = str(row.get(company_field, "")).strip().lower()
        if candidate == needle:
            return row

    raise ValueError(f"SKU '{sku}' was not found for company '{company}'.")


def resolve_rc_products(
    sku_xref_rows: List[Dict[str, Any]],
    company: str,
    skus: List[str],
) -> Dict[str, Any]:
    company_field = _get_company_field(company)
    normalized_skus = _normalize_skus(skus)

    resolved_rows: List[Dict[str, Any]] = []
    rc_product_numbers: List[str] = []

    for sku in normalized_skus:
        needle = sku.lower()
        matched_row = None

        for row in sku_xref_rows:
            if not row.get("active", True):
                continue

            candidate = str(row.get(company_field, "")).strip().lower()
            if candidate == needle:
                matched_row = row
                break

        if matched_row is None:
            raise ValueError(f"SKU '{sku}' was not found for company '{company}'.")

        rc_product_number = str(matched_row.get("rc_product_number", "")).strip()
        if not rc_product_number:
            raise ValueError(
                f"SKU '{sku}' for company '{company}' is missing an RC product number."
            )

        resolved_rows.append(
            {
                "sku": sku,
                "rc_product_number": rc_product_number,
                "row": matched_row,
            }
        )
        rc_product_numbers.append(rc_product_number)

    return {
        "company": company,
        "skus": normalized_skus,
        "rc_product_numbers": rc_product_numbers,
        "resolved_rows": resolved_rows,
    }
