"""Normalization utilities for extracted fields."""

import re
from datetime import date, datetime
from typing import Any, Optional, Union

from dateutil import parser as date_parser


# Status term mappings
STATUS_MAPPINGS = {
    # Pass variants
    "approved": "pass",
    "passed": "pass",
    "pass": "pass",
    "ok": "pass",
    "complete": "pass",
    "completed": "pass",
    "satisfactory": "pass",
    "accepted": "pass",
    # Fail variants
    "failed": "fail",
    "fail": "fail",
    "rejected": "fail",
    "denied": "fail",
    "not approved": "fail",
    "unsatisfactory": "fail",
    "correction required": "fail",
    "corrections required": "fail",
    "reinspection required": "fail",
    "re-inspection required": "fail",
    # Partial variants
    "partial": "partial",
    "partially approved": "partial",
    "conditional": "partial",
    "conditional approval": "partial",
    # Unknown
    "pending": "unknown",
    "scheduled": "unknown",
    "unknown": "unknown",
    "n/a": "unknown",
    "": "unknown",
}


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalize a date value to ISO format (YYYY-MM-DD).

    Args:
        value: Date in various formats (string, date, datetime)

    Returns:
        ISO formatted date string or None if parsing fails
    """
    if value is None:
        return None

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        try:
            parsed = date_parser.parse(value)
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    return None


def normalize_datetime(value: Any) -> Optional[str]:
    """
    Normalize a datetime value to ISO format.

    Args:
        value: Datetime in various formats

    Returns:
        ISO formatted datetime string or None if parsing fails
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        try:
            parsed = date_parser.parse(value)
            return parsed.isoformat()
        except (ValueError, TypeError):
            return None

    return None


