from typing import Any, Dict, List


COMPANY_TO_FIELD = {
    "GameTime": "gametime",
    "Park and Play Structures": "park_and_play_structures",
    "Superior Recreational Products": "superior_recreational_products",
    "Playcraft": "playcraft",
}


def resolve_rc_product(
    sku_xref_rows: List[Dict[str, Any]],
    company: str,
    sku: str,
) -> Dict[str, Any]:
    if company not in COMPANY_TO_FIELD:
        allowed = ", ".join(COMPANY_TO_FIELD.keys())
        raise ValueError(f"Unsupported company '{company}'. Allowed values: {allowed}")

    company_field = COMPANY_TO_FIELD[company]
    needle = sku.strip().lower()

    for row in sku_xref_rows:
        if not row.get("active", True):
            continue

        candidate = str(row.get(company_field, "")).strip().lower()
        if candidate == needle:
            return row

    raise ValueError(f"SKU '{sku}' was not found for company '{company}'.")
