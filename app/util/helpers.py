import re
from typing import Any, Dict, List


def clean_header(header: str) -> str:
    return str(header).strip()


def require_value(mapping: Dict[str, Any], key: str) -> None:
    if key not in mapping:
        raise RuntimeError(f"Required INPUTS setting missing: '{key}'")


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in {"true", "t", "yes", "y", "1", "checked", "x"}


def parse_float(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    s = str(value).strip().replace(",", "").replace("$", "")
    if s.endswith("%"):
        s = s[:-1]
    return float(s)


def parse_currency(value: Any) -> float:
    return parse_float(value)


def parse_percentage(value: Any) -> float:
    s = str(value).strip()
    if s.endswith("%"):
        return parse_float(s) / 100.0
    raw = parse_float(s)
    return raw / 100.0 if raw > 1 else raw


def parse_email_list(value: Any) -> List[str]:
    if value is None:
        return []

    parts = [x.strip() for x in str(value).split(",")]
    emails = [x for x in parts if x]

    valid: List[str] = []
    for email in emails:
        if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            valid.append(email)
    return valid
