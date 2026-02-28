#!/usr/bin/env python3
"""
20 "Unbreakable" Edge Cases for SmartRoute — using Agent A's parse_message().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smartroute import parse_message

# ── Edge Case Definitions ────────────────────────────────────────────────────

EDGE_CASES: list[dict] = [
    {
        "id": "EC-01",
        "name": "Two Conflicting Permit Numbers",
        "description": "Email contains two different permit numbers",
        "text": """Subject: Inspection Update

Hi team, regarding permit BP-2026-00200 — actually sorry, I meant CP-2026-00305.
The inspection at 500 River Rd, Springfield, 62704 was completed on 01/20/2026.
Result: Passed. Structure type: Commercial.
Inspector: Tom Wilson""",
        "expected_permits": ["BP-2026-00200", "CP-2026-00305"],
    },
    {
        "id": "EC-02",
        "name": "Completely Empty Email Body",
        "description": "Message has subject line only",
        "text": """Subject: Inspection Complete - Permit #99887\n""",
        "expected_permits": ["99887"],
    },
    {
        "id": "EC-03",
        "name": "Date in the Future / Wrong Year",
        "description": "Date is obviously wrong (year 2099)",
        "text": """Permit BP-2099-00001 approved on 12/31/2099.
Address: 1 Future Blvd, Springfield, 62704
Type: Residential. Result: Pass. Inspector: John Smith""",
    },
    {
        "id": "EC-04",
        "name": "Address Split Between Body and Signature",
        "description": "Real site address in body, office address in signature",
        "text": """The inspection for permit BP-2026-00300 was completed.
Site location is 42 Oak Ave in Shelbyville, zip 62706.
Result: Fail. Needs immediate attention. Structure: Commercial

--
John Smith, Building Inspector
Office: 1 City Hall Sq, Springfield, IL 62704""",
    },
    {
        "id": "EC-05",
        "name": "Permit Number Inside a URL",
        "description": "Permit reference embedded in a hyperlink",
        "text": """Please review the inspection results at:
https://portal.springfield.gov/inspections/view?permit=BP-2026-00456&status=pass

The inspection was completed on 2026-02-01 at 789 Pine Dr, Springfield, 62705.
Type: Residential. Inspector: Maria Chen""",
        "expected_permits": ["BP-2026-00456"],
    },
    {
        "id": "EC-06",
        "name": "Heavy OCR Corruption",
        "description": "Text looks like badly scanned document",
        "text": """Perml7 #8P-2O26-OO5O1
Oate: Ol/25/2O26
Addre55: l23 Ma1n 5t, 5pringfie1d, 627O4
Type: Re5identia1. Re5u1t: Pa55ed. ln5pector: J0hn 5mith""",
    },
    {
        "id": "EC-07",
        "name": "100% Banner / Disclaimer, No Content",
        "description": "Email is entirely legal boilerplate",
        "text": """CONFIDENTIALITY NOTICE: This email and any attachments are intended solely for the use of the individual or entity to whom they are addressed. If you are not the named addressee, you should not disseminate, distribute, or copy this email.

DISCLAIMER: The information contained in this transmission is privileged and confidential.

SECURITY WARNING: This system is for authorized use only.""",
    },
    {
        "id": "EC-08",
        "name": "Tab-separated with Misaligned Columns",
        "description": "Clipboard paste where tabs don't line up",
        "text": """Permit\tDate\tAddress\t\tType\tResult
BP-2026-00600\t\t02/10/2026\t321 Cherry Ln, Capital City\t\tComm\tPass
\tBP-2026-00601\t02/11/2026\t\t445 Elm St, Springfield, 62704\tRes\tFail""",
    },
    {
        "id": "EC-09",
        "name": "Forward Chain 3 Levels Deep",
        "description": "Actual data buried under 3 forward headers",
        "text": """From: admin@springfield.gov
Subject: FW: FW: FW: Urgent Inspection

See below.

---------- Forwarded message ----------
From: supervisor@springfield.gov
Please handle.

---------- Forwarded message ----------
From: dispatch@springfield.gov
Forwarding for action.

---------- Forwarded message ----------
From: sarah.kim@springfield.gov

Inspection done.
Permit: IP-2026-00777
Date: 02/15/2026
Address: 999 Factory Ave, Shelbyville, 62706
Type: Industrial. Result: Failed
Inspector: Sarah Kim
Notes: Major structural concerns.""",
        "expected_permits": ["IP-2026-00777"],
    },
    {
        "id": "EC-10",
        "name": "Non-English Characters Mixed In",
        "description": "Unicode from copy-paste or encoding issues",
        "text": """Permit Nümbér: BP-2026-00888
Inspëction Dàte: 02/20/2026
Síte Addrëss: 555 Maplé Rd, Spríngfïeld, 62704
Strücture Typé: Résidential. Résult: Pàssed. Ínspector: Dïane Crüz""",
        "expected_permits": ["BP-2026-00888"],
    },
    {
        "id": "EC-11",
        "name": "Multiple Dates — Which is Inspection?",
        "description": "Email has scheduled date, inspection date, and follow-up date",
        "text": """Originally scheduled for 01/05/2026.
Inspection for permit BP-2026-00999 was actually conducted on 01/12/2026.
Follow-up inspection required by 02/15/2026.
Address: 100 Cedar Ln, Springfield, 62704
Type: Residential. Result: Partial. Inspector: Tom Wilson""",
    },
    {
        "id": "EC-12",
        "name": "Permit Number in Subject Only",
        "description": "Permit only in email subject, no body reference",
        "text": """Subject: BP-2026-01234 Final Report

The inspection was completed successfully on 02/01/2026.
Address: 200 Birch Way, Shelbyville, 62706
Building type is commercial. All systems passed.
Inspector: Lisa Wang""",
        "expected_permits": ["BP-2026-01234"],
    },
    {
        "id": "EC-13",
        "name": "Result Contradiction",
        "description": "Says 'passed' but mentions 'violations found'",
        "text": """Permit: BP-2026-01500
Date: 02/05/2026
Address: 300 Walnut St, Capital City, 62707
Type: Residential. Result: Passed

Note: While recorded as passed, several minor violations were found
that should be addressed before final occupancy.""",
    },
    {
        "id": "EC-14",
        "name": "Extremely Long Email with Data at End",
        "description": "200+ words of irrelevant discussion before data",
        "text": """Hi everyone,

I wanted to touch base about the quarterly review meeting. As discussed, we need to finalize the budget allocations for the next fiscal year. The facilities team has submitted proposals and we should review them before the March deadline.

Also, regarding the company picnic — we've booked the park for June 15th. Please RSVP by May 1st.

On another note, the IT department mentioned they'll be doing server maintenance next Thursday. Please save all your work before 5 PM.

Speaking of maintenance, the break room refrigerator needs to be cleaned out.

Now, regarding the actual inspection result:

Permit: CP-2026-01600
Date: 02/08/2026
Address: 400 Business Pkwy, Capital City, 62707
Type: Commercial. Result: Failed
Inspector: Ryan Taylor
Notes: Fire suppression system not up to code.""",
        "expected_permits": ["CP-2026-01600"],
    },
    {
        "id": "EC-15",
        "name": "All Caps Email",
        "description": "Entire email in uppercase",
        "text": """PERMIT NUMBER BP-2026-01700
INSPECTION DATE 02/10/2026
SITE ADDRESS 500 MAGNOLIA BLVD SPRINGFIELD 62704
STRUCTURE TYPE RESIDENTIAL
INSPECTION RESULT PASSED
INSPECTOR NAME STEPHANIE ADAMS
NOTES FINAL INSPECTION ALL CLEAR""",
        "expected_permits": ["BP-2026-01700"],
    },
    {
        "id": "EC-16",
        "name": "JSON-like Data in Email",
        "description": "Someone pasted JSON into the email",
        "text": """Here are the results:

{"permit_number": "BP-2026-01800", "date": "02/12/2026", "address": "600 Sycamore Dr, Shelbyville, 62706", "type": "Industrial", "result": "Fail", "inspector": "Brian Hall"}

Please process ASAP.""",
        "expected_permits": ["BP-2026-01800"],
    },
    {
        "id": "EC-17",
        "name": "Raw Number Permit (No Prefix/Dashes)",
        "description": "Just a raw number as permit reference",
        "text": """inspection complete for permit 55234
date 2/14/26
address 700 poplar ct springfield 62705
residential pass
inspector amy johnson""",
        "expected_permits": ["55234"],
    },
    {
        "id": "EC-18",
        "name": "Spanish-Language Report",
        "description": "Report partially in Spanish",
        "text": """Informe de Inspección

Número de Permiso: BP-2026-01900
Fecha: 14/02/2026
Dirección: 800 Juniper Way, Capital City, 62707
Tipo de Estructura: Comercial. Resultado: Aprobado
Inspector: Eric Martinez""",
        "expected_permits": ["BP-2026-01900"],
    },
    {
        "id": "EC-19",
        "name": "Typo in Permit Prefix",
        "description": "Typo in the permit prefix (BOP instead of BP)",
        "text": """Prmt BOP-2026-02000 done
date: 02/15/2026
addr: 900 Dogwood Dr, Springfield, 62704
type: res. result: pass. insp: Kevin Nguyen""",
        "expected_permits": ["BOP-2026-02000", "2026-02000"],
    },
    {
        "id": "EC-20",
        "name": "Mixed Newlines and Formatting Chaos",
        "description": "CR/LF chaos, random whitespace",
        "text": "Permit:   BP-2026-02100   \r\n  Date:    02/16/2026\r\n\n    Address:  1000 Beech Ave,  Springfield,   62704   \n\rType : Residential\r\n\n\nResult:Passed\r\nInspector:   Diane   Cruz   \r\n\r\n",
        "expected_permits": ["BP-2026-02100"],
    },
]


