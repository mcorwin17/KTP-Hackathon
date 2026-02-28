"""Pydantic models for SmartRoute records."""

from datetime import date, datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    EMAIL = "email"
    PORTAL = "portal"
    ATTACHMENT_OCR = "attachment_ocr"


class InspectionStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class RouteTeam(str, Enum):
    RELEASE_DESK = "RELEASE_DESK"
    FIELD_DISPATCH = "FIELD_DISPATCH"
    PERMITTING = "PERMITTING"
    ENGINEERING = "ENGINEERING"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    UNKNOWN = "UNKNOWN"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ContactRole(str, Enum):
    INSPECTOR = "inspector"
    REQUESTER = "requester"
    CONTRACTOR = "contractor"
    OWNER = "owner"


class Attachment(BaseModel):
    """Represents an email attachment."""
    filename: str = ""
    content_type: str = ""
    extracted_text: str = ""


class Sender(BaseModel):
    """Email sender information."""
    name: str = ""
    email: str = ""


class Source(BaseModel):
    """Source information for the communication."""
    source_type: SourceType = SourceType.EMAIL
    received_at: Optional[datetime] = None
    from_: Sender = Field(default_factory=Sender, alias="from")
    to: list[str] = Field(default_factory=list)
    subject: str = ""
    raw_text: str = ""
    clean_text: str = ""
    attachments: list[Attachment] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class Jurisdiction(BaseModel):
    """Jurisdiction information."""
    name: str = ""
    county: str = ""
    state: str = "SC"


class Permit(BaseModel):
    """Permit information."""
    permit_number: str = ""
    permit_type: str = ""
    permit_category: str = ""


class InspectionNote(BaseModel):
    """A note associated with an inspection."""
    date: str = ""
    text: str = ""


class Inspection(BaseModel):
    """Inspection information."""
    inspection_type: str = ""
    inspection_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: InspectionStatus = InspectionStatus.UNKNOWN
    description: str = ""
    notes: list[InspectionNote] = Field(default_factory=list)


class Release(BaseModel):
    """Release information."""
    release_date: Optional[date] = None
    release_type: str = ""
    structure_type: str = ""
    reason_for_release: str = ""


class Site(BaseModel):
    """Site/address information."""
    address_full: str = ""
    street_number: str = ""
    street_name: str = ""
    city: str = ""
    state: str = "SC"
    zip: str = ""
    subdivision: str = ""
    lot_unit: str = ""
    parcel_id: str = ""
    flood_zone: str = ""


class Contact(BaseModel):
    """Contact information."""
    role: ContactRole = ContactRole.INSPECTOR
    name: str = ""
    org: str = ""
    phone: str = ""
    email: str = ""


class Operational(BaseModel):
    """Operational routing and action information."""
    action_required: bool = False
    action_reason: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    route_to_team: RouteTeam = RouteTeam.UNKNOWN
    priority: Priority = Priority.NORMAL


class Quality(BaseModel):
    """Quality and confidence metrics."""
    confidence_overall: float = 0.0
    field_confidence: dict[str, float] = Field(default_factory=dict)
    missing_required_fields: list[str] = Field(default_factory=list)


class SmartrouteRecord(BaseModel):
    """Complete SmartRoute record for a parsed communication."""
    source: Source = Field(default_factory=Source)
    jurisdiction: Jurisdiction = Field(default_factory=Jurisdiction)
    permit: Permit = Field(default_factory=Permit)
    inspection: Inspection = Field(default_factory=Inspection)
    release: Release = Field(default_factory=Release)
    site: Site = Field(default_factory=Site)
    contacts: list[Contact] = Field(default_factory=list)
    operational: Operational = Field(default_factory=Operational)
    quality: Quality = Field(default_factory=Quality)

    def to_dict(self) -> dict:
        """Convert to dictionary with proper field aliasing."""
        return self.model_dump(by_alias=True)
