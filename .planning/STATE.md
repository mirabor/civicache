---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: "Phase 02 Plan 05 complete — scripts/plot_results.py POLICY_COLORS['W-TinyLFU']=#8c564b (tab:brown), POLICY_MARKERS['W-TinyLFU']='P' (filled plus) at b089209; +2 lines, all 6 values unique per dict (T-02-05-01 mitigated); Rule 3 hygiene added __pycache__/ + *.pyc to .gitignore; make plots regression -> 6 PDFs generated, no crash; next 02-06 validation sweep on Congress trace"
last_updated: "2026-04-19T04:07:05Z"
last_activity: "2026-04-19 -- Phase 02 Plan 05 complete (scripts/plot_results.py W-TinyLFU color/marker entries; WTLFU-02 plot-render support satisfied)"
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 12
  completed_plans: 11
  percent: 92
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** A defensible, well-analyzed comparison of cache eviction policies on real legislative + judicial API workloads, delivered as a submission-ready paper + code + AI-use report + live demo.
**Current focus:** Phase 02 — W-TinyLFU Core

## Current Position

Phase: 02 (W-TinyLFU Core) — EXECUTING
Plan: 6 of 6 (next: 02-06 validation sweep on Congress trace + scripts/check_wtlfu_acceptance.py)
Status: Executing Phase 02 — Plans 01 + 02 + 03 + 04 + 05 complete
Last activity: 2026-04-19 -- Phase 02 Plan 05 complete (scripts/plot_results.py POLICY_COLORS + POLICY_MARKERS gain W-TinyLFU -> #8c564b / P; all 6 values unique per dict; make plots regression clean)

Progress: [█████████▓] 92% (1 of 6 phases, 11 of 12 plans)

## Performance Metrics

**Velocity:**

- Total plans completed: 6
- Average duration: ~3-5 min per autonomous plan (worktree-parallel)
- Total execution time: ~45 min wall-clock for Phase 1 (gated on user CourtListener registration)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1     | 6     | ~45m  | ~3-8m    |
| 2     | 1/6   | ~7m   | 7m       |

**Recent Trend:**

- Last 5 plans: 01-02 (2m45s), 01-06 (5m live pilot), 01-03 (3m), 01-04 (6m), 02-01 (~7m Caffeine pre-work)
- Trend: Stable — autonomous plans 2-7 min, human-gated plans limited by user turnaround

*Updated after each plan completion*
| Phase 02 P02 | 2m | 1 tasks | 1 files |
| Phase 02 P03 | 18m | 3 tasks | 3 files |
| Phase 02 P04 | 3m 20s | 2 tasks | 2 files |
| Phase 02 P05 | 2m | 1 tasks | 2 files |

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
- **Phase 02 Plan 01 (Caffeine pre-work):** Caffeine v3.1.8 confirmed to use STANDARD update in `FrequencySketch.increment` (FrequencySketch.java:L161-L164); our port DELIBERATELY uses CONSERVATIVE per WTLFU-01. 6 deliberate deviations documented in `.planning/phases/02-w-tinylfu-core/02-01-CAFFEINE-NOTES.md` §6. Plans 02-02 + 02-03 unblocked.
- [Phase 02]: Plan 02-02 (CMS): CONSERVATIVE update locked by WTLFU-01 — deliberately deviates from Caffeine's STANDARD update (FrequencySketch.java:L161-L164); sample_size = 10*width*depth = 40*width (4× slower halving than Caffeine's 10*maxSize); halving mask 0x77 ensures nibble-independent shift
- [Phase 02]: Plan 02-03 (W-TinyLFU header + integration): byte-bounded regions (D-01) — 1% window / 99% main / 80% protected inside main; stats single-source (L-12) enforced by grep-countable record(true|false)==4; D-08a explicit empty-probation short-circuit kept per CONTEXT.md (CAFFEINE-NOTES §6 row 4 deviation from Caffeine's protected/window victim-escalation); D-08e strict `>` reject-on-tie without Caffeine's 1/128 hash-DoS random admit (no adversarial threat model; preserves determinism for D-05); dropped unused total_capacity_ / probation_capacity_ members to pass -Wunused-private-field build-clean gate; make_policy widened to (name, capacity, n_objects_hint) with (void) ignore-pattern for non-wtinylfu branches
- [Phase 02]: Plan 02-04 (test binary + make test): CMS basics uses N=10 (below 4-bit COUNTER_MAX=15) for exact CONSERVATIVE-update estimate reads at width>=1024; aging test uses BOTH force_age() (deterministic D-10 hook) AND sample_size+10 burst (natural auto-halve path, asserts sample_count()==10 exactly); WTLFU-04 literal sizing cap_bytes=20000/obj_size=100/n_obj_hint=200 yields ~200-resident cache overflowed 5x by 1000-key scan; TEST_ASSERT accumulates failures (not abort-on-first) so one `make test` surfaces every broken invariant; build/test/ separate object dir (D-07) — `make && make test` does not invalidate main cache_sim
- [Phase 02]: Plan 02-05 (plot_results W-TinyLFU entry): POLICY_COLORS['W-TinyLFU']=#8c564b (matplotlib tab:brown, the 6th tab10 color) — deliberately NOT CONTEXT.md's suggested purple #9467bd because SIEVE owns it; POLICY_MARKERS['W-TinyLFU']='P' (filled plus) — deliberately NOT CONTEXT.md's suggested 'D' because S3-FIFO owns it; both deviations avoid T-02-05-01 "visual confusion" collision; dict key is exact CSV policy string 'W-TinyLFU' emitted by wtinylfu.h::name() (not 'wtinylfu' CLI arg); no plot-function edits because existing loops at lines 79/113/150 use .get(policy, fallback); `make plots` on existing Congress CSVs regenerates 6 PDFs (no W-TinyLFU legend entry yet because Phase 1 CSVs predate the policy — 02-06 will fix); Rule 3 hygiene added __pycache__/ + *.pyc to .gitignore since import smoke test creates scripts/__pycache__/

### Pending Todos

None yet.

### Blockers/Concerns

Phase 1 risks resolved:

- C1/C2/C3 CLEARED: CourtListener token verified via live curl; all 4 endpoints (/dockets/, /opinions/, /clusters/, /courts/) returned 200 with zero 403s and zero 429s during the 200-request pilot (90%/74%/90%/100% success rates).

Open items for Phase 2:

- C6: W-TinyLFU must mirror Caffeine `WindowTinyLfuPolicy` line-by-line, not paraphrase the paper — REFERENCE LOCKED 2026-04-19 in `.planning/phases/02-w-tinylfu-core/02-01-CAFFEINE-NOTES.md` (Plan 02-01 complete; Caffeine v3.1.8 source pinned)
- ~~Pre-work verification: pull Caffeine `FrequencySketch.java` and confirm `sampleSize = 10×max(capacity,1)` before locking CMS constants~~ DONE — Caffeine confirmed `sampleSize = 10 * maximumSize` (FrequencySketch.java:L96); our port deliberately uses `10 * width * depth` per CONTEXT.md L-5 (deviation §6 row 2)

Phase 1 human-UAT items (non-blocking, deferred to post-merge):

- HUMAN-UAT: Visual sanity of `results/congress/figures/*.pdf` pending
- HUMAN-UAT: `make plots` end-to-end on user's machine (libexpat/DYLD workaround)
- Stale CSVs in `results/congress/` (alpha_sensitivity.csv, shards_mrc.csv pre-refactor) — regenerate via `make run-sweep` before Phase 2 consumes them

## Deferred Items

Items deferred to v2 (from REQUIREMENTS.md):

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Validation | V2-01: Caffeine trace cross-validation (±2% agreement) | Deferred to v2 | Milestone 2 planning |
| Policy | V2-02: LHD or AdaptSize as 7th policy | Deferred to v2 | Milestone 2 planning |
| Trace | V2-03: Third trace domain (SEC EDGAR) | Deferred to v2 | Milestone 2 planning |

## Session Continuity

Last session: 2026-04-19T04:07:05Z
Stopped at: Phase 02 Plan 05 complete — scripts/plot_results.py POLICY_COLORS['W-TinyLFU']=#8c564b (tab:brown), POLICY_MARKERS['W-TinyLFU']='P' (filled plus) at b089209; +2 lines to scripts/plot_results.py, +4 lines to .gitignore (Rule 3 __pycache__/+*.pyc); all 6 values unique per dict (T-02-05-01 mitigated); `make plots` regression -> 6 PDFs, no crash; WTLFU-02 plot-render support satisfied (W-TinyLFU will render automatically once 02-06 regenerates CSVs with the 6-policy sweep)
Resume: execute Plan 02-06 (validation sweep on Congress trace via `make run-sweep` with --policies lru,fifo,clock,s3fifo,sieve,wtinylfu + scripts/check_wtlfu_acceptance.py for α-regime gates — Wave 5 autonomous, WTLFU-05; this plan regenerates MRC / byte_mrc / alpha_sensitivity CSVs so plot_results picks up W-TinyLFU rows)
