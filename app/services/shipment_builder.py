from typing import Any, Dict, List, Union


def build_shipment(
    rc_master_rows: List[Dict[str, Any]],
    rc_product_numbers: Union[str, List[str]],
    quantity: int = 1,
) -> Dict[str, Any]:
    """
    Build a shipment from one or more RC product numbers.

    Supports:
      - single rc_product_number as str
      - multiple rc_product_numbers as List[str] (up to 5)

    Notes:
      - quantity defaults to 1
      - when multiple RC product numbers are supplied, each is treated as quantity=1
      - duplicate RC product numbers are rejected
    """

    # Normalize input to a clean list
    if isinstance(rc_product_numbers, str):
        normalized_products = [rc_product_numbers.strip()]
        single_input = True
    else:
        normalized_products = [
            str(x).strip() for x in rc_product_numbers
            if str(x).strip()
        ]
        single_input = len(normalized_products) == 1

    if not normalized_products:
        raise ValueError("At least one RC product number is required.")

    if len(normalized_products) > 5:
        raise ValueError("A maximum of 5 RC product numbers is allowed.")

    # Enforce uniqueness
    seen = set()
    duplicates = []
    unique_products: List[str] = []
    for product in normalized_products:
        key = product.lower()
        if key in seen:
            duplicates.append(product)
        else:
            seen.add(key)
            unique_products.append(product)

    if duplicates:
        raise ValueError(
            f"Duplicate RC product numbers are not allowed: {', '.join(duplicates)}"
        )

    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    items: List[Dict[str, Any]] = []
    total_weight = 0.0
    total_pieces = 0
    pieces_per_unit = 0

    product_summaries: List[Dict[str, Any]] = []

    for rc_product_number in unique_products:
        matching_rows = [
            row for row in rc_master_rows
            if row["rc_product_number"] == rc_product_number and row.get("active", True)
        ]

        if not matching_rows:
            raise ValueError(
                f"No active RC_MASTER rows found for '{rc_product_number}'."
            )

        matching_rows.sort(key=lambda x: str(x.get("component", "")))

        product_total_weight = 0.0
        product_total_pieces = 0
        product_pieces_per_unit = 0

        # Each unique SKU / RC product is treated as quantity=1 for the new workflow.
        # For backward compatibility, if only one product is supplied, we still honor `quantity`.
        effective_quantity = quantity if single_input else 1

        for row in matching_rows:
            row_pieces = int(row["pieces"])
            pieces = row_pieces * effective_quantity
            weight = float(row["weight"]) * effective_quantity

            item = {
                "rc_product_number": rc_product_number,
                "component": row["component"],
                "pieces": pieces,
                "length": float(row["length"]),
                "width": float(row["width"]),
                "height": float(row["height"]),
                "weight": weight,
                "density": float(row["density"]),
                "freight_class": row["freight_class"],
                "overlength_tier": row["overlength_tier"],
            }

            items.append(item)

            total_weight += weight
            total_pieces += pieces
            pieces_per_unit += row_pieces

            product_total_weight += weight
            product_total_pieces += pieces
            product_pieces_per_unit += row_pieces

        product_summaries.append(
            {
                "rc_product_number": rc_product_number,
                "quantity": effective_quantity,
                "pieces_per_unit": product_pieces_per_unit,
                "total_weight": round(product_total_weight, 2),
                "total_pieces": product_total_pieces,
            }
        )

    result = {
        "rc_product_numbers": unique_products,
        "quantity": quantity if single_input else 1,
        "pieces_per_unit": pieces_per_unit,
        "total_weight": round(total_weight, 2),
        "total_pieces": total_pieces,
        "items": items,
        "products": product_summaries,
    }

    # Preserve the old singular field when only one product is present
    if len(unique_products) == 1:
        result["rc_product_number"] = unique_products[0]

    return result