# ── Runner ───────────────────────────────────────────────────────────────────


def run_edge_cases() -> list[dict]:
    results = []
    for case in EDGE_CASES:
        record = parse_message(case["text"])

        # Extract key fields
        permit = record.permit.permit_number
        status = record.inspection.status.value
        confidence = record.quality.confidence_overall
        team = record.operational.route_to_team.value
        action = record.operational.action_required

        result = {
            "id": case["id"],
            "name": case["name"],
            "description": case["description"],
            "extracted_permit": permit,
            "extracted_status": status,
            "confidence": confidence,
            "route_team": team,
            "action_required": action,
        }

        # Check permit
        checks = []
        if case.get("expected_permits"):
            permit_hit = any(exp in permit for exp in case["expected_permits"])
            checks.append(("permit_found", permit_hit))

        result["checks"] = checks
        result["all_passed"] = all(v for _, v in checks) if checks else None
        results.append(result)

    return results


def print_edge_case_report(results: list[dict]) -> None:
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="Edge Case Results", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Name", style="white", width=40)
    table.add_column("Permit", justify="center", width=12)
    table.add_column("Confidence", justify="right", width=10)
    table.add_column("Route", style="dim", width=18)

    passed = 0
    total = 0

    for r in results:
        permit_status = "—"
        for cn, cv in r.get("checks", []):
            if cn == "permit_found":
                permit_status = "[green]✅[/green]" if cv else "[red]❌[/red]"
                total += 1
                if cv:
                    passed += 1

        conf = r["confidence"]
        cc = "green" if conf >= 0.7 else "yellow" if conf >= 0.4 else "red"
        table.add_row(r["id"], r["name"], permit_status, f"[{cc}]{conf*100:.0f}%[/{cc}]", r["route_team"])

    console.print(table)
    if total > 0:
        console.print(f"\n[bold]Permit Detection: {passed}/{total} ({passed/total*100:.0f}%)[/bold]")


