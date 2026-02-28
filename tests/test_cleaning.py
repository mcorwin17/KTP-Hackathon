"""Tests for text cleaning utilities."""

import pytest
from smartroute.cleaning import (
    clean_text,
    remove_security_banners,
    remove_email_headers,
    remove_reply_quotes,
    extract_signature,
    normalize_whitespace,
)


class TestRemoveSecurityBanners:
    """Tests for security banner removal."""

    def test_removes_caution_banner(self):
        text = """CAUTION! This message was NOT SENT from a trusted source.
Be careful with links and attachments.

Hello, this is the actual message."""
        result = remove_security_banners(text)
        assert "CAUTION" not in result
        assert "Hello, this is the actual message." in result

    def test_removes_external_sender_warning(self):
        text = """[EXTERNAL] This email came from outside the organization.

Please review the inspection results."""
        result = remove_security_banners(text)
        assert "[EXTERNAL]" not in result
        assert "Please review the inspection results." in result

    def test_preserves_normal_text(self):
        text = "This is a normal email about permit #12345."
        result = remove_security_banners(text)
        assert result == text


class TestRemoveEmailHeaders:
    """Tests for email header removal."""

    def test_removes_from_header(self):
        text = """From: inspector@county.gov
To: contractor@company.com
Subject: Inspection Results

The inspection passed."""
        result = remove_email_headers(text)
        assert "From:" not in result
        assert "To:" not in result
        assert "Subject:" not in result
        assert "The inspection passed." in result

    def test_removes_x_headers(self):
        text = """X-Mailer: Microsoft Outlook
X-Spam-Status: No

Actual content here."""
        result = remove_email_headers(text)
        assert "X-Mailer" not in result
        assert "X-Spam-Status" not in result
        assert "Actual content here." in result


class TestRemoveReplyQuotes:
    """Tests for reply quote removal."""

    def test_removes_quoted_text(self):
        text = """> This is quoted text
> From a previous email
>
> More quoted text

My actual response."""
        result = remove_reply_quotes(text)
        assert "quoted text" not in result
        assert "My actual response." in result

    def test_removes_original_message_block(self):
        text = """My reply here.

--- Original Message ---
From: someone@email.com
Subject: Previous subject

Original content."""
        result = remove_reply_quotes(text)
        assert "My reply here." in result
        assert "Original Message" not in result


class TestExtractSignature:
    """Tests for signature extraction."""

    def test_extracts_regards_signature(self):
        text = """Please review the attached report.

Regards,
John Smith
Inspector
County Building Department"""
        main, sig = extract_signature(text)
        assert "Please review" in main
        assert "John Smith" in sig

    def test_extracts_respectfully_signature(self):
        text = """The inspection is complete.

Respectfully,
Jane Doe"""
        main, sig = extract_signature(text)
        assert "inspection is complete" in main
        assert "Jane Doe" in sig

    def test_no_signature_returns_original(self):
        text = "Just a simple message with no signature."
        main, sig = extract_signature(text)
        assert main == text
        assert sig == ""


class TestNormalizeWhitespace:
    """Tests for whitespace normalization."""

    def test_collapses_multiple_spaces(self):
        text = "This   has    multiple    spaces."
        result = normalize_whitespace(text)
        assert result == "This has multiple spaces."

    def test_collapses_multiple_newlines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = normalize_whitespace(text)
        assert result == "Line 1\n\nLine 2"

    def test_trims_line_whitespace(self):
        text = "  Leading spaces  \n  Another line  "
        result = normalize_whitespace(text)
        assert result == "Leading spaces\nAnother line"


class TestCleanText:
    """Integration tests for full text cleaning."""

    def test_cleans_typical_email(self):
        raw = """CAUTION! This message was NOT SENT from a trusted source.
Be careful!

From: inspector@county.gov
To: builder@company.com
Subject: Inspection Complete

Permit #2511463 - 123 Main Street

The electrical inspection has passed.

Regards,
Inspector Bob
County Building Dept
(555) 123-4567"""

        result = clean_text(raw)

        # Should remove banner and headers
        assert "CAUTION" not in result
        assert "From:" not in result

        # Should keep important content
        assert "Permit #2511463" in result
        assert "123 Main Street" in result
        assert "electrical inspection has passed" in result

    def test_preserves_signature_when_requested(self):
        raw = """Inspection complete.

Regards,
Bob Smith"""

        result = clean_text(raw, preserve_signature=True)
        assert "[SIGNATURE]" in result
        assert "Bob Smith" in result

    def test_handles_empty_input(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""
