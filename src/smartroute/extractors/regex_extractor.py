"""Deterministic regex-based field extraction with OCR robustness."""

import re
from datetime import datetime
from typing import Any, Optional
from dateutil import parser as date_parser


# Patterns that indicate redacted/unclear content (OCR artifacts from blacked-out areas)
GARBAGE_PATTERNS = [
    r'^[^a-zA-Z0-9]*$',  # Only special characters
    r'^[█▓▒░■□▪▫]+',  # Block characters (redaction marks)
    r'^\*+$',  # Only asterisks
    r'^[_\-=]+$',  # Only underscores/dashes
    r'^[xX]{4,}$',  # Multiple x's (common redaction) - increased threshold
    r'^\[redacted\]$',
    r'^\[blocked\]$',
    r'^\[removed\]$',
]

# Minimum readable character ratio for valid text (lowered for OCR tolerance)
MIN_READABLE_RATIO = 0.5


def is_garbage_text(text: str) -> bool:
    """Check if text appears to be garbage/OCR artifacts from redacted content."""
    if not text or len(text.strip()) == 0:
        return True

    text = text.strip()

    # Check against garbage patterns
    for pattern in GARBAGE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    # Check readable character ratio (more lenient for OCR)
    readable_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in '.,/-#')
    if len(text) > 0 and readable_chars / len(text) < MIN_READABLE_RATIO:
        return True

    # Check for excessive repeated characters (OCR artifacts) - only non-digit, non-space
    if len(text) >= 5:
        for i in range(len(text) - 4):
            char = text[i]
            if char == text[i+1] == text[i+2] == text[i+3] == text[i+4]:
                if not char.isdigit() and not char.isspace():
                    return True

    return False


def normalize_ocr_text(text: str) -> str:
    """
    Normalize common OCR errors in text.

    Fixes common character confusions while preserving the original structure.
    """
    if not text:
        return text

    # Fix common OCR character confusions in specific contexts
    normalized = text

    # Fix date-like patterns: O -> 0 when surrounded by digits or in date context
    # e.g., "O1/15/2O26" -> "01/15/2026"
    normalized = re.sub(r'(?<=\d)O(?=\d)', '0', normalized)
    normalized = re.sub(r'(?<=/)O(?=\d)', '0', normalized)
    normalized = re.sub(r'(?<=\d)O(?=/)', '0', normalized)
    normalized = re.sub(r'(?<=--)O(?=\d)', '0', normalized)
    normalized = re.sub(r'\bO(\d)', r'0\1', normalized)  # O1 -> 01 at word boundary

    # Fix year patterns: 2O26 -> 2026
    normalized = re.sub(r'(20)O(\d)', r'\g<1>0\2', normalized)
    normalized = re.sub(r'(19)O(\d)', r'\g<1>0\2', normalized)

    # Fix l/1/I confusions in permit numbers (when followed/preceded by digits)
    # BP-2026-OOl42 -> BP-2026-00142
    normalized = re.sub(r'(?<=[A-Z]-\d{4}-)OO([lI1])(\d+)', r'00\1\2', normalized)
    normalized = re.sub(r'(?<=\d)[lI](?=\d)', '1', normalized)

    # Normalize various dash types to standard hyphen
    normalized = re.sub(r'[–—−]', '-', normalized)

    # Fix spacing around slashes and dashes in dates
    normalized = re.sub(r'\s*/\s*', '/', normalized)
    normalized = re.sub(r'(\d)\s+-\s+(\d)', r'\1-\2', normalized)

    return normalized


def preprocess_ocr_date(date_str: str) -> str:
    """Preprocess a potential date string to fix OCR errors."""
    if not date_str:
        return date_str

    result = date_str.strip()

    # Fix O/0 confusions
    result = re.sub(r'\bO(?=\d)', '0', result)
    result = re.sub(r'(?<=\d)O(?=\d)', '0', result)
    result = re.sub(r'(?<=\d)O\b', '0', result)
    result = re.sub(r'(?<=/)O', '0', result)
    result = re.sub(r'O(?=/)', '0', result)

    # Fix year: 2O26 -> 2026
    result = re.sub(r'2O(\d\d)\b', r'20\1', result)

    # Fix l/1 confusions
    result = re.sub(r'(?<=\d)l(?=\d)', '1', result)
    result = re.sub(r'(?<=/)[lI](?=\d)', '1', result)

    # Remove extra spaces
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def clean_ocr_artifacts(text: str) -> str:
    """Remove common OCR artifacts from redacted/blacked-out areas."""
    if not text:
        return text

    # First normalize OCR text
    text = normalize_ocr_text(text)

    # Remove lines that are mostly non-readable characters
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        if not is_garbage_text(line):
            clean_lines.append(line)

    return '\n'.join(clean_lines)


