"""
SmartRoute - Intelligent intake/extraction engine for inspector communications.

Transforms messy inspector emails, portal text, and OCR'd attachments into
normalized structured records with action routing.
"""

from .models import SmartrouteRecord, Attachment
from .pipeline import parse_message
from .cleaning import clean_text
from .routing import route

__version__ = "0.1.0"
__all__ = [
    "SmartrouteRecord",
    "Attachment",
    "parse_message",
    "clean_text",
    "route",
]
