from typing import Any, Dict


def apply_pricing_logic(
    tms_result: Dict[str, Any],
    msrp: float,
    inputs_map: Dict[str, Any],
) -> Dict[str, Any]:
    parsed = inputs_map["_parsed"]

    uplift_percentage = float(parsed["uplift_percentage"])
    flat_min_enabled = bool(parsed["flat_min_enabled"])
    flat_min_value = float(parsed["flat_min_value"])
    min_pct_msrp = float(parsed["min_pct_msrp"])

    base_rate = float(tms_result["base_rate"])
    uplifted_rate = base_rate * (1 + uplift_percentage)
    msrp_floor = msrp * min_pct_msrp
    flat_floor = flat_min_value if flat_min_enabled else 0.0

    final_quote = max(uplifted_rate, msrp_floor, flat_floor)

    winner = "uplifted_rate"
    if final_quote == flat_floor and flat_floor >= uplifted_rate and flat_floor >= msrp_floor:
        winner = "flat_min"
    elif final_quote == msrp_floor and msrp_floor >= uplifted_rate and msrp_floor >= flat_floor:
        winner = "msrp_floor"

    return {
        "base_rate": round(base_rate, 2),
        "uplift_percentage": uplift_percentage,
        "uplifted_rate": round(uplifted_rate, 2),
        "flat_min_enabled": flat_min_enabled,
        "flat_min_value": round(flat_floor, 2),
        "msrp": round(msrp, 2),
        "min_pct_msrp": min_pct_msrp,
        "msrp_floor": round(msrp_floor, 2),
        "final_quote": round(final_quote, 2),
        "winning_rule": winner,
        "carrier": tms_result.get("carrier", ""),
        "service": tms_result.get("service", ""),
        "transit_days": tms_result.get("transit_days"),
    }
