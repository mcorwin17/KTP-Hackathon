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
