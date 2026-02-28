"""Deterministic regex-based field extraction."""

import re
from datetime import datetime
from typing import Any, Optional
from dateutil import parser as date_parser


class RegexExtractor:
    """Extract fields from text using regex patterns and heuristics."""

    # Permit number patterns
    PERMIT_PATTERNS = [
        r"Permit\s*#\s*:?\s*([A-Z0-9-]+)",
        r"Permit\s+Number\s*:?\s*([A-Z0-9-]+)",
        r"Permit\s*:?\s*#?\s*([A-Z0-9-]{6,})",
        r"#\s*(\d{7,})",
        r"(?:permit|application)\s*(?:no|number|#)?\s*:?\s*([A-Z]?\d{6,})",
    ]

    # Date patterns
    DATE_PATTERNS = [
        # Full date with day name: Monday, December 22, 2025
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        # MM/DD/YYYY or MM-DD-YYYY
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        # Month DD, YYYY
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})",
        # YYYY-MM-DD
        r"(\d{4}-\d{2}-\d{2})",
    ]

    # Status patterns
    STATUS_PATTERNS = [
        (r"(?:inspection\s+)?status\s*:?\s*(pass(?:ed)?)", "pass"),
        (r"(?:inspection\s+)?status\s*:?\s*(fail(?:ed)?)", "fail"),
        (r"(?:inspection\s+)?status\s*:?\s*(partial)", "partial"),
        (r"\b(approved)\b", "pass"),
        (r"\b(passed)\b", "pass"),
        (r"\b(failed)\b", "fail"),
        (r"\b(rejected)\b", "fail"),
        (r"\bre-?inspection\s+required\b", "fail"),
        (r"\bcorrections?\s+(?:needed|required)\b", "fail"),
    ]

    # Phone patterns
    PHONE_PATTERNS = [
        r"(?:phone|tel|cell|mobile|fax)\s*:?\s*([\d\s\-\(\)\.]{10,})",
        r"\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b",
        r"\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})",
    ]

    # Email patterns
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Address patterns
    ADDRESS_PATTERNS = [
        r"Address\s*:?\s*(.+?)(?:\n|$)",
        r"Location\s*:?\s*(.+?)(?:\n|$)",
        r"Property\s*:?\s*(.+?)(?:\n|$)",
        r"Site\s*:?\s*(.+?)(?:\n|$)",
        r"(\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Boulevard|Blvd)\.?(?:\s*,?\s*[A-Za-z\s]+)?)",
    ]

    # Inspection type patterns
    INSPECTION_TYPE_PATTERNS = [
        r"(?:inspection\s+)?type\s*:?\s*([A-Za-z\s]+?)(?:\n|$)",
        r"((?:Electrical|Plumbing|Mechanical|Building|Fire|Final|Rough|Framing|Foundation|Footing|Slab|Roofing|Insulation|Drywall)\s*(?:Inspection)?)",
    ]

    # Release type patterns
    RELEASE_TYPE_PATTERNS = [
        r"Release\s+Type\s*:?\s*(.+?)(?:\n|$)",
        r"((?:Electrical|Plumbing|Mechanical|Building|Utility|Power|Gas|Water)\s+(?:Power\s+)?Release)",
    ]

    def extract(self, clean_text: str, attachment_text: Optional[str] = None) -> dict:
        """
        Extract fields from cleaned text using regex patterns.

        Args:
            clean_text: Pre-cleaned text from email/portal
            attachment_text: Optional text extracted from attachments

        Returns:
            Dictionary with extracted fields and confidence scores
        """
        combined_text = clean_text
        if attachment_text:
            combined_text += "\n\n" + attachment_text

        result = {
            "permit": {},
            "inspection": {},
            "release": {},
            "site": {},
            "contacts": [],
            "field_confidence": {},
        }

        # Extract permit number
        permit_num, conf = self._extract_permit_number(combined_text)
        if permit_num:
            result["permit"]["permit_number"] = permit_num
            result["field_confidence"]["permit.permit_number"] = conf

        # Extract dates
        dates = self._extract_dates(combined_text)
        if dates:
            # Try to categorize dates based on context
            result["_extracted_dates"] = dates
            result["field_confidence"]["dates"] = 0.7

        # Extract status
        status, conf = self._extract_status(combined_text)
        if status:
            result["inspection"]["status"] = status
            result["field_confidence"]["inspection.status"] = conf

        # Extract address
        address, conf = self._extract_address(combined_text)
        if address:
            result["site"]["address_full"] = address
            result["field_confidence"]["site.address_full"] = conf

        # Extract contacts (emails and phones)
        contacts = self._extract_contacts(combined_text)
        if contacts:
            result["contacts"] = contacts
            result["field_confidence"]["contacts"] = 0.6

        # Extract inspection type
        insp_type, conf = self._extract_inspection_type(combined_text)
        if insp_type:
            result["inspection"]["inspection_type"] = insp_type
            result["field_confidence"]["inspection.inspection_type"] = conf

        # Extract release type
        release_type, conf = self._extract_release_type(combined_text)
        if release_type:
            result["release"]["release_type"] = release_type
            result["field_confidence"]["release.release_type"] = conf

        return result

    def _extract_permit_number(self, text: str) -> tuple[Optional[str], float]:
        """Extract permit number from text."""
        for pattern in self.PERMIT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                permit_num = match.group(1).strip()
                # Higher confidence for explicit labels
                conf = 0.9 if "permit" in pattern.lower() else 0.7
                return permit_num, conf
        return None, 0.0

    def _extract_dates(self, text: str) -> list[dict]:
        """Extract and parse dates from text."""
        dates = []
        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    date_str = match.group(1) if match.lastindex else match.group(0)
                    parsed = date_parser.parse(date_str)
                    dates.append({
                        "original": date_str,
                        "parsed": parsed.strftime("%Y-%m-%d"),
                        "position": match.start(),
                    })
                except (ValueError, TypeError):
                    continue

        # Sort by position in text and deduplicate
        dates.sort(key=lambda x: x["position"])
        seen = set()
        unique_dates = []
        for d in dates:
            if d["parsed"] not in seen:
                seen.add(d["parsed"])
                unique_dates.append(d)

        return unique_dates

    def _extract_status(self, text: str) -> tuple[Optional[str], float]:
        """Extract inspection status from text."""
        text_lower = text.lower()

        for pattern, status in self.STATUS_PATTERNS:
            if re.search(pattern, text_lower):
                # Higher confidence for explicit status labels
                conf = 0.9 if "status" in pattern else 0.7
                return status, conf

        return None, 0.0

    def _extract_address(self, text: str) -> tuple[Optional[str], float]:
        """Extract address from text."""
        for pattern in self.ADDRESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                address = match.group(1).strip()
                # Clean up the address
                address = re.sub(r"\s+", " ", address)
                conf = 0.8 if any(label in pattern.lower() for label in ["address", "location", "property"]) else 0.6
                return address, conf
        return None, 0.0

    def _extract_contacts(self, text: str) -> list[dict]:
        """Extract contact information (emails and phones)."""
        contacts = []

        # Extract emails
        emails = re.findall(self.EMAIL_PATTERN, text)
        for email in set(emails):
            contacts.append({
                "email": email,
                "role": "inspector" if any(kw in email.lower() for kw in ["inspector", "county", "gov", "city"]) else "unknown"
            })

        # Extract phones
        for pattern in self.PHONE_PATTERNS:
            for match in re.finditer(pattern, text):
                phone = match.group(1) if match.lastindex else match.group(0)
                # Normalize phone
                phone_digits = re.sub(r"\D", "", phone)
                if len(phone_digits) >= 10:
                    contacts.append({
                        "phone": phone_digits,
                        "role": "unknown"
                    })

        return contacts

    def _extract_inspection_type(self, text: str) -> tuple[Optional[str], float]:
        """Extract inspection type from text."""
        for pattern in self.INSPECTION_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                insp_type = match.group(1).strip()
                return insp_type, 0.8
        return None, 0.0

    def _extract_release_type(self, text: str) -> tuple[Optional[str], float]:
        """Extract release type from text."""
        for pattern in self.RELEASE_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                release_type = match.group(1).strip()
                return release_type, 0.8
        return None, 0.0
