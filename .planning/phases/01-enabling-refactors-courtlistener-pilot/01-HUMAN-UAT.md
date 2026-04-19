---
status: partial
phase: 01-enabling-refactors-courtlistener-pilot
source: [01-VERIFICATION.md]
started: 2026-04-19T01:49:00Z
updated: 2026-04-19T01:49:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Confirm the CourtListener pilot report reflects a real live-API run
expected: User confirms `results/court/pilot_report.txt` was generated against live `www.courtlistener.com` (not replayed from a local mock), with 200 actual HTTP requests issued using the .env token. All 4 endpoints show ≥70% success with no 403s.
result: [pending]

### 2. Visually inspect results/congress/figures/*.pdf for sensible shapes
expected: `mrc.pdf` shows miss-ratio curves monotonically decreasing with cache size for all 5 policies; `alpha_sensitivity.pdf` shows LRU/FIFO/CLOCK degrading at low alpha; `workload.pdf` shows a log-normal-ish size distribution.
result: [pending]

### 3. Confirm `make plots` works end-to-end on the user's machine
expected: `make plots` exits 0 and regenerates `results/congress/figures/*.pdf`; or, if libexpat workaround is needed, user confirms `.venv` activation + `DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib` produces the PDFs.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
