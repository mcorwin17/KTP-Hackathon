"""Routing logic for determining action requirements and team assignment."""

import re
from typing import Optional

from .models import RouteTeam, Priority, Operational, SmartrouteRecord


# Keywords that indicate action is required
ACTION_REQUIRED_KEYWORDS = [
    "correction",
    "corrections",
    "reinspect",
    "re-inspect",
    "reinspection",
    "re-inspection",
    "required",
    "missing",
    "failed",
    "fail",
    "rejected",
    "violation",
    "deficiency",
    "deficiencies",
    "incomplete",
    "not approved",
    "denied",
    "urgent",
    "immediately",
    "asap",
]

# Keywords for release desk routing
RELEASE_KEYWORDS = [
    "electrical power release",
    "utility release",
    "power release",
    "gas release",
    "water release",
    "approved for release",
    "release approved",
    "release granted",
    "certificate of occupancy",
    "co release",
    "final release",
]

# Keywords for field dispatch
FIELD_DISPATCH_KEYWORDS = [
    "reinspection",
    "re-inspection",
    "site visit",
    "field inspection",
    "on-site",
    "physical inspection",
    "correction needed",
    "correction required",
]

# Keywords for engineering
ENGINEERING_KEYWORDS = [
    "structural",
    "load calculation",
    "engineering review",
    "structural review",
    "foundation issue",
    "design review",
    "plan review",
    "code analysis",
]

# Keywords for permitting
PERMITTING_KEYWORDS = [
    "permit application",
    "permit renewal",
    "permit extension",
    "permit modification",
    "permit status",
    "application status",
    "permit fee",
    "permit hold",
]

# Keywords for customer service
CUSTOMER_SERVICE_KEYWORDS = [
    "question",
    "inquiry",
    "information request",
    "status check",
    "general inquiry",
    "contact us",
    "help",
    "assistance",
]


