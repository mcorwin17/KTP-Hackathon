"""Smoke tests for the full pipeline."""

import pytest
from smartroute.pipeline import parse_message, extract_fields, clean_text
from smartroute.models import Attachment, SourceType


class TestParseMessage:
    """End-to-end tests for message parsing."""

    def test_parses_simple_email(self):
        raw = """
        Permit #2511463
        Address: 123 Main Street, Columbia, SC 29201

        Inspection Status: Pass

        The electrical inspection has been completed and approved.
        """

        record = parse_message(raw)

        assert record.permit.permit_number == "2511463"
        assert "123 Main Street" in record.site.address_full
        assert record.inspection.status.value == "pass"

    def test_parses_failed_inspection_email(self):
        raw = """
        INSPECTION NOTICE

        Permit Number: BLD-2024-98765
        Location: 456 Oak Avenue

        Inspection Status: Failed

        Corrections required:
        - Missing smoke detector in bedroom
        - Electrical outlet not grounded

        Please schedule a re-inspection after corrections are made.
        """

        record = parse_message(raw)

        assert "98765" in record.permit.permit_number
        assert record.inspection.status.value == "fail"
        assert record.operational.action_required is True
        assert record.operational.route_to_team.value == "FIELD_DISPATCH"

    def test_parses_release_approval_email(self):
        raw = """
        RELEASE NOTIFICATION

        Permit #EPR-2025-001
        Address: 789 Pine Road, Charleston, SC

        Electrical Power Release has been approved.

        The utility company may now connect power to the property.
        """

        record = parse_message(raw)

        assert "EPR-2025-001" in record.permit.permit_number
        assert "Electrical Power Release" in record.release.release_type
        assert record.operational.action_required is True
        assert record.operational.route_to_team.value == "RELEASE_DESK"

    def test_parses_portal_style_text(self):
        raw = """
        ===== INSPECTION SUMMARY =====

        Permit #: 1234567
        Type: Residential
        Address: 100 Beach Blvd
        City: Myrtle Beach

        Inspection Date: 01/15/2025
        Inspector: John Smith
        Result: APPROVED

        Notes: Lock box code 0752
        ===============================
        """

        record = parse_message(raw, source_type=SourceType.PORTAL)

        assert record.permit.permit_number == "1234567"
        assert record.source.source_type == SourceType.PORTAL
        assert record.inspection.status.value == "pass"

    def test_handles_attachments(self):
        raw = "Please see attached inspection report."

        attachment = Attachment(
            filename="report.txt",
            content_type="text/plain",
            extracted_text="""
            Permit Number: ATT-9999
            Inspection Result: Pass
            Address: 555 Attachment Lane
            """
        )

        record = parse_message(raw, attachments=[attachment])

        assert "ATT-9999" in record.permit.permit_number

    def test_cleans_noisy_email(self):
        raw = """CAUTION! This message was NOT SENT from a trusted source.
Be very careful with any links or attachments!

From: inspector@county.gov
To: contractor@builder.com
Subject: Inspection Results

Permit #CLEAN-123
Address: 999 Test Street

Status: Pass

Regards,
Inspector"""

        record = parse_message(raw)

        # Should have extracted the permit despite the noise
        assert "CLEAN-123" in record.permit.permit_number
        assert record.inspection.status.value == "pass"

        # Clean text should not have the banner
        assert "CAUTION" not in record.source.clean_text


class TestExtractFields:
    """Tests for field extraction."""

    def test_extracts_from_clean_text(self):
        text = """
        Permit #EXT-456
        123 Extract Street
        Status: Approved
        """

        result = extract_fields(text)

        assert "permit" in result
        assert "site" in result

    def test_extracts_with_attachment(self):
        main_text = "See attachment for details."
        attachment_text = """
        Permit: #ATT-2026-99999
        Result: Failed
        """

        result = extract_fields(main_text, attachment_text)

        assert result.get("permit", {}).get("permit_number") or result.get("permit_number")


class TestQualityMetrics:
    """Tests for quality/confidence scoring."""

    def test_high_confidence_for_complete_data(self):
        raw = """
        Permit #CONF-001
        Address: 123 Complete Street, Columbia, SC 29201
        Inspection Status: Pass
        Inspector: John Doe
        Email: john@county.gov
        """

        record = parse_message(raw)

        # Should have reasonable confidence with key fields present
        assert record.quality.confidence_overall > 0.5

    def test_identifies_missing_fields(self):
        raw = "Just some text without any structured data."

        record = parse_message(raw)

        # Should identify missing required fields
        assert len(record.quality.missing_required_fields) > 0


class TestRouting:
    """Tests for routing logic."""

    def test_routes_failed_to_field_dispatch(self):
        raw = """
        Permit #ROUTE-001
        Status: Failed
        Corrections needed before re-inspection.
        """

        record = parse_message(raw)

        assert record.operational.action_required is True
        assert record.operational.route_to_team.value == "FIELD_DISPATCH"

    def test_routes_release_to_release_desk(self):
        raw = """
        Permit #ROUTE-002
        Electrical Power Release approved.
        """

        record = parse_message(raw)

        assert record.operational.route_to_team.value == "RELEASE_DESK"

    def test_passed_inspection_lower_priority(self):
        raw = """
        Permit #ROUTE-003
        Inspection Status: Pass
        Everything looks good.
        """

        record = parse_message(raw)

        assert record.operational.action_required is False
        assert record.operational.priority.value == "low"

    def test_urgent_keywords_increase_priority(self):
        raw = """
        URGENT: Permit #ROUTE-004
        Immediate attention required!
        """

        record = parse_message(raw)

        assert record.operational.priority.value == "high"
