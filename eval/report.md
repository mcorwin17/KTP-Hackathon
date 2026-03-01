# SmartRoute Evaluation Report

**Total messages evaluated:** 500
**Generated:** 2026-03-01 02:01:51

---

## Aggregate Metrics

| Metric | Score |
|--------|-------|
| Permit # (Exact Match) | 91.8% |
| Inspection Date (Exact Match) | 74.8% |
| Site Address (Fuzzy Match avg) | 87.0% |
| Status (Exact Match) | 97.2% |
| Structure Type (Fuzzy Match) | 85.8% |
| Routing Action Accuracy | 63.4% |
| Average Confidence | 92.1% |

---

## Per-Template Breakdown

| Template | Count | Permit EM | Date EM | Address FM | Status EM |
|----------|-------|-----------|---------|------------|-----------|
| data_dump | 92 | 91.3% | 96.7% | 99.6% | 98.9% |
| formal_bureaucratic | 97 | 94.8% | 86.6% | 95.2% | 97.9% |
| forward_chain | 106 | 98.1% | 80.2% | 97.0% | 98.1% |
| minimalist_mobile | 102 | 76.5% | 48.0% | 44.5% | 92.2% |
| portal_scraping | 103 | 98.1% | 65.0% | 99.7% | 99.0% |

---

## Worst 10 Messages

### msg_0386 (template: minimalist_mobile)

- **Permit**: `0226-37485` vs `BP-2026-37485` — EM: 0.0
- **Date**: `` vs `2025-06-30` — EM: 0.0
- **Address**: FM score 0.156
- **Status**: `unknown` vs `partial`
- **Routing**: action ❌

### msg_0071 (template: minimalist_mobile)

- **Permit**: `2026-08277` vs `BP-2026-08277` — EM: 0.0
- **Date**: `` vs `2025-12-13` — EM: 0.0
- **Address**: FM score 0.114
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0160 (template: minimalist_mobile)

- **Permit**: `2026-98362` vs `EP-2026-98362` — EM: 0.0
- **Date**: `` vs `2025-11-10` — EM: 0.0
- **Address**: FM score 0.121
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0389 (template: minimalist_mobile)

- **Permit**: `2025-94243` vs `EP-2025-94243` — EM: 0.0
- **Date**: `` vs `2026-04-09` — EM: 0.0
- **Address**: FM score 0.128
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0308 (template: minimalist_mobile)

- **Permit**: `2026-96446` vs `EP-2026-96446` — EM: 0.0
- **Date**: `` vs `2026-04-26` — EM: 0.0
- **Address**: FM score 0.182
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0120 (template: minimalist_mobile)

- **Permit**: `2026-22345` vs `MP-2026-22345` — EM: 0.0
- **Date**: `` vs `2025-10-30` — EM: 0.0
- **Address**: FM score 0.206
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0229 (template: minimalist_mobile)

- **Permit**: `2026-98721` vs `IP-2026-98721` — EM: 0.0
- **Date**: `` vs `2025-10-16` — EM: 0.0
- **Address**: FM score 0.270
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0428 (template: minimalist_mobile)

- **Permit**: `2026-43165` vs `CP-2026-43165` — EM: 0.0
- **Date**: `` vs `2026-05-04` — EM: 0.0
- **Address**: FM score 0.286
- **Status**: `partial` vs `partial`
- **Routing**: action ❌

### msg_0426 (template: minimalist_mobile)

- **Permit**: `2026-84997` vs `MP-2026-84997` — EM: 0.0
- **Date**: `` vs `2026-01-05` — EM: 0.0
- **Address**: FM score 0.000
- **Status**: `pass` vs `pass`
- **Routing**: action ✅

### msg_0388 (template: minimalist_mobile)

- **Permit**: `2025-06957` vs `BP-2025-06957` — EM: 0.0
- **Date**: `` vs `2026-05-04` — EM: 0.0
- **Address**: FM score 0.121
- **Status**: `pass` vs `pass`
- **Routing**: action ✅

---

## Edge-Case Test Results (20 Manual Cases)

| ID | Name | Permit | Confidence | Route |
|----|------|--------|------------|-------|
| EC-01 | Two Conflicting Permit Numbers | ✅ | 99% | PERMITTING |
| EC-02 | Completely Empty Email Body | ❌ | 0% | UNKNOWN |
| EC-03 | Date in the Future / Wrong Year | — | 96% | PERMITTING |
| EC-04 | Address Split Between Body and Signature | — | 90% | FIELD_DISPATCH |
| EC-05 | Permit Number Inside a URL | ✅ | 99% | PERMITTING |
| EC-06 | Heavy OCR Corruption | — | 31% | UNKNOWN |
| EC-07 | 100% Banner / Disclaimer, No Content | — | 0% | UNKNOWN |
| EC-08 | Tab-separated with Misaligned Columns | — | 53% | UNKNOWN |
| EC-09 | Forward Chain 3 Levels Deep | ✅ | 99% | FIELD_DISPATCH |
| EC-10 | Non-English Characters Mixed In | ✅ | 70% | UNKNOWN |
| EC-11 | Multiple Dates — Which is Inspection? | — | 99% | UNKNOWN |
| EC-12 | Permit Number in Subject Only | ❌ | 94% | PERMITTING |
| EC-13 | Result Contradiction | — | 93% | PERMITTING |
| EC-14 | Extremely Long Email with Data at End | ✅ | 99% | FIELD_DISPATCH |
| EC-15 | All Caps Email | ✅ | 99% | PERMITTING |
| EC-16 | JSON-like Data in Email | ✅ | 80% | UNKNOWN |
| EC-17 | Raw Number Permit (No Prefix/Dashes) | ✅ | 93% | PERMITTING |
| EC-18 | Spanish-Language Report | ✅ | 91% | UNKNOWN |
| EC-19 | Typo in Permit Prefix | ✅ | 90% | PERMITTING |
| EC-20 | Mixed Newlines and Formatting Chaos | ✅ | 99% | PERMITTING |

