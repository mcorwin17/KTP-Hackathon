"""Main pipeline for parsing messages into SmartRoute records."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import (
    SmartrouteRecord,
    Attachment,
    Source,
    SourceType,
    Sender,
    Jurisdiction,
    Permit,
    Inspection,
    InspectionStatus,
    Release,
    Site,
    Contact,
    ContactRole,
    Operational,
    Quality,
)
from .cleaning import clean_text
from .extractors.regex_extractor import RegexExtractor
from .extractors.llm_extractor import LLMExtractor, LLMClient, MockLLMClient
from .normalize import normalize_record, compute_confidence, normalize_status
from .routing import route, route_from_dict


def extract_fields(
    clean_text_content: str,
    attachment_text: Optional[str] = None,
    llm_client: Optional[LLMClient] = None,
) -> dict:
    """
    Extract fields from cleaned text using hybrid approach.

    Args:
        clean_text_content: Pre-cleaned text
        attachment_text: Optional text from attachments
        llm_client: Optional LLM client for enhanced extraction

    Returns:
        Dictionary of extracted fields
    """
    # Step 1: Deterministic extraction with regex
    regex_extractor = RegexExtractor()
    regex_results = regex_extractor.extract(clean_text_content, attachment_text)

    # Step 2: LLM extraction if client provided
    llm_results = {}
    if llm_client:
        llm_extractor = LLMExtractor(llm_client)
        # Pass regex results as hints
        hints = {
            k: v for k, v in regex_results.items()
            if k not in ["field_confidence", "_extracted_dates"] and v
        }
        llm_results = llm_extractor.extract(clean_text_content, attachment_text, hints)

    # Step 3: Merge results (regex takes precedence for high-confidence fields)
    merged = _merge_extraction_results(regex_results, llm_results)

    return merged


def _merge_extraction_results(regex_results: dict, llm_results: dict) -> dict:
    """
    Merge regex and LLM extraction results.

    Regex results take precedence for fields with confidence > 0.8.
    LLM results fill in gaps and low-confidence fields.
    """
    merged = {}
    field_confidence = regex_results.get("field_confidence", {})

    # Start with LLM results as base
    for key, value in llm_results.items():
        if key.startswith("_"):
            continue
        if value is not None:
            merged[key] = value

    # Override with high-confidence regex results
    for section in ["permit", "inspection", "release", "site"]:
        if section in regex_results:
            if section not in merged:
                merged[section] = {}
            for field, value in regex_results[section].items():
                conf_key = f"{section}.{field}"
                confidence = field_confidence.get(conf_key, 0.0)
                if value and confidence >= 0.7:
                    merged[section][field] = value
                elif value and conf_key not in merged.get(section, {}):
                    merged[section][field] = value

    # Handle contacts
    if "contacts" in regex_results and regex_results["contacts"]:
        merged["contacts"] = regex_results["contacts"]

    # Store confidence data
    merged["_field_confidence"] = field_confidence

    # Handle extracted dates
    if "_extracted_dates" in regex_results:
        merged["_extracted_dates"] = regex_results["_extracted_dates"]

    return merged


def _build_record_from_extracted(
    extracted: dict,
    raw_text: str,
    cleaned_text: str,
    attachments: list[Attachment],
    source_type: SourceType = SourceType.EMAIL,
) -> SmartrouteRecord:
    """Build a SmartrouteRecord from extracted data."""

    # Build source
    source = Source(
        source_type=source_type,
        received_at=datetime.now(),
        raw_text=raw_text,
        clean_text=cleaned_text,
        attachments=attachments,
    )

    # Handle from/to if extracted
    if "from_email" in extracted:
        source.from_ = Sender(email=extracted.get("from_email", ""))
    if "inspector_email" in extracted:
        source.from_ = Sender(
            name=extracted.get("inspector_name", ""),
            email=extracted.get("inspector_email", "")
        )

    # Build jurisdiction
    jurisdiction = Jurisdiction(
        name=extracted.get("jurisdiction_name", ""),
        county=extracted.get("county", ""),
        state=extracted.get("state", "SC"),
    )

    # Build permit
    permit_data = extracted.get("permit", {})
    permit = Permit(
        permit_number=permit_data.get("permit_number", "") or extracted.get("permit_number", ""),
        permit_type=permit_data.get("permit_type", "") or extracted.get("permit_type", ""),
        permit_category=permit_data.get("permit_category", ""),
    )

    # Build inspection
    insp_data = extracted.get("inspection", {})
    status_str = insp_data.get("status") or extracted.get("status", "unknown")
    status = normalize_status(status_str)

    inspection = Inspection(
        inspection_type=insp_data.get("inspection_type", "") or extracted.get("inspection_type", ""),
        status=InspectionStatus(status),
        description=insp_data.get("description", ""),
    )

    # Handle dates
    if insp_data.get("inspection_date"):
        try:
            from dateutil import parser as date_parser
            inspection.inspection_date = date_parser.parse(insp_data["inspection_date"]).date()
        except (ValueError, TypeError):
            pass

    if extracted.get("inspection_date"):
        try:
            from dateutil import parser as date_parser
            inspection.inspection_date = date_parser.parse(extracted["inspection_date"]).date()
        except (ValueError, TypeError):
            pass

    if extracted.get("scheduled_date"):
        try:
            from dateutil import parser as date_parser
            inspection.scheduled_date = date_parser.parse(extracted["scheduled_date"]).date()
        except (ValueError, TypeError):
            pass

    # Build release
    rel_data = extracted.get("release", {})
    release = Release(
        release_type=rel_data.get("release_type", "") or extracted.get("release_type", ""),
        structure_type=rel_data.get("structure_type", "") or extracted.get("structure_type", ""),
        reason_for_release=rel_data.get("reason_for_release", "") or extracted.get("reason_for_release", ""),
    )

    if rel_data.get("release_date") or extracted.get("release_date"):
        try:
            from dateutil import parser as date_parser
            date_str = rel_data.get("release_date") or extracted.get("release_date")
            release.release_date = date_parser.parse(date_str).date()
        except (ValueError, TypeError):
            pass

    # Build site
    site_data = extracted.get("site", {})
    site = Site(
        address_full=site_data.get("address_full", "") or extracted.get("address_full", ""),
        street_number=site_data.get("street_number", "") or extracted.get("street_number", ""),
        street_name=site_data.get("street_name", "") or extracted.get("street_name", ""),
        city=site_data.get("city", "") or extracted.get("city", ""),
        state=site_data.get("state", "SC") or extracted.get("state", "SC"),
        zip=site_data.get("zip", "") or extracted.get("zip", ""),
        subdivision=site_data.get("subdivision", "") or extracted.get("subdivision", ""),
        lot_unit=site_data.get("lot_unit", "") or extracted.get("lot_unit", ""),
    )

    # Build contacts
    contacts = []
    raw_contacts = extracted.get("contacts", [])
    for c in raw_contacts:
        role_str = c.get("role", "inspector")
        try:
            role = ContactRole(role_str)
        except ValueError:
            role = ContactRole.INSPECTOR

        contacts.append(Contact(
            role=role,
            name=c.get("name", ""),
            org=c.get("org", ""),
            phone=c.get("phone", ""),
            email=c.get("email", ""),
        ))

    # Add inspector from extracted fields if not in contacts
    if extracted.get("inspector_name") or extracted.get("inspector_email"):
        inspector_exists = any(c.role == ContactRole.INSPECTOR for c in contacts)
        if not inspector_exists:
            contacts.append(Contact(
                role=ContactRole.INSPECTOR,
                name=extracted.get("inspector_name", ""),
                email=extracted.get("inspector_email", ""),
                phone=extracted.get("inspector_phone", ""),
            ))

    # Build initial record
    record = SmartrouteRecord(
        source=source,
        jurisdiction=jurisdiction,
        permit=permit,
        inspection=inspection,
        release=release,
        site=site,
        contacts=contacts,
    )

    # Route the record
    record.operational = route(record)

    # Compute quality metrics
    record_dict = record.to_dict()
    confidence, missing = compute_confidence(record_dict)

    field_conf = extracted.get("_field_confidence", {})
    record.quality = Quality(
        confidence_overall=confidence,
        field_confidence=field_conf,
        missing_required_fields=missing,
    )

    return record


def parse_message(
    raw_email_text: str,
    attachments: list[Attachment] = None,
    source_type: SourceType = SourceType.EMAIL,
    llm_client: Optional[LLMClient] = None,
) -> SmartrouteRecord:
    """
    Parse a raw message into a structured SmartRoute record.

    Args:
        raw_email_text: Raw text of the email/portal message
        attachments: List of Attachment objects with extracted text
        source_type: Type of source (email, portal, attachment_ocr)
        llm_client: Optional LLM client for enhanced extraction

    Returns:
        Fully populated SmartrouteRecord
    """
    if attachments is None:
        attachments = []

    # Step 1: Clean the text
    cleaned = clean_text(raw_email_text)

    # Step 2: Combine attachment text
    attachment_text = "\n\n".join(
        att.extracted_text for att in attachments if att.extracted_text
    )

    # Step 3: Extract fields
    extracted = extract_fields(cleaned, attachment_text, llm_client)

    # Step 4: Build and return record
    record = _build_record_from_extracted(
        extracted,
        raw_email_text,
        cleaned,
        attachments,
        source_type,
    )

    return record


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SmartRoute - Parse inspector communications into structured records"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input file (email text)"
    )
    parser.add_argument(
        "--out", "-o",
        help="Path to output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--source-type", "-t",
        choices=["email", "portal", "attachment_ocr"],
        default="email",
        help="Type of source document"
    )
    parser.add_argument(
        "--attachment", "-a",
        action="append",
        help="Path to attachment text file (can be used multiple times)"
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="Pretty-print JSON output"
    )

    args = parser.parse_args()

    # Read input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    raw_text = input_path.read_text(encoding="utf-8")

    # Read attachments
    attachments = []
    if args.attachment:
        for att_path in args.attachment:
            att_file = Path(att_path)
            if att_file.exists():
                attachments.append(Attachment(
                    filename=att_file.name,
                    content_type="text/plain",
                    extracted_text=att_file.read_text(encoding="utf-8"),
                ))

    # Determine source type
    source_type_map = {
        "email": SourceType.EMAIL,
        "portal": SourceType.PORTAL,
        "attachment_ocr": SourceType.ATTACHMENT_OCR,
    }
    source_type = source_type_map[args.source_type]

    # Parse the message
    record = parse_message(raw_text, attachments, source_type)

    # Convert to JSON
    indent = 2 if args.pretty else None
    output = json.dumps(record.to_dict(), indent=indent, default=str)

    # Write output
    if args.out:
        output_path = Path(args.out)
        output_path.write_text(output, encoding="utf-8")
        print(f"Output written to: {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