def _text_contains_any(text: str, keywords: list[str]) -> bool:
    """Check if text contains any of the keywords (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _determine_priority(
    status: Optional[str],
    text: str,
    action_required: bool
) -> Priority:
    """Determine priority level based on status and content."""
    text_lower = text.lower()

    # High priority indicators
    high_priority_keywords = [
        "urgent",
        "immediately",
        "asap",
        "critical",
        "emergency",
        "time sensitive",
        "deadline",
    ]

    if any(kw in text_lower for kw in high_priority_keywords):
        return Priority.HIGH

    # Failed inspections with corrections are high priority
    if status == "fail" and _text_contains_any(text, ["correction", "required"]):
        return Priority.HIGH

    # Action required items are at least normal priority
    if action_required:
        return Priority.NORMAL

    # Passed inspections with no action are low priority
    if status == "pass":
        return Priority.LOW

    return Priority.NORMAL


def _determine_team(
    status: Optional[str],
    text: str,
    release_type: Optional[str] = None
) -> RouteTeam:
    """Determine which team should handle this item."""
    # Check for release desk routing first
    if release_type and "release" in release_type.lower():
        return RouteTeam.RELEASE_DESK

    if _text_contains_any(text, RELEASE_KEYWORDS):
        return RouteTeam.RELEASE_DESK

    # Check for field dispatch (reinspection, corrections)
    if _text_contains_any(text, FIELD_DISPATCH_KEYWORDS):
        return RouteTeam.FIELD_DISPATCH

    if status == "fail":
        return RouteTeam.FIELD_DISPATCH

    # Check for engineering
    if _text_contains_any(text, ENGINEERING_KEYWORDS):
        return RouteTeam.ENGINEERING

    # Check for permitting
    if _text_contains_any(text, PERMITTING_KEYWORDS):
        return RouteTeam.PERMITTING

    # Check for customer service
    if _text_contains_any(text, CUSTOMER_SERVICE_KEYWORDS):
        return RouteTeam.CUSTOMER_SERVICE

    # Default to permitting for informational items
    if status == "pass":
        return RouteTeam.PERMITTING

    return RouteTeam.UNKNOWN


def _generate_action_reason(
    status: Optional[str],
    text: str,
    route_team: RouteTeam
) -> str:
    """Generate explanation for why action is required."""
    reasons = []

    if status == "fail":
        reasons.append("Inspection failed")

    if _text_contains_any(text, ["correction", "corrections"]):
        reasons.append("Corrections required")

    if _text_contains_any(text, ["reinspection", "re-inspection"]):
        reasons.append("Re-inspection needed")

    if _text_contains_any(text, ["missing"]):
        reasons.append("Missing items identified")

    if _text_contains_any(text, ["violation"]):
        reasons.append("Code violation noted")

    if route_team == RouteTeam.RELEASE_DESK:
        reasons.append("Release workflow triggered")

    if not reasons:
        return "Review required"

    return "; ".join(reasons)


def _generate_recommended_actions(
    status: Optional[str],
    text: str,
    route_team: RouteTeam
) -> list[str]:
    """Generate list of recommended actions."""
    actions = []

    if status == "fail":
        actions.append("Review inspection report for specific failures")
        actions.append("Schedule re-inspection after corrections")

    if route_team == RouteTeam.RELEASE_DESK:
        actions.append("Process release documentation")
        actions.append("Update permit status")

    if route_team == RouteTeam.FIELD_DISPATCH:
        actions.append("Assign field inspector for follow-up")

    if route_team == RouteTeam.ENGINEERING:
        actions.append("Forward to engineering team for review")

    if _text_contains_any(text, ["correction", "corrections"]):
        actions.append("Notify contractor of required corrections")

    if not actions:
        actions.append("Review and file for records")

    return actions


def route(record: SmartrouteRecord) -> Operational:
    """
    Determine routing and action requirements for a record.

    Args:
        record: The parsed SmartRoute record

    Returns:
        Operational object with routing decisions
    """
    # Get relevant text for analysis
    text = record.source.clean_text or record.source.raw_text or ""

    # Get status
    status = record.inspection.status.value if record.inspection.status else None

    # Get release type
    release_type = record.release.release_type if record.release else None

    # Determine if action is required
    action_required = False

    # Failed inspection always requires action
    if status == "fail":
        action_required = True

    # Check for action keywords
    if _text_contains_any(text, ACTION_REQUIRED_KEYWORDS):
        action_required = True

    # Release items require action
    if release_type or _text_contains_any(text, RELEASE_KEYWORDS):
        action_required = True

    # Determine routing
    route_team = _determine_team(status, text, release_type)

    # Determine priority
    priority = _determine_priority(status, text, action_required)

    # Generate reason and recommendations
    action_reason = ""
    recommended_actions = []

    if action_required:
        action_reason = _generate_action_reason(status, text, route_team)
        recommended_actions = _generate_recommended_actions(status, text, route_team)

    return Operational(
        action_required=action_required,
        action_reason=action_reason,
        recommended_actions=recommended_actions,
        route_to_team=route_team,
        priority=priority,
    )


def route_from_dict(record_dict: dict) -> dict:
    """
    Determine routing from a dictionary record.

    Args:
        record_dict: Record as dictionary

    Returns:
        Operational fields as dictionary
    """
    # Get text
    text = ""
    if "source" in record_dict:
        text = record_dict["source"].get("clean_text", "") or record_dict["source"].get("raw_text", "")

    # Get status
    status = None
    if "inspection" in record_dict:
        status = record_dict["inspection"].get("status")

    # Get release type
    release_type = None
    if "release" in record_dict:
        release_type = record_dict["release"].get("release_type")

    # Determine if action is required
    action_required = False

    if status == "fail":
        action_required = True

    if _text_contains_any(text, ACTION_REQUIRED_KEYWORDS):
        action_required = True

    if release_type or _text_contains_any(text, RELEASE_KEYWORDS):
        action_required = True

    # Determine routing
    route_team = _determine_team(status, text, release_type)

    # Determine priority
    priority = _determine_priority(status, text, action_required)

    # Generate reason and recommendations
    action_reason = ""
    recommended_actions = []

    if action_required:
        action_reason = _generate_action_reason(status, text, route_team)
        recommended_actions = _generate_recommended_actions(status, text, route_team)

    return {
        "action_required": action_required,
        "action_reason": action_reason,
        "recommended_actions": recommended_actions,
        "route_to_team": route_team.value,
        "priority": priority.value,
    }
