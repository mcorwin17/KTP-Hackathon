"""Tests for regex-based extraction."""

import pytest
from smartroute.extractors.regex_extractor import RegexExtractor


@pytest.fixture
def extractor():
    return RegexExtractor()


class TestPermitExtraction:
    """Tests for permit number extraction."""

    def test_extracts_permit_with_hash(self, extractor):
        text = "Permit #2511463 has been approved."
        result = extractor.extract(text)
        assert result["permit"]["permit_number"] == "2511463"

    def test_extracts_permit_with_number_label(self, extractor):
        text = "Permit Number: ABC-2024-12345"
        result = extractor.extract(text)
        assert "ABC-2024-12345" in result["permit"]["permit_number"]

    def test_extracts_permit_with_colon(self, extractor):
        text = "Permit: #7890123 for electrical work"
        result = extractor.extract(text)
        assert "7890123" in result["permit"]["permit_number"]

    def test_no_permit_returns_empty(self, extractor):
        text = "This message has no permit information."
        result = extractor.extract(text)
        assert result["permit"].get("permit_number", "") == ""


class TestDateExtraction:
    """Tests for date extraction."""

    def test_extracts_full_date_with_day(self, extractor):
        text = "Scheduled for Monday, December 22, 2025 at 3:00 PM"
        result = extractor.extract(text)
        dates = result.get("_extracted_dates", [])
        assert len(dates) > 0
        assert "2025-12-22" in [d["parsed"] for d in dates]

    def test_extracts_mm_dd_yyyy(self, extractor):
        text = "Inspection date: 12/19/2025"
        result = extractor.extract(text)
        dates = result.get("_extracted_dates", [])
        assert len(dates) > 0
        assert "2025-12-19" in [d["parsed"] for d in dates]

    def test_extracts_iso_date(self, extractor):
        text = "Released on 2025-01-15"
        result = extractor.extract(text)
        dates = result.get("_extracted_dates", [])
        assert len(dates) > 0
        assert "2025-01-15" in [d["parsed"] for d in dates]

    def test_extracts_month_name_date(self, extractor):
        text = "The release was granted January 5, 2025"
        result = extractor.extract(text)
        dates = result.get("_extracted_dates", [])
        assert len(dates) > 0
        assert "2025-01-05" in [d["parsed"] for d in dates]


class TestStatusExtraction:
    """Tests for inspection status extraction."""

    def test_extracts_pass_status(self, extractor):
        text = "Inspection Status: Pass"
        result = extractor.extract(text)
        assert result["inspection"]["status"] == "pass"

    def test_extracts_failed_status(self, extractor):
        text = "The inspection failed due to code violations."
        result = extractor.extract(text)
        assert result["inspection"]["status"] == "fail"

    def test_extracts_approved_as_pass(self, extractor):
        text = "Your permit has been approved."
        result = extractor.extract(text)
        assert result["inspection"]["status"] == "pass"

    def test_reinspection_required_is_fail(self, extractor):
        text = "Re-inspection required after corrections."
        result = extractor.extract(text)
        assert result["inspection"]["status"] == "fail"


class TestAddressExtraction:
    """Tests for address extraction."""

    def test_extracts_labeled_address(self, extractor):
        text = "Address: 123 Main Street, Columbia"
        result = extractor.extract(text)
        assert "123 Main Street" in result["site"]["address_full"]

    def test_extracts_street_address_pattern(self, extractor):
        text = "Site located at 456 Oak Avenue for inspection."
        result = extractor.extract(text)
        assert "456 Oak Avenue" in result["site"]["address_full"]

    def test_extracts_address_with_drive(self, extractor):
        text = "Property: 789 Sunset Drive, Charleston"
        result = extractor.extract(text)
        assert "789 Sunset Drive" in result["site"]["address_full"]


class TestContactExtraction:
    """Tests for contact information extraction."""

    def test_extracts_email(self, extractor):
        text = "Contact the inspector at john.smith@county.gov"
        result = extractor.extract(text)
        emails = [c["email"] for c in result["contacts"] if "email" in c]
        assert "john.smith@county.gov" in emails

    def test_extracts_phone_number(self, extractor):
        text = "Phone: (555) 123-4567"
        result = extractor.extract(text)
        phones = [c["phone"] for c in result["contacts"] if "phone" in c]
        assert any("5551234567" in p for p in phones)

    def test_extracts_multiple_contacts(self, extractor):
        text = """Inspector: bob@county.gov
Contractor: builder@company.com
Phone: 555-987-6543"""
        result = extractor.extract(text)
        assert len(result["contacts"]) >= 2


class TestInspectionTypeExtraction:
    """Tests for inspection type extraction."""

    def test_extracts_electrical_inspection(self, extractor):
        text = "Electrical Inspection scheduled for tomorrow."
        result = extractor.extract(text)
        assert "Electrical" in result["inspection"]["inspection_type"]

    def test_extracts_type_from_label(self, extractor):
        text = "Inspection Type: Rough Plumbing"
        result = extractor.extract(text)
        assert "Plumbing" in result["inspection"]["inspection_type"] or "Rough" in result["inspection"]["inspection_type"]


class TestReleaseTypeExtraction:
    """Tests for release type extraction."""

    def test_extracts_electrical_power_release(self, extractor):
        text = "Electrical Power Release has been granted."
        result = extractor.extract(text)
        assert "Electrical Power Release" in result["release"]["release_type"]

    def test_extracts_utility_release(self, extractor):
        text = "Utility Release approved for the property."
        result = extractor.extract(text)
        assert "Utility" in result["release"]["release_type"]
