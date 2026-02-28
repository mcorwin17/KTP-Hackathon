#!/usr/bin/env python3
"""
SmartRoute Web Demo — FastAPI application using Agent A's pipeline.

Run:
    source venv/bin/activate
    uvicorn app:app --reload --port 8000
"""

from __future__ import annotations

import json
import io
import re
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from smartroute import parse_message

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from PIL import Image
    import pytesseract
    IMAGE_OCR_SUPPORT = True
except ImportError:
    IMAGE_OCR_SUPPORT = False

# Supported file extensions
PDF_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp'}

app = FastAPI(title="SmartRoute", description="Inspector message extraction & routing demo", version="0.1.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class ExtractRequest(BaseModel):
    text: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/extract")
async def extract_endpoint(body: ExtractRequest):
    record = parse_message(body.text)
    # Flatten for display
    date_str = ""
    if record.inspection.inspection_date:
        date_str = record.inspection.inspection_date.strftime("%Y-%m-%d")
    elif record.release.release_date:
        date_str = record.release.release_date.strftime("%Y-%m-%d")

    inspector = ""
    for c in record.contacts:
        if c.role.value == "inspector":
            inspector = c.name
            break

    return {
        "record": {
            "permit_number": record.permit.permit_number,
            "inspection_date": date_str,
            "status": record.inspection.status.value,
            "site_address": record.site.address_full,
            "structure_type": record.release.structure_type,
            "inspector": inspector,
            "notes": record.inspection.description,
        },
        "routing": {
            "team": record.operational.route_to_team.value,
            "action_required": record.operational.action_required,
            "priority": record.operational.priority.value,
            "reason": record.operational.action_reason,
            "recommended_actions": record.operational.recommended_actions,
        },
        "confidence": record.quality.confidence_overall,
    }


@app.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """Extract text from uploaded PDF or image file."""
    filename = file.filename.lower()
    ext = Path(filename).suffix

    # Determine file type and process accordingly
    if ext in PDF_EXTENSIONS:
        return await _process_pdf(file)
    elif ext in IMAGE_EXTENSIONS:
        return await _process_image(file)
    else:
        supported = ', '.join(sorted(PDF_EXTENSIONS | IMAGE_EXTENSIONS))
        return {"error": f"Unsupported file type. Supported: {supported}"}


async def _process_pdf(file: UploadFile) -> dict:
    """Extract text from PDF file."""
    if not PDF_SUPPORT:
        return {"error": "PDF support not available. Install pdfplumber."}

    try:
        contents = await file.read()
        pdf_file = io.BytesIO(contents)

        extracted_text = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text.append(page_text)

        full_text = "\n\n".join(extracted_text)

        if not full_text.strip():
            return {"error": "Could not extract text from PDF. The PDF may be image-based or empty."}

        return {"text": full_text, "pages": len(extracted_text), "type": "pdf"}

    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}


async def _process_image(file: UploadFile) -> dict:
    """Extract text from image file using OCR with confidence filtering.

    Uses per-word confidence scores to discard text from blacked-out,
    redacted, or otherwise unreadable regions. Only words with
    confidence >= MIN_OCR_CONFIDENCE are kept.
    """
    MIN_OCR_CONFIDENCE = 60  # 0-100 scale; below this = likely garbage/redacted

    if not IMAGE_OCR_SUPPORT:
        return {"error": "Image OCR not available. Install Pillow and pytesseract."}

    try:
        contents = await file.read()
        image_file = io.BytesIO(contents)
        image = Image.open(image_file)

        # Use image_to_data for per-word confidence scores
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Rebuild text keeping only high-confidence words
        # Group words by (block, paragraph, line) to preserve structure
        lines: dict[tuple[int, int, int], list[str]] = {}
        n_total = 0
        n_kept = 0

        for i, word in enumerate(ocr_data["text"]):
            word = word.strip()
            if not word:
                continue

            n_total += 1
            conf = int(ocr_data["conf"][i])

            # Skip low-confidence words (redacted/blacked-out regions)
            if conf < MIN_OCR_CONFIDENCE:
                continue

            n_kept += 1
            line_key = (
                ocr_data["block_num"][i],
                ocr_data["par_num"][i],
                ocr_data["line_num"][i],
            )
            lines.setdefault(line_key, []).append(word)

        # Assemble lines in reading order
        extracted_lines = []
        prev_block = None
        for key in sorted(lines.keys()):
            block = key[0]
            if prev_block is not None and block != prev_block:
                extracted_lines.append("")  # blank line between blocks
            prev_block = block
            extracted_lines.append(" ".join(lines[key]))

        extracted_text = "\n".join(extracted_lines)

        # Scrub partial/incomplete structured data
        extracted_text = _scrub_partial_fragments(extracted_text)

        if not extracted_text.strip():
            return {"error": "Could not extract readable text from image. The content may be redacted or too degraded."}

        return {
            "text": extracted_text,
            "type": "image",
            "ocr_stats": {
                "total_words_detected": n_total,
                "words_kept": n_kept,
                "words_filtered": n_total - n_kept,
                "confidence_threshold": MIN_OCR_CONFIDENCE,
            },
        }

    except Exception as e:
        return {"error": f"Failed to process image: {str(e)}"}


def _scrub_partial_fragments(text: str) -> str:
    """Remove incomplete emails, phone numbers, and addresses from OCR text.

    If OCR only captured a fragment (e.g. redacted portions), drop it
    entirely rather than passing garbage to the extraction pipeline.
    """
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        words = line.split()
        kept = []
        for word in words:
            # --- Partial emails: has @ but isn't a valid email ---
            if "@" in word:
                if re.match(r'^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$', word):
                    kept.append(word)  # valid email, keep it
                # else: drop the fragment
                continue

            # --- Partial phone numbers: digit-heavy but too short ---
            digits_only = re.sub(r'\D', '', word)
            if len(digits_only) >= 3 and len(digits_only) < 7:
                # Looks like a truncated phone number (3-6 digits with
                # punctuation like "555-12" or "(803)"). Skip it.
                digit_ratio = len(digits_only) / max(len(word), 1)
                if digit_ratio > 0.5:
                    continue

            # --- Partial URLs: starts with http but no full domain ---
            if word.startswith(('http://', 'https://')):
                if re.match(r'https?://[\w.-]+\.[a-zA-Z]{2,}', word):
                    kept.append(word)  # valid URL
                continue

            # --- Random short garbage (1-2 char fragments) ---
            if len(word) <= 1 and not word.isdigit() and word not in ('I', 'a', 'A', '&', '#', '-', '/'):
                continue

            kept.append(word)

        cleaned.append(" ".join(kept))

    # Remove blank lines that resulted from scrubbing
    result_lines = []
    for line in cleaned:
        if line.strip() or (result_lines and result_lines[-1].strip()):
            result_lines.append(line)

    return "\n".join(result_lines).strip()


# Keep old endpoint for backwards compatibility
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Legacy endpoint - redirects to upload-file."""
    return await upload_file(file)


@app.get("/health")
async def health():
    return {"status": "ok", "pdf_support": PDF_SUPPORT, "image_ocr_support": IMAGE_OCR_SUPPORT}