def save_edge_case_report(results: list[dict], output_path: Path) -> None:
    lines = [
        "", "---", "",
        "## Edge-Case Test Results (20 Manual Cases)", "",
        "| ID | Name | Permit | Confidence | Route |",
        "|----|------|--------|------------|-------|",
    ]
    for r in results:
        permit_ok = "—"
        for cn, cv in r.get("checks", []):
            if cn == "permit_found":
                permit_ok = "✅" if cv else "❌"
        lines.append(f"| {r['id']} | {r['name']} | {permit_ok} | {r['confidence']*100:.0f}% | {r['route_team']} |")

    lines.extend(["", "### Detailed Edge Case Results", ""])
    for r in results:
        lines.append(f"**{r['id']}: {r['name']}** — {r['description']}")
        lines.append(f"- Extracted permit: `{r['extracted_permit']}`")
        lines.append(f"- Status: `{r['extracted_status']}` | Confidence: {r['confidence']*100:.0f}%")
        lines.append(f"- Routed to: `{r['route_team']}` | Action: {'Yes' if r['action_required'] else 'No'}")
        lines.append("")

    if output_path.exists():
        with open(output_path, "a") as f:
            f.write("\n".join(lines))
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write("# Edge Case Report\n\n" + "\n".join(lines))
    print(f"✅ Edge case results appended to {output_path}")


if __name__ == "__main__":
    results = run_edge_cases()
    print_edge_case_report(results)

    report_path = Path("eval/report.md")
    save_edge_case_report(results, report_path)

    json_path = Path("eval/edge_cases.json")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✅ Raw results saved to {json_path}")
