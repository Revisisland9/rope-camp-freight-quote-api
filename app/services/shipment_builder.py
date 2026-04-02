from typing import Any, Dict, List


def build_shipment(
    rc_master_rows: List[Dict[str, Any]],
    rc_product_number: str,
    quantity: int,
) -> Dict[str, Any]:
    matching_rows = [
        row for row in rc_master_rows
        if row["rc_product_number"] == rc_product_number and row.get("active", True)
    ]

    if not matching_rows:
        raise ValueError(f"No active RC_MASTER rows found for '{rc_product_number}'.")

    matching_rows.sort(key=lambda x: str(x.get("component", "")))

    items: List[Dict[str, Any]] = []
    total_weight = 0.0
    total_pieces = 0
    pieces_per_unit = 0

    for row in matching_rows:
        row_pieces = int(row["pieces"])
        pieces = row_pieces * quantity
        weight = float(row["weight"]) * quantity

        item = {
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

    return {
        "rc_product_number": rc_product_number,
        "quantity": quantity,
        "pieces_per_unit": pieces_per_unit,
        "total_weight": round(total_weight, 2),
        "total_pieces": total_pieces,
        "items": items,
    }