### Detailed Edge Case Results

**EC-01: Two Conflicting Permit Numbers** — Email contains two different permit numbers
- Extracted permit: `BP-2026-00200`
- Status: `pass` | Confidence: 99%
- Routed to: `PERMITTING` | Action: No

**EC-02: Completely Empty Email Body** — Message has subject line only
- Extracted permit: ``
- Status: `unknown` | Confidence: 0%
- Routed to: `UNKNOWN` | Action: No

**EC-03: Date in the Future / Wrong Year** — Date is obviously wrong (year 2099)
- Extracted permit: `BP-2099-00001`
- Status: `pass` | Confidence: 96%
- Routed to: `PERMITTING` | Action: No

**EC-04: Address Split Between Body and Signature** — Real site address in body, office address in signature
- Extracted permit: `BP-2026-00300`
- Status: `fail` | Confidence: 90%
- Routed to: `FIELD_DISPATCH` | Action: Yes

**EC-05: Permit Number Inside a URL** — Permit reference embedded in a hyperlink
- Extracted permit: `BP-2026-00456`
- Status: `pass` | Confidence: 99%
- Routed to: `PERMITTING` | Action: No

**EC-06: Heavy OCR Corruption** — Text looks like badly scanned document
- Extracted permit: ``
- Status: `unknown` | Confidence: 31%
- Routed to: `UNKNOWN` | Action: No

**EC-07: 100% Banner / Disclaimer, No Content** — Email is entirely legal boilerplate
- Extracted permit: ``
- Status: `unknown` | Confidence: 0%
- Routed to: `UNKNOWN` | Action: No

**EC-08: Tab-separated with Misaligned Columns** — Clipboard paste where tabs don't line up
- Extracted permit: `BP-2026-00600`
- Status: `unknown` | Confidence: 53%
- Routed to: `UNKNOWN` | Action: Yes

**EC-09: Forward Chain 3 Levels Deep** — Actual data buried under 3 forward headers
- Extracted permit: `IP-2026-00777`
- Status: `fail` | Confidence: 99%
- Routed to: `FIELD_DISPATCH` | Action: Yes

**EC-10: Non-English Characters Mixed In** — Unicode from copy-paste or encoding issues
- Extracted permit: `BP-2026-00888`
- Status: `unknown` | Confidence: 70%
- Routed to: `UNKNOWN` | Action: No

**EC-11: Multiple Dates — Which is Inspection?** — Email has scheduled date, inspection date, and follow-up date
- Extracted permit: `BP-2026-00999`
- Status: `partial` | Confidence: 99%
- Routed to: `UNKNOWN` | Action: Yes

**EC-12: Permit Number in Subject Only** — Permit only in email subject, no body reference
- Extracted permit: ``
- Status: `pass` | Confidence: 94%
- Routed to: `PERMITTING` | Action: No

**EC-13: Result Contradiction** — Says 'passed' but mentions 'violations found'
- Extracted permit: `BP-2026-01500`
- Status: `pass` | Confidence: 93%
- Routed to: `PERMITTING` | Action: Yes

**EC-14: Extremely Long Email with Data at End** — 200+ words of irrelevant discussion before data
- Extracted permit: `CP-2026-01600`
- Status: `fail` | Confidence: 99%
- Routed to: `FIELD_DISPATCH` | Action: Yes

**EC-15: All Caps Email** — Entire email in uppercase
- Extracted permit: `BP-2026-01700`
- Status: `pass` | Confidence: 99%
- Routed to: `PERMITTING` | Action: No

**EC-16: JSON-like Data in Email** — Someone pasted JSON into the email
- Extracted permit: `BP-2026-01800`
- Status: `unknown` | Confidence: 80%
- Routed to: `UNKNOWN` | Action: Yes

**EC-17: Raw Number Permit (No Prefix/Dashes)** — Just a raw number as permit reference
- Extracted permit: `55234`
- Status: `pass` | Confidence: 93%
- Routed to: `PERMITTING` | Action: No

**EC-18: Spanish-Language Report** — Report partially in Spanish
- Extracted permit: `BP-2026-01900`
- Status: `unknown` | Confidence: 91%
- Routed to: `UNKNOWN` | Action: No

**EC-19: Typo in Permit Prefix** — Typo in the permit prefix (BOP instead of BP)
- Extracted permit: `BOP-2026-02000`
- Status: `pass` | Confidence: 90%
- Routed to: `PERMITTING` | Action: No

**EC-20: Mixed Newlines and Formatting Chaos** — CR/LF chaos, random whitespace
- Extracted permit: `BP-2026-02100`
- Status: `pass` | Confidence: 99%
- Routed to: `PERMITTING` | Action: No
