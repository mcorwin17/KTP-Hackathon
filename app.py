#!/usr/bin/env python3
"""
SmartRoute Web Demo — FastAPI application using Agent A's pipeline.

Run:
    source venv/bin/activate
    uvicorn app:app --reload --port 8000
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from smartroute import parse_message

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


@app.get("/health")
async def health():
    return {"status": "ok"}
