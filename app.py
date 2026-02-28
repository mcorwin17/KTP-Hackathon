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


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Extract text from uploaded PDF and return it."""
    if not PDF_SUPPORT:
        return {"error": "PDF support not available. Install pdfplumber."}

    if not file.filename.lower().endswith('.pdf'):
        return {"error": "File must be a PDF"}

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

        return {"text": full_text, "pages": len(extracted_text)}

    except Exception as e:
        return {"error": f"Failed to process PDF: {str(e)}"}


@app.get("/health")
async def health():
    return {"status": "ok", "pdf_support": PDF_SUPPORT}
