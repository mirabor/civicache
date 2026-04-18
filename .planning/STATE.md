# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** A defensible, well-analyzed comparison of cache eviction policies on real legislative + judicial API workloads, delivered as a submission-ready paper + code + AI-use report + live demo.
**Current focus:** Phase 1 — Enabling Refactors & CourtListener Pilot

## Current Position

Phase: 1 of 6 (Enabling Refactors & CourtListener Pilot)
Plan: Not yet planned
Status: Ready to plan
Last activity: 2026-04-18 — Milestone 2 roadmap created, 29 v1 requirements mapped across 6 phases

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: N/A
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: N/A
- Trend: N/A (no plans executed yet this milestone)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table and research/SUMMARY.md.
Recent decisions affecting current work (from research phase):

- Court API locked to CourtListener REST v4 (not PACER) — free, token-auth, 5k/hr
- W-TinyLFU implemented header-only C++17 with roll-your-own CMS — no external deps
- Doorkeeper kept as optional ablation (first-cut omits; added in Phase 4)
- SHARDS 1M validation via self-convergence (no exact oracle at 1M scale)
- `std::hash` banned — FNV-1a extracted to `include/hash_util.h` with 4 seeds
- Hill-climbing W-TinyLFU explicitly omitted (static 1%/99% config)
- Writeup budget ≥1 week; demo last, tested 3+ times on target laptop

### Pending Todos

None yet.

### Blockers/Concerns

Pre-Phase-1 risks flagged by research (address during Phase 1 execution):

- C1/C2/C3: CourtListener token must be verified via single curl call before any 20K run; test each of 4 planned endpoints unauthenticated-to-confirm-not-gated
- C6: W-TinyLFU will be implemented in Phase 2 — mirror Caffeine `WindowTinyLfuPolicy` line-by-line, not paraphrase the paper
- Pre-work verification: pull Caffeine `FrequencySketch.java` and confirm `sampleSize = 10×max(capacity,1)` before locking CMS constants

## Deferred Items

Items deferred to v2 (from REQUIREMENTS.md):

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Validation | V2-01: Caffeine trace cross-validation (±2% agreement) | Deferred to v2 | Milestone 2 planning |
| Policy | V2-02: LHD or AdaptSize as 7th policy | Deferred to v2 | Milestone 2 planning |
| Trace | V2-03: Third trace domain (SEC EDGAR) | Deferred to v2 | Milestone 2 planning |

## Session Continuity

Last session: 2026-04-18
Stopped at: ROADMAP.md and STATE.md written; Phase 1 ready to plan
Resume file: None (run `/gsd-plan-phase 1` to begin)