class RegexExtractor:
    """Extract fields from text using regex patterns and heuristics.

    Optimized for OCR text with common recognition errors.
    Only extracts clearly visible text - skips redacted or unclear content.
    """

    # Permit number patterns - ordered by specificity
    PERMIT_PATTERNS = [
        # Structured format first: BP-2026-00142, CP-2026-00201, IP-2026-00050
        r"(?:Permit\s*(?:#|Number|No\.?)\s*:?\s*)([A-Z]{1,3}-?\d{4}-?\d{3,6})",
        r"(?:Permit\s*:?\s*#?\s*)([A-Z]{1,3}-?\d{4}-?\d{3,6})",
        # Standalone structured format (no label needed)
        r"\b([A-Z]{2}-\d{4}-\d{4,6})\b",
        r"\b([A-Z]{1,3}-20\d{2}-\d{3,6})\b",
        # Labeled with alphanumeric-only capture (no spaces allowed in permit)
        r"Permit\s*#\s*:?\s*([A-Z0-9][A-Z0-9\-]{4,20})",
        r"Permit\s+(?:Number|No\.?)\s*:?\s*([A-Z0-9][A-Z0-9\-]{4,20})",
        # Standalone number references
        r"#\s*(\d{5,})",
        r"(?:permit|application)\s*(?:no|number|#)?\s*:?\s*([A-Z]?\d{5,})",
    ]

    # Date patterns - expanded for OCR variations
    DATE_PATTERNS = [
        # Full date with day name: Monday, December 22, 2025
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[,\s]+"
        r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"[\s\.]+\d{1,2}[,\s]+\d{4})",

        # MM/DD/YYYY or MM-DD-YYYY with flexible spacing (OCR often adds spaces)
        r"(\d{1,2}\s*[/\-]\s*\d{1,2}\s*[/\-]\s*\d{2,4})",

        # Month DD, YYYY with abbreviations
        r"((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"[\s\.]+\d{1,2}[,\s]+\d{4})",

        # DD-Mon-YYYY: 15-Jan-2026
        r"(\d{1,2}[\-\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\-\s]+\d{4})",

        # YYYY-MM-DD (ISO)
        r"(\d{4}\s*-\s*\d{1,2}\s*-\s*\d{1,2})",

        # Written out: "January 15, 2026" or "January 15 2026"
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2}[,\s]+\d{4})",

        # Date with label context
        r"[Dd]ate[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
        r"[Dd]ate[:\s]+(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
    ]

    # Status patterns - expanded
    STATUS_PATTERNS = [
        # Explicit status labels
        (r"(?:inspection\s+)?status\s*:?\s*(pass(?:ed)?)", "pass"),
        (r"(?:inspection\s+)?status\s*:?\s*(fail(?:ed)?)", "fail"),
        (r"(?:inspection\s+)?status\s*:?\s*(partial)", "partial"),
        (r"[Rr]esult\s*:?\s*(pass(?:ed)?)", "pass"),
        (r"[Rr]esult\s*:?\s*(fail(?:ed)?)", "fail"),
        (r"[Rr]esult\s*:?\s*(partial)", "partial"),
        # Status values
        (r"\b(approved)\b", "pass"),
        (r"\b(passed)\b", "pass"),
        (r"\b(pass)\b", "pass"),
        (r"\b(failed)\b", "fail"),
        (r"\b(fail)\b", "fail"),
        (r"\b(rejected)\b", "fail"),
        (r"\bre-?inspection\s+required\b", "fail"),
        (r"\bcorrections?\s+(?:needed|required)\b", "fail"),
        (r"\b(conditional(?:ly)?(?:\s+approved)?)\b", "partial"),
        (r"\b(pending)\b", "partial"),
    ]

    # Phone patterns
    PHONE_PATTERNS = [
        r"(?:phone|tel|cell|mobile|fax)\s*:?\s*([\d\s\-\(\)\.]{10,})",
        r"\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b",
        r"\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})",
    ]

    # Email patterns
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Address patterns - more flexible for OCR
    ADDRESS_PATTERNS = [
        # Labeled addresses
        r"(?:Site\s+)?[Aa]ddress\s*:?\s*(.+?)(?:\n|$)",
        r"[Ll]ocation\s*:?\s*(.+?)(?:\n|$)",
        r"[Pp]roperty\s*:?\s*(.+?)(?:\n|$)",
        r"[Ss]ite\s*:?\s*(.+?)(?:\n|$)",
        # Street address patterns with common street types
        r"(\d+\s+[A-Za-z0-9\s\.]+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Drive|Dr\.?|"
        r"Lane|Ln\.?|Way|Court|Ct\.?|Circle|Cir\.?|Boulevard|Blvd\.?|"
        r"Parkway|Pkwy\.?|Place|Pl\.?|Highway|Hwy\.?|Trail|Trl\.?)\.?"
        r"(?:[,\s]+[A-Za-z\s]+)?(?:[,\s]+\d{5}(?:-\d{4})?)?)",
        # Simpler pattern: number + words + optional city/zip
        r"(\d{1,5}\s+[A-Za-z][A-Za-z0-9\s\.]{5,40}(?:,\s*[A-Za-z\s]+)?(?:,?\s*\d{5})?)",
    ]

    # Structure type patterns - order matters, most specific first
    STRUCTURE_TYPE_PATTERNS = [
        # Explicit "Structure Type:" label
        r"(?:Structure|Building|Property)\s+[Tt]ype\s*:?\s*([A-Za-z\-]+)",
        # Just "Type:" but only when followed by structure type values (not inspection types)
        r"(?<![Ii]nspection\s)[Tt]ype\s*:?\s*(Residential|Commercial|Industrial|Mixed[\-\s]?Use)",
    ]

    # Structure type abbreviation mappings
    STRUCTURE_TYPE_ABBREVS = {
        "res": "Residential",
        "resi": "Residential",
        "resid": "Residential",
        "comm": "Commercial",
        "com": "Commercial",
        "ind": "Industrial",
        "indus": "Industrial",
        "mix": "Mixed-Use",
        "mixed": "Mixed-Use",
    }

    # Inspection type patterns
    INSPECTION_TYPE_PATTERNS = [
        r"(?:[Ii]nspection\s+)?[Tt]ype\s*:?\s*([A-Za-z\s]+?)(?:\n|$)",
        r"((?:Electrical|Plumbing|Mechanical|Building|Fire|Final|Rough|"
        r"Framing|Foundation|Footing|Slab|Roofing|Insulation|Drywall|HVAC|"
        r"Gas|Water|Sewer|Grading|Demolition|Certificate\s+of\s+Occupancy|CO)\s*"
        r"(?:Inspection)?)",
    ]

    # Release type patterns
    RELEASE_TYPE_PATTERNS = [
        r"[Rr]elease\s+[Tt]ype\s*:?\s*(.+?)(?:\n|$)",
        r"((?:Electrical|Plumbing|Mechanical|Building|Utility|Power|Gas|Water|Meter)\s+"
        r"(?:Power\s+)?[Rr]elease)",
    ]

    # Inspector name patterns
    INSPECTOR_PATTERNS = [
        r"[Ii]nspector\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"[Ii]nspected\s+[Bb]y\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
        r"[Ii]nspector\s+[Nn]ame\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)",
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

        # Apply OCR normalization
        combined_text = normalize_ocr_text(combined_text)

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
            result["_extracted_dates"] = dates
            # Assign dates based on context
            self._assign_dates(result, dates, combined_text)
            result["field_confidence"]["dates"] = 0.75

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

        # Extract structure type
        struct_type, conf = self._extract_structure_type(combined_text)
        if struct_type:
            result["site"]["structure_type"] = struct_type
            result["release"]["structure_type"] = struct_type
            result["field_confidence"]["site.structure_type"] = conf
            result["field_confidence"]["release.structure_type"] = conf

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

        # Extract inspector name
        inspector, conf = self._extract_inspector(combined_text)
        if inspector:
            # Add to contacts if not already present
            inspector_contact = {"name": inspector, "role": "inspector"}
            if not any(c.get("name") == inspector for c in result["contacts"]):
                result["contacts"].append(inspector_contact)

        return result

    def _extract_permit_number(self, text: str) -> tuple[Optional[str], float]:
        """Extract permit number from text. Only returns clearly readable values."""
        for pattern in self.PERMIT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                permit_num = match.group(1).strip()
                # Normalize: remove extra spaces, fix O/0
                permit_num = re.sub(r'\s+', '', permit_num)
                permit_num = re.sub(r'O(?=\d)', '0', permit_num)
                permit_num = re.sub(r'(?<=\d)O', '0', permit_num)

                # Skip if it looks like garbage/redacted content
                if is_garbage_text(permit_num):
                    continue
                # Permit numbers should be mostly alphanumeric
                alnum_ratio = sum(1 for c in permit_num if c.isalnum() or c == '-') / max(len(permit_num), 1)
                if alnum_ratio < 0.6:
                    continue
                # Should have at least some digits
                if not any(c.isdigit() for c in permit_num):
                    continue
                # Higher confidence for explicit labels
                conf = 0.9 if "permit" in pattern.lower() else 0.75
                return permit_num.upper(), conf
        return None, 0.0

    def _extract_dates(self, text: str) -> list[dict]:
        """Extract and parse dates from text with OCR error tolerance."""
        dates = []
        for pattern in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    date_str = match.group(1) if match.lastindex else match.group(0)
                    # Preprocess for OCR errors
                    date_str = preprocess_ocr_date(date_str)
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    # Sanity check: year should be reasonable (1990-2100)
                    if parsed.year < 1990 or parsed.year > 2100:
                        continue
                    dates.append({
                        "original": date_str,
                        "parsed": parsed.strftime("%Y-%m-%d"),
                        "position": match.start(),
                    })
                except (ValueError, TypeError, OverflowError):
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

    def _assign_dates(self, result: dict, dates: list[dict], text: str) -> None:
        """Assign extracted dates to appropriate fields based on context."""
        if not dates:
            return

        text_lower = text.lower()

        for date_info in dates:
            pos = date_info["position"]
            parsed = date_info["parsed"]

            # Look at context around the date (80 chars before)
            context_start = max(0, pos - 80)
            context = text_lower[context_start:pos]

            if any(kw in context for kw in ["inspection", "inspected", "insp ", "insp."]):
                result["inspection"]["inspection_date"] = parsed
            elif any(kw in context for kw in ["schedule", "planned", "upcoming"]):
                result["inspection"]["scheduled_date"] = parsed
            elif any(kw in context for kw in ["release", "approved on", "cleared on"]):
                result["release"]["release_date"] = parsed
            elif any(kw in context for kw in ["date", "completed", "conducted", " on ", "sent"]):
                # Generic "date" label — likely inspection date
                if not result["inspection"].get("inspection_date"):
                    result["inspection"]["inspection_date"] = parsed
            elif not result["inspection"].get("inspection_date"):
                # Default first unassigned date to inspection date
                result["inspection"]["inspection_date"] = parsed

    def _extract_status(self, text: str) -> tuple[Optional[str], float]:
        """Extract inspection status from text."""
        # First check for explicit labels (highest confidence)
        label_patterns = [
            (r"(?:inspection\s+)?(?:status|result|outcome)\s*:?\s*(?:is\s+)?(pass(?:ed)?|approv(?:ed|al)|ok|complete[d]?)", "pass", 0.95),
            (r"(?:inspection\s+)?(?:status|result|outcome)\s*:?\s*(?:is\s+)?(fail(?:ed)?|reject(?:ed)?|denied|not\s+approv(?:ed|al))", "fail", 0.95),
            (r"(?:inspection\s+)?(?:status|result|outcome)\s*:?\s*(?:is\s+)?(partial(?:ly)?|conditional(?:ly)?)", "partial", 0.95),
            (r"(?:inspection\s+)?(?:status|result|outcome)\s*:?\s*(?:is\s+)?(pending|scheduled|under\s+review|in\s+review)", "unknown", 0.85),
        ]
        for pattern, status, conf in label_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return status, conf

        # Then check for standalone keywords
        for pattern, status in self.STATUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                conf = 0.85 if "status" in pattern or "result" in pattern.lower() else 0.75
                return status, conf

        return None, 0.0

    def _extract_address(self, text: str) -> tuple[Optional[str], float]:
        """Extract address from text. Only returns clearly readable values."""
        for pattern in self.ADDRESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = match.group(1).strip()
                # Clean up the address
                address = re.sub(r"\s+", " ", address)
                address = re.sub(r"[,\s]+$", "", address)
                # Skip if it looks like garbage/redacted content
                if is_garbage_text(address):
                    continue
                # Address should have reasonable length
                if len(address) < 5:
                    continue
                # Should contain at least one digit (street number)
                if not any(c.isdigit() for c in address):
                    continue
                conf = 0.85 if any(label in pattern.lower() for label in ["address", "location", "property", "site"]) else 0.65
                return address, conf
        return None, 0.0

    def _extract_structure_type(self, text: str) -> tuple[Optional[str], float]:
        """Extract structure/building type from text."""
        # First try explicit patterns
        for pattern in self.STRUCTURE_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                struct_type = match.group(1).strip()
                # Remove trailing punctuation
                struct_type = re.sub(r'[.,;:]+$', '', struct_type).strip()
                # Check if it's an abbreviation
                struct_lower = struct_type.lower()
                if struct_lower in self.STRUCTURE_TYPE_ABBREVS:
                    return self.STRUCTURE_TYPE_ABBREVS[struct_lower], 0.85
                # Normalize known values
                if struct_lower in ["residential", "res"]:
                    return "Residential", 0.9
                elif struct_lower in ["commercial", "comm", "com"]:
                    return "Commercial", 0.9
                elif struct_lower in ["industrial", "ind"]:
                    return "Industrial", 0.9
                elif "mixed" in struct_lower or struct_lower == "mix":
                    return "Mixed-Use", 0.9
                # Return as-is if not recognized abbreviation
                return struct_type.title(), 0.8

        # Look for standalone structure type keywords with context
        # "type: res" or "type:res" patterns (common in mobile/short messages)
        abbrev_pattern = r"[Tt]ype\s*:?\s*(res|comm?|ind|mix(?:ed)?)\b"
        match = re.search(abbrev_pattern, text, re.IGNORECASE)
        if match:
            abbrev = match.group(1).lower()
            if abbrev in self.STRUCTURE_TYPE_ABBREVS:
                return self.STRUCTURE_TYPE_ABBREVS[abbrev], 0.8
            # Handle partial matches
            if abbrev.startswith("res"):
                return "Residential", 0.8
            elif abbrev.startswith("com"):
                return "Commercial", 0.8
            elif abbrev.startswith("ind"):
                return "Industrial", 0.8
            elif abbrev.startswith("mix"):
                return "Mixed-Use", 0.8

        # Last resort: look for standalone full structure type words
        standalone_pattern = r"\b(Residential|Commercial|Industrial|Mixed[\-\s]?Use)\b"
        match = re.search(standalone_pattern, text, re.IGNORECASE)
        if match:
            struct_type = match.group(1).strip()
            if "mixed" in struct_type.lower():
                return "Mixed-Use", 0.7
            return struct_type.title(), 0.7

        return None, 0.0

    def _extract_contacts(self, text: str) -> list[dict]:
        """Extract contact information (emails and phones)."""
        contacts = []

        # Extract emails
        emails = re.findall(self.EMAIL_PATTERN, text)
        for email in set(emails):
            role = "unknown"
            email_lower = email.lower()
            if any(kw in email_lower for kw in ["inspector", "inspect"]):
                role = "inspector"
            elif any(kw in email_lower for kw in ["county", "gov", "city", "state"]):
                role = "government"
            contacts.append({"email": email, "role": role})

        # Extract phones
        for pattern in self.PHONE_PATTERNS:
            for match in re.finditer(pattern, text):
                phone = match.group(1) if match.lastindex else match.group(0)
                # Normalize phone
                phone_digits = re.sub(r"\D", "", phone)
                if len(phone_digits) >= 10:
                    # Avoid duplicates
                    if not any(c.get("phone") == phone_digits for c in contacts):
                        contacts.append({"phone": phone_digits, "role": "unknown"})

        return contacts

    def _extract_inspection_type(self, text: str) -> tuple[Optional[str], float]:
        """Extract inspection type from text."""
        for pattern in self.INSPECTION_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                insp_type = match.group(1).strip()
                insp_type = re.sub(r"\s+", " ", insp_type).title()
                return insp_type, 0.8
        return None, 0.0

    def _extract_release_type(self, text: str) -> tuple[Optional[str], float]:
        """Extract release type from text."""
        for pattern in self.RELEASE_TYPE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                release_type = match.group(1).strip()
                release_type = release_type.title()
                return release_type, 0.8
        return None, 0.0

    def _extract_inspector(self, text: str) -> tuple[Optional[str], float]:
        """Extract inspector name from text."""
        # Extended patterns — handle all-caps, varied labels, signatures
        patterns = [
            r"[Ii]nspector\s*:?\s*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
            r"[Ii]nspected\s+[Bb]y\s*:?\s*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
            r"[Ii]nspector\s+[Nn]ame\s*:?\s*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
            r"[Ee]xaminer\s*:?\s*([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
            # All-caps: INSPECTOR: JOHN SMITH
            r"INSPECTOR\s*:?\s*([A-Z][A-Z]+\s+[A-Z][A-Z]+)",
            # "Inspector John Smith" without colon
            r"[Ii]nspector\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Title-case if all caps
                if name.isupper():
                    name = name.title()
                if not is_garbage_text(name) and len(name) >= 3:
                    return name, 0.85
        return None, 0.0
