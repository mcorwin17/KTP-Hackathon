"""Text cleaning utilities for removing noise from inspector communications."""

import re
from typing import Tuple


# Security banner patterns
SECURITY_BANNER_PATTERNS = [
    r"CAUTION[!:]?\s*This message was NOT SENT.*?(?=\n\n|\Z)",
    r"CAUTION[!:]?\s*This email originated.*?(?=\n\n|\Z)",
    r"\[EXTERNAL\].*?(?=\n)",
    r"This message is from an external sender.*?(?=\n\n|\Z)",
    r"WARNING:?\s*This email.*?outside.*?(?=\n\n|\Z)",
    r"DISCLAIMER:.*?(?=\n\n|\Z)",
    r"CONFIDENTIALITY NOTICE:.*?(?=\n\n|\Z)",
    r"This email and any attachments.*?confidential.*?(?=\n\n|\Z)",
]

# Email header patterns
EMAIL_HEADER_PATTERNS = [
    r"^From:.*$",
    r"^To:.*$",
    r"^Cc:.*$",
    r"^Bcc:.*$",
    r"^Date:.*$",
    r"^Subject:.*$",
    r"^Sent:.*$",
    r"^Received:.*$",
    r"^Reply-To:.*$",
    r"^Message-ID:.*$",
    r"^Content-Type:.*$",
    r"^MIME-Version:.*$",
    r"^X-.*:.*$",
]

# Reply/forward quote patterns
REPLY_PATTERNS = [
    r"^>+\s*.*$",
    r"^On .* wrote:$",
    r"^-{3,}\s*Original Message\s*-{3,}.*",
    r"^-{3,}\s*Forwarded Message\s*-{3,}.*",
    r"^From:.*\nSent:.*\nTo:.*\nSubject:.*",
]

# Signature separators and common signatures
SIGNATURE_PATTERNS = [
    r"\n--\s*\n.*",
    r"\nRespectfully,?\s*\n.*",
    r"\nRegards,?\s*\n.*",
    r"\nBest regards,?\s*\n.*",
    r"\nSincerely,?\s*\n.*",
    r"\nThank you,?\s*\n.*",
    r"\nThanks,?\s*\n.*",
    r"\nBest,?\s*\n.*",
]


def remove_security_banners(text: str) -> str:
    """Remove security warning banners from email text."""
    result = text
    for pattern in SECURITY_BANNER_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
    return result


def remove_email_headers(text: str) -> str:
    """Remove email header lines."""
    result = text
    for pattern in EMAIL_HEADER_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.MULTILINE | re.IGNORECASE)
    return result


def remove_reply_quotes(text: str) -> str:
    """Remove quoted reply content."""
    result = text
    for pattern in REPLY_PATTERNS:
        result = re.sub(pattern, "", result, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    return result


def extract_signature(text: str) -> Tuple[str, str]:
    """
    Extract and separate signature from main text.

    Returns:
        Tuple of (main_text, signature_text)
    """
    signature = ""
    main_text = text

    for pattern in SIGNATURE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            signature = match.group(0)
            main_text = text[:match.start()]
            break

    return main_text, signature


def normalize_whitespace(text: str) -> str:
    """Normalize excessive whitespace and line breaks."""
    # Replace multiple spaces with single space
    result = re.sub(r"[ \t]+", " ", text)
    # Replace 3+ newlines with 2 newlines
    result = re.sub(r"\n{3,}", "\n\n", result)
    # Remove leading/trailing whitespace from lines
    result = "\n".join(line.strip() for line in result.split("\n"))
    # Remove leading/trailing whitespace from entire text
    result = result.strip()
    return result


def remove_html_artifacts(text: str) -> str:
    """Remove common HTML artifacts that might remain after conversion."""
    # Remove HTML tags
    result = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    html_entities = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&apos;": "'",
    }
    for entity, replacement in html_entities.items():
        result = result.replace(entity, replacement)
    return result


def clean_text(raw_text: str, preserve_signature: bool = False) -> str:
    """
    Clean raw email/portal text by removing noise.

    Args:
        raw_text: The raw text to clean
        preserve_signature: If True, keeps signature section (marked)

    Returns:
        Cleaned text suitable for extraction
    """
    if not raw_text:
        return ""

    text = raw_text

    # Remove HTML artifacts first
    text = remove_html_artifacts(text)

    # Remove security banners
    text = remove_security_banners(text)

    # Remove email headers
    text = remove_email_headers(text)

    # Remove reply quotes
    text = remove_reply_quotes(text)

    # Handle signature
    if preserve_signature:
        main_text, signature = extract_signature(text)
        if signature:
            text = main_text + "\n\n[SIGNATURE]\n" + signature
        else:
            text = main_text
    else:
        text, _ = extract_signature(text)

    # Normalize whitespace
    text = normalize_whitespace(text)

    return text