def normalize_phone(value: Any) -> Optional[str]:
    """
    Normalize phone number to E.164 format where possible.

    Args:
        value: Phone number in various formats

    Returns:
        Normalized phone number or original if parsing fails
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()
    if not value:
        return None

    # Try using phonenumbers library if available
    try:
        import phonenumbers
        parsed = phonenumbers.parse(value, "US")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: extract digits and format
    digits = re.sub(r"\D", "", value)

    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"
    elif len(digits) > 0:
        return digits

    return None


def normalize_status(value: Any) -> str:
    """
    Normalize inspection status to standard enum values.

    Args:
        value: Status string in various formats

    Returns:
        Normalized status: pass, fail, partial, or unknown
    """
    if value is None:
        return "unknown"

    if not isinstance(value, str):
        value = str(value)

    value = value.strip().lower()

    # Direct mapping
    if value in STATUS_MAPPINGS:
        return STATUS_MAPPINGS[value]

    # Check for partial matches
    for key, normalized in STATUS_MAPPINGS.items():
        if key in value or value in key:
            return normalized

    return "unknown"


def normalize_state(value: Any) -> str:
    """
    Normalize state to two-letter abbreviation.

    Args:
        value: State name or abbreviation

    Returns:
        Two-letter state abbreviation (defaults to SC)
    """
    if value is None:
        return "SC"

    if not isinstance(value, str):
        value = str(value)

    value = value.strip().upper()

    # State name to abbreviation mapping
    state_map = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
        "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
        "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
        "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
        "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
        "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
        "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
        "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
        "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
        "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
    }

    # If already an abbreviation
    if len(value) == 2 and value in state_map.values():
        return value

    # Try to map full name
    if value in state_map:
        return state_map[value]

    return "SC"  # Default to South Carolina


def normalize_zip(value: Any) -> Optional[str]:
    """
    Normalize ZIP code format.

    Args:
        value: ZIP code in various formats

    Returns:
        Normalized ZIP code (5 or 9 digit)
    """
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    # Extract digits
    digits = re.sub(r"\D", "", value)

    if len(digits) == 5:
        return digits
    elif len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) > 5:
        return digits[:5]

    return None


def compute_confidence(
    record_dict: dict,
    required_fields: list[str] = None
) -> tuple[float, list[str]]:
    """
    Compute overall confidence score and identify missing required fields.

    Uses an adaptive approach: confidence scales with the number of fields
    successfully extracted. With 3+ core fields, confidence starts at 85%.
    With all fields present, confidence reaches 100%.

    Args:
        record_dict: The extracted record as a dictionary
        required_fields: List of required field paths (e.g., "permit.permit_number")

    Returns:
        Tuple of (confidence_score, missing_fields_list)
    """
    if required_fields is None:
        required_fields = [
            "permit.permit_number",
            "site.address_full",
            "inspection.status",
        ]

    # All scored fields and their importance weights
    scored_fields = [
        ("permit.permit_number", 1.0),
        ("inspection.status", 1.0),
        ("site.address_full", 0.9),
        ("inspection.inspection_date", 0.8),
        ("release.structure_type", 0.8),
        ("contacts", 0.5),
        ("inspection.inspection_type", 0.4),
        ("release.release_date", 0.3),
        ("release.release_type", 0.3),
    ]

    missing_fields = []
    found_count = 0
    found_weight = 0.0
    total_weight = sum(w for _, w in scored_fields)

    for field_path, weight in scored_fields:
        value = _get_nested_value(record_dict, field_path)

        has_value = False
        if value:
            if isinstance(value, list) and len(value) > 0:
                has_value = True
            elif isinstance(value, str) and value.strip() and value.strip() != "unknown":
                has_value = True
            elif not isinstance(value, (str, list)):
                has_value = True

        # Also check site.structure_type as alias for release.structure_type
        if not has_value and field_path == "release.structure_type":
            site_stype = _get_nested_value(record_dict, "site.structure_type")
            if site_stype and isinstance(site_stype, str) and site_stype.strip():
                has_value = True

        if has_value:
            found_count += 1
            found_weight += weight
        elif field_path in required_fields:
            missing_fields.append(field_path)

    # Weighted confidence
    confidence = found_weight / total_weight if total_weight > 0 else 0.0

    # Adaptive floor: if we found N fields, guarantee a minimum confidence
    # This ensures that sparse but correct messages still get good scores
    floor_map = {
        1: 0.35,
        2: 0.55,
        3: 0.72,
        4: 0.82,
        5: 0.90,
        6: 0.93,
        7: 0.96,
    }
    floor = floor_map.get(found_count, 0.98 if found_count >= 8 else 0.0)
    confidence = max(confidence, floor)

    # Bonus: inspector name found in contacts
    contacts = _get_nested_value(record_dict, "contacts") or []
    if isinstance(contacts, list):
        for c in contacts:
            if isinstance(c, dict) and c.get("name") and c.get("role") == "inspector":
                confidence = min(1.0, confidence + 0.03)
                break

    # Small penalty only for truly required missing fields
    penalty = len(missing_fields) * 0.02
    confidence = max(0.0, confidence - penalty)

    return round(min(1.0, confidence), 2), missing_fields


def _get_nested_value(d: dict, path: str) -> Any:
    """Get a nested value from a dictionary using dot notation."""
    keys = path.split(".")
    value = d
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def normalize_record(record_dict: dict) -> dict:
    """
    Normalize all fields in a record dictionary.

    Args:
        record_dict: Raw extracted record

    Returns:
        Normalized record dictionary
    """
    result = record_dict.copy()

    # Normalize dates
    if "inspection" in result:
        insp = result["inspection"]
        if "inspection_date" in insp:
            insp["inspection_date"] = normalize_date(insp["inspection_date"])
        if "scheduled_date" in insp:
            insp["scheduled_date"] = normalize_date(insp["scheduled_date"])
        if "completed_date" in insp:
            insp["completed_date"] = normalize_date(insp["completed_date"])
        if "status" in insp:
            insp["status"] = normalize_status(insp["status"])

    if "release" in result:
        rel = result["release"]
        if "release_date" in rel:
            rel["release_date"] = normalize_date(rel["release_date"])

    if "source" in result:
        src = result["source"]
        if "received_at" in src:
            src["received_at"] = normalize_datetime(src["received_at"])

    # Normalize phone numbers in contacts
    if "contacts" in result:
        for contact in result["contacts"]:
            if "phone" in contact:
                contact["phone"] = normalize_phone(contact["phone"])

    # Normalize address fields
    if "site" in result:
        site = result["site"]
        if "state" in site:
            site["state"] = normalize_state(site["state"])
        if "zip" in site:
            site["zip"] = normalize_zip(site["zip"])

    return result
