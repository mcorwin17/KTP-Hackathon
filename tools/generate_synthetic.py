#!/usr/bin/env python3
"""
Synthetic Inspector Message Generator — "Real-World Chaos" Engine.

Generates 200–2,000 synthetic inspector messages across 5 template families
with configurable noise injection. Ground truth uses Agent A's SmartrouteRecord
compatible format.

Usage:
    python tools/generate_synthetic.py --count 500 --output-dir data/synthetic/ --seed 42 --noise-level 0.3
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(0)

# ── Data Pools ──────────────────────────────────────────────────────────────

PERMIT_PREFIXES = ["BP", "CP", "IP", "MP", "EP", "FP"]
CITIES = ["Springfield", "Shelbyville", "Capital City", "Ogdenville", "North Haverbrook", "Brockway"]
STREETS = [
    "Main St", "Oak Ave", "Elm Blvd", "Pine Dr", "Maple Rd", "Cedar Ln", "Birch Ct",
    "Walnut Way", "Ash Pl", "Spruce Cir", "Willow Ter", "Cypress Way", "Sequoia Dr",
    "Redwood Ave", "Chestnut St", "Hickory Ln", "Magnolia Blvd", "Sycamore Rd",
    "Poplar Ct", "Juniper Way", "Dogwood Dr", "Beech Ave", "Alder Ln",
]
ZIPS = ["62701", "62702", "62703", "62704", "62705", "62706", "62707", "62708"]
INSPECTOR_NAMES = [
    "John Smith", "Jane Doe", "Robert Garcia", "Maria Chen", "Tom Wilson",
    "Sarah Kim", "James Lee", "Lisa Wang", "David Park", "Anna Lopez",
    "Chris Brown", "Michelle Lee", "Kevin Nguyen", "Diane Cruz", "Ryan Taylor",
    "Amy Johnson", "Eric Martinez", "Nicole White", "Brian Hall", "Stephanie Adams",
]
# Agent A status enum values
STATUSES = ["pass", "fail", "partial", "unknown"]
STRUCTURE_TYPES = ["residential", "commercial", "industrial", "mixed-use"]

LEGAL_BANNERS = [
    "CONFIDENTIALITY NOTICE: This email and any attachments are intended solely for the use of the individual or entity to whom they are addressed. If you are not the named addressee, you should not disseminate, distribute, or copy this email.",
    "DISCLAIMER: The information contained in this transmission is privileged and confidential and protected from disclosure.",
    "*** CAUTION: This email originated from outside of the organization. Do not click links or open attachments unless you recognize the sender and know the content is safe. ***",
    "This message is from the City of Springfield Department of Buildings & Inspections. All inspection data is subject to FOIA regulations.",
    "SECURITY WARNING: This system is for authorized use only. Unauthorized access or use may result in disciplinary action.",
]

STATUS_DISPLAY = {
    "pass": ["Passed", "Pass", "Approved", "OK", "Complete"],
    "fail": ["Failed", "Fail", "Rejected", "Denied", "Not Approved"],
    "partial": ["Partial", "Conditional", "Conditional Approval"],
    "unknown": ["Pending", "Scheduled", "Under Review", "In Review"],
}


def _generate_record(rng: random.Random) -> dict:
    prefix = rng.choice(PERMIT_PREFIXES)
    year = rng.choice([2025, 2026])
    seq = rng.randint(100, 99999)
    permit = f"{prefix}-{year}-{seq:05d}"

    base_date = datetime(2025, 6, 1)
    inspection_date = base_date + timedelta(days=rng.randint(0, 400))
    date_str = inspection_date.strftime("%Y-%m-%d")

    number = rng.randint(100, 9999)
    street = f"{number} {rng.choice(STREETS)}"
    city = rng.choice(CITIES)
    zipcode = rng.choice(ZIPS)
    address = f"{street}, {city}, {zipcode}"

    status = rng.choice(STATUSES)
    stype = rng.choice(STRUCTURE_TYPES)
    inspector = rng.choice(INSPECTOR_NAMES)

    notes_options = [
        "All clear, no issues found.",
        "Wiring issues in panel B-3.",
        "Needs follow-up inspection within 30 days.",
        "Safety violations noted — see attached report.",
        "Conditional pass — minor corrections required.",
        "Final inspection completed successfully.",
        "Plumbing code violation in basement unit.",
        "",
    ]
    notes = rng.choice(notes_options)

    return {
        "permit_number": permit,
        "inspection_date": date_str,
        "status": status,
        "site_address": address,
        "structure_type": stype,
        "inspector_name": inspector,
        "notes": notes or "",
    }


# ── Date Format Variants ────────────────────────────────────────────────────

def _format_date_variant(date_str: str, rng: random.Random) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    formats = [
        dt.strftime("%Y-%m-%d"), dt.strftime("%m/%d/%Y"), dt.strftime("%m/%d/%y"),
        dt.strftime("%d-%b-%Y"), dt.strftime("%B %d, %Y"), dt.strftime("%b %d %Y"),
        f"{dt.month}/{dt.day}/{dt.year}",
    ]
    return rng.choice(formats)


# ── Noise Injection ─────────────────────────────────────────────────────────

def _ocr_degrade(text: str, rng: random.Random, intensity: float) -> str:
    replacements = {"0": "O", "O": "0", "1": "l", "l": "1", "5": "S", ":": ";", ",": "."}
    chars = list(text)
    for i, c in enumerate(chars):
        if c in replacements and rng.random() < intensity * 0.15:
            chars[i] = replacements[c]
    return "".join(chars)


def _typo_word(word: str, rng: random.Random) -> str:
    if len(word) < 3 or rng.random() > 0.3:
        return word
    ops = ["swap", "drop", "double", "replace"]
    op = rng.choice(ops)
    idx = rng.randint(0, len(word) - 1)
    chars = list(word)
    if op == "swap" and idx < len(chars) - 1:
        chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    elif op == "drop":
        chars.pop(idx)
    elif op == "double":
        chars.insert(idx, chars[idx])
    elif op == "replace":
        chars[idx] = rng.choice(string.ascii_lowercase)
    return "".join(chars)


# ── Template Families ────────────────────────────────────────────────────────

def _template_formal_bureaucratic(record: dict, rng: random.Random, noise: float) -> str:
    dt = datetime.now() - timedelta(hours=rng.randint(1, 72))
    timestamp = dt.strftime("%A, %B %d, %Y %I:%M %p EST")
    date_display = _format_date_variant(record["inspection_date"], rng)
    status_display = rng.choice(STATUS_DISPLAY[record["status"]])

    sections = [
        f"From: {record['inspector_name']} <{record['inspector_name'].lower().replace(' ', '.')}@springfield.gov>",
        f"Sent: {timestamp}",
        f"To: inspections-intake@springfield.gov",
        f"Subject: Inspection Report — Permit {record['permit_number']}",
        "",
    ]
    if rng.random() < 0.7 + noise * 0.3:
        sections.extend(["=" * 60, rng.choice(LEGAL_BANNERS), "=" * 60, ""])
    sections.extend([
        "Dear Inspections Team,", "",
        "This memo serves as the official inspection report for the following permit:", "",
        f"    Permit Number:     {record['permit_number']}",
        f"    Inspection Date:   {date_display}",
        f"    Site Address:      {record['site_address']}",
        f"    Structure Type:    {record['structure_type'].title()}",
        f"    Result:            {status_display}",
        f"    Inspector:         {record['inspector_name']}",
        "",
    ])
    if record["notes"]:
        sections.extend([f"    Notes: {record['notes']}", ""])
    sections.extend([
        "Please process this report in accordance with departmental procedures.", "",
        "Respectfully,", record["inspector_name"],
        "Building Inspector, Grade III",
        f"City of Springfield — Dept. of Buildings & Inspections",
        f"Tel: (555) {rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
    ])
    if rng.random() < 0.5 + noise * 0.3:
        sections.extend(["", "─" * 60, rng.choice(LEGAL_BANNERS)])
    text = "\n".join(sections)
    return _ocr_degrade(text, rng, noise) if noise > 0 else text


def _template_portal_scraping(record: dict, rng: random.Random, noise: float) -> str:
    date_display = _format_date_variant(record["inspection_date"], rng)
    status_display = rng.choice(STATUS_DISPLAY[record["status"]])
    sep = rng.choice([": ", " = ", " - ", ":\t", " → "])
    permit_labels = ["Permit No", "Permit #", "Permit Number", "PERMIT"]
    date_labels = ["Inspection Date", "Date", "Insp Date"]
    addr_labels = ["Site Address", "Property Address", "Address", "Location"]
    type_labels = ["Structure Type", "Bldg Type", "Type"]
    result_labels = ["Status", "Result", "Inspection Result", "Outcome"]
    inspector_labels = ["Inspector", "Inspected By", "Examiner"]

    lines = [
        "--- INSPECTION PORTAL EXPORT ---",
        f"Generated{sep}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
        f"{rng.choice(permit_labels)}{sep}{record['permit_number']}",
        f"{rng.choice(date_labels)}{sep}{date_display}",
        f"{rng.choice(addr_labels)}{sep}{record['site_address']}",
        f"{rng.choice(type_labels)}{sep}{record['structure_type'].title()}",
        f"{rng.choice(result_labels)}{sep}{status_display}",
        f"{rng.choice(inspector_labels)}{sep}{record['inspector_name']}",
    ]
    if record["notes"]:
        lines.append(f"Notes{sep}{record['notes']}")
    lines.extend(["", "--- END OF RECORD ---"])
    if noise > 0 and rng.random() < noise:
        lines.insert(rng.randint(2, len(lines) - 1), f"SessionID{sep}{fake.uuid4()[:8]}")
    text = "\n".join(lines)
    return _ocr_degrade(text, rng, noise) if noise > 0 else text


def _template_forward_chain(record: dict, rng: random.Random, noise: float) -> str:
    date_display = _format_date_variant(record["inspection_date"], rng)
    status_display = rng.choice(STATUS_DISPLAY[record["status"]])
    dt = datetime.now() - timedelta(hours=rng.randint(2, 96))
    depth = rng.randint(1, 3)

    sections = [
        f"From: dispatch@springfield.gov", f"To: team-leads@springfield.gov",
        f"Subject: FW: FW: Inspection Update — {record['permit_number']}",
        f"Date: {dt.strftime('%m/%d/%Y %I:%M %p')}", "",
        "Team,", "", f"Please see the inspection result below for permit {record['permit_number']}.",
        f"Routing action needed: {'YES' if record['status'] in ('fail', 'partial') else 'NO'}", "",
    ]
    for layer in range(depth):
        sections.extend([
            "─" * 40, "---------- Forwarded message ----------",
            f"From: {record['inspector_name'].lower().replace(' ', '.')}@springfield.gov",
            f"Date: {(dt - timedelta(hours=rng.randint(1, 24))).strftime('%a, %b %d, %Y at %I:%M %p')}",
            f"Subject: {'Re: ' * layer}Inspection Report", "",
        ])
    sections.extend([
        "Inspection completed.",
        f"Permit: {record['permit_number']}", f"Date: {date_display}",
        f"Address: {record['site_address']}", f"Type: {record['structure_type'].title()}",
        f"Result: {status_display}", f"Inspector: {record['inspector_name']}",
    ])
    if record["notes"]:
        sections.append(f"Notes: {record['notes']}")
    sections.extend(["", "--", record["inspector_name"], "Building Inspector"])
    if noise > 0 and rng.random() < noise:
        sections.insert(0, rng.choice(LEGAL_BANNERS))
    text = "\n".join(sections)
    return _ocr_degrade(text, rng, noise) if noise > 0 else text


def _template_minimalist_mobile(record: dict, rng: random.Random, noise: float) -> str:
    date_display = _format_date_variant(record["inspection_date"], rng)
    permit_short = record["permit_number"]
    for prefix in PERMIT_PREFIXES:
        permit_short = permit_short.replace(f"{prefix}-", "")

    result_map = {
        "pass": rng.choice(["pass", "ok", "good", "approved", "✓", "👍"]),
        "fail": rng.choice(["fail", "no good", "rejected", "❌", "nope"]),
        "partial": rng.choice(["partial", "cond", "maybe", "needs work"]),
        "unknown": rng.choice(["pending", "tbd", "waiting", "hold"]),
    }
    result_short = result_map.get(record["status"], "???")
    addr_short = record["site_address"].split(",")[0]

    templates = [
        f"Prmt {permit_short} {result_short} for {record['structure_type'][:3]}",
        f"insp done {record['permit_number']} - {result_short}. addr {addr_short}",
        f"{record['permit_number']} {result_short} @ {addr_short} on {date_display}",
        f"hey just finished {record['permit_number']}. {result_short}. {addr_short}. type: {record['structure_type'][:3]}. date {date_display}",
        f"Done w/ inspection\npermit {record['permit_number']}\n{result_short}\n{record['site_address']}\n{date_display}",
    ]
    text = rng.choice(templates)
    if noise > 0:
        words = text.split()
        words = [_typo_word(w, rng) if rng.random() < noise * 0.4 else w for w in words]
        text = " ".join(words)
    if rng.random() < 0.6:
        text += f"\n\nSent from my {rng.choice(['iPhone', 'Galaxy S24', 'Pixel 9', 'phone'])}"
    return text


def _template_data_dump(record: dict, rng: random.Random, noise: float) -> str:
    date_display = _format_date_variant(record["inspection_date"], rng)
    status_display = rng.choice(STATUS_DISPLAY[record["status"]])
    header_sets = [
        ["Permit\tDate\tAddress\tType\tResult\tInspector\tNotes"],
        ["PERMIT_NO\tINSP_DATE\tSITE_ADDR\tSTRUCT_TYPE\tSTATUS\tINSPECTOR\tCOMMENTS"],
    ]
    lines = rng.choice(header_sets)
    lines.append(
        f"{record['permit_number']}\t{date_display}\t{record['site_address']}\t"
        f"{record['structure_type'].title()}\t{status_display}\t"
        f"{record['inspector_name']}\t{record['notes']}"
    )
    extra = rng.randint(0, 5)
    for _ in range(extra):
        e = _generate_record(rng)
        lines.append(
            f"{e['permit_number']}\t{_format_date_variant(e['inspection_date'], rng)}\t"
            f"{e['site_address']}\t{e['structure_type'].title()}\t"
            f"{rng.choice(STATUS_DISPLAY[e['status']])}\t{e['inspector_name']}\t{e['notes']}"
        )
    if rng.random() < 0.5:
        lines.insert(0, f"FYI here is today's batch:")
    text = "\n".join(lines)
    if noise > 0:
        text = _ocr_degrade(text, rng, noise)
    return text


TEMPLATE_GENERATORS = {
    "formal_bureaucratic": _template_formal_bureaucratic,
    "portal_scraping": _template_portal_scraping,
    "forward_chain": _template_forward_chain,
    "minimalist_mobile": _template_minimalist_mobile,
    "data_dump": _template_data_dump,
}


def _apply_structural_variance(text: str, record: dict, rng: random.Random, noise: float) -> str:
    if noise <= 0 or rng.random() > noise * 0.5:
        return text
    permit = record["permit_number"]
    if permit not in text:
        return text
    text = text.replace(permit, "***REDACTED***", 1)
    text += rng.choice([f"\n\nRef: {permit}", f"\n\n[Permit Reference: {permit}]", f"\n\n---\nPermit tracking ID: {permit}"])
    return text


# ── Main Generator ───────────────────────────────────────────────────────────

def generate_messages(count: int, output_dir: Path, seed: int = 42, noise_level: float = 0.2) -> list[dict]:
    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    template_names = list(TEMPLATE_GENERATORS.keys())
    ground_truth: list[dict] = []

    for i in range(count):
        record = _generate_record(rng)
        template_name = rng.choice(template_names)
        text = TEMPLATE_GENERATORS[template_name](record, rng, noise_level)
        text = _apply_structural_variance(text, record, rng, noise_level)

        msg_file = output_dir / f"msg_{i + 1:04d}.txt"
        with open(msg_file, "w") as f:
            f.write(text)

        ground_truth.append({"message_id": f"msg_{i + 1:04d}", "template_type": template_name, **record})

    gt_file = output_dir / "ground_truth.json"
    with open(gt_file, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"✅ Generated {count} synthetic messages in {output_dir}")
    print(f"   Templates: {', '.join(template_names)}")
    print(f"   Noise level: {noise_level}")
    dist = {}
    for gt in ground_truth:
        dist[gt["template_type"]] = dist.get(gt["template_type"], 0) + 1
    for t, c in sorted(dist.items()):
        print(f"   {t}: {c} messages")

    return ground_truth


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic inspector messages")
    parser.add_argument("--count", "-n", type=int, default=500)
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--noise-level", type=float, default=0.2)
    args = parser.parse_args()
    generate_messages(args.count, args.output_dir, args.seed, args.noise_level)


if __name__ == "__main__":
    main()
