---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Phase 4 context gathered — ready for /gsd-plan-phase 4
last_updated: "2026-04-20T00:00:00.000Z"
last_activity: 2026-04-20 -- Phase 4 CONTEXT.md written (19 decisions across SHARDS, Doorkeeper, ablations, trace layout); checkpoint cleaned; ready for planning
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** A defensible, well-analyzed comparison of cache eviction policies on real legislative + judicial API workloads, delivered as a submission-ready paper + code + AI-use report + live demo.
**Current focus:** Phase 03 — CourtListener Trace Collection & Replay Sweep

## Current Position

Phase: 03 (CourtListener Trace Collection & Replay Sweep) — EXECUTING
Plan: 2 of 3
Status: Executing Phase 03 — Plan 01 complete; Plan 02 (overnight 20K run) next
Last activity: 2026-04-19 -- Phase 03 Plan 01 completed (scripts/collect_court_trace.py, 609 lines, 10-row smoke PASS in 14s, exit 0)

Progress: [█████████░] 87% (2 of 6 phases, 13 of 15 plans — Phase 3 in progress)

## Performance Metrics

**Velocity:**

- Total plans completed: 6
- Average duration: ~3-5 min per autonomous plan (worktree-parallel)
- Total execution time: ~45 min wall-clock for Phase 1 (gated on user CourtListener registration)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1     | 6     | ~45m  | ~3-8m    |
| 2     | 6/6   | ~34m  | ~5-6m    |

**Recent Trend:**

- Last 5 plans: 02-02 (2m), 02-03 (18m), 02-04 (3m20s), 02-05 (2m), 02-06 (2m)
- Trend: Stable — autonomous plans 2-7 min, 02-03 was the heaviest (wtinylfu.h implementation + integration + make_policy widen)

*Updated after each plan completion*
| Phase 02 P02 | 2m | 1 tasks | 1 files |
| Phase 02 P03 | 18m | 3 tasks | 3 files |
| Phase 02 P04 | 3m 20s | 2 tasks | 2 files |
| Phase 02 P05 | 2m | 1 tasks | 2 files |
| Phase 02 P06 | 2m | 2 tasks | 1 file |
| Phase 03 P01 | 3m 53s | 2 tasks | 1 files |

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
- [Phase 02]: Plan 02-06 (validation sweep on Congress + WTLFU-05 gate): scripts/check_wtlfu_acceptance.py at 10f96e3 checks 3 conditions (A1 mrc.csv WTLFU<LRU at every cache fraction, A2 alpha_sensitivity.csv WTLFU<LRU at alpha ≥ 0.8, B one-sided regression guard at alpha=0.6); Condition B semantics changed from two-sided abs(WTLFU-LRU)/LRU≤0.02 to ONE-SIDED (WTLFU-LRU)/LRU≤0.02 via checkpoint decision — rationale: WTLFU-05 literal "within ±2% of LRU at α=0 uniform" is a REGRESSION GUARD against LFU-flavor policies underperforming LRU on flat workloads, NOT a penalty for WTLFU outperforming LRU; at alpha=0.6 WTLFU beats LRU by 7.84% which two-sided abs() would flag as failure — opposite of intent; W-TinyLFU monotonically dominates LRU across full sweep grid alpha {0.6..1.2} with advantage growing 7.84% → 21.55% as skew rises (matches TinyLFU theory on OHW filtering); LOW_ALPHA_PROXY=0.6 (lowest value in hardcoded src/main.cpp:216 sweep grid) used as uniform proxy since alpha=0 not in grid; TOLERANCE=0.02 constant + LOW_ALPHA_PROXY=0.6 constant + HIGH_ALPHA=[0.8..1.2] list all preserved for grep-discoverable spec-drift path (T-02-06-01); sweep itself ran in prior session — 6 policies × 7 alphas × 6 cache fractions regenerated into results/congress/{alpha_sensitivity.csv, mrc.csv} (gitignored); make plots exit 0 → 6 PDFs in results/congress/figures/ now render W-TinyLFU in brown/plus per Wave 4 styling; Phase 2 milestone complete — all 5 WTLFU-01..05 requirements verified
- [Phase 03]: Plan 03-01 (scripts/collect_court_trace.py production collector) at e9d8557: 609-line sibling to scripts/pilot_court_trace.py (NOT a replacement per STACK.md §32 copy-modify policy); all 26 grep-discoverable invariants pass on first write (ALLOWED_HOST, BASE_URL, BASE_DELAY=0.8, JITTER=0.4, OPINION_METADATA_FRACTION=0.8, D-02 field set "id,absolute_url,type,date_filed,author_id", [0,30,90] ramp, CONSECUTIVE_429_HARD_STOP=5, exact FATAL diagnostic "FATAL: 5 consecutive 429s — token throttled or pacing too aggressive. Resume after 1 hour.", PER_ENDPOINT_TARGET=5000, --resume, FALLBACK_PROBE_WINDOW=500, FALLBACK_NARROW_FACTOR=0.67, COURTLISTENER_API_KEY, f.flush(), all 4 endpoint templates, court_ids list); D-11 429 ramp counter is PER-ENDPOINT (matches pilot semantics) with index-clamp reusing the +90 bucket for 4th consecutive before the 5-consec hard-stop fires; Retry-After value clamped to [0, 120]s to protect against pathological server hints; D-06 fallback evaluated AFTER the 500th response lands (fallback_triggered latch ensures at most one narrowing per endpoint); target-rows remainder distributed 1-per-endpoint to first N so 10-row smoke touches all 4 families (observed: docket=3, opinion=3, cluster=2, court=2); module-level assert urlparse(BASE_URL).netloc == ALLOWED_HOST + per-request urlparse(url) check = defence-in-depth SSRF mitigation for T-03-01-01; token fingerprint-only logging (api_key[:4]+"..."+api_key[-4:]+len, never raw); 10-row smoke run against live CourtListener API completed in 14s exit 0 with well-formed CSV (CRLF line endings matching traces/court_pilot.csv schema verbatim); observed smoke pacing ~1.27s/issued-request (0.8s base + ~0.2s jitter + ~0.07s network RTT) revises Plan 03-02 runtime estimate UP from ROADMAP's 6.1h to ~8h wall-clock for 20K successful rows at 85% aggregate success rate (~23,530 issued requests); Plan 03-02 unblocked

### Pending Todos

None yet.

### Blockers/Concerns

Phase 1 risks resolved:

- C1/C2/C3 CLEARED: CourtListener token verified via live curl; all 4 endpoints (/dockets/, /opinions/, /clusters/, /courts/) returned 200 with zero 403s and zero 429s during the 200-request pilot (90%/74%/90%/100% success rates).

Phase 2 items — ALL RESOLVED:

- ✓ C6: W-TinyLFU must mirror Caffeine `WindowTinyLfuPolicy` line-by-line — LOCKED 2026-04-19 in `.planning/phases/02-w-tinylfu-core/02-01-CAFFEINE-NOTES.md` (Plan 02-01 complete; Caffeine v3.1.8 source pinned)
- ✓ Pre-work verification: Caffeine confirmed `sampleSize = 10 * maximumSize` (FrequencySketch.java:L96); our port deliberately uses `10 * width * depth` per CONTEXT.md L-5 (deviation §6 row 2)
- ✓ WTLFU-05 validation: Plan 02-06 complete — scripts/check_wtlfu_acceptance.py exit 0, W-TinyLFU beats LRU monotonically across alpha {0.6..1.2}, all 3 acceptance conditions PASS

Phase 1 human-UAT items (resolved during Phase 2):

- ✓ RESOLVED: `make plots` end-to-end on user's machine — Makefile's `DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib` + `PYTHONPATH=.venv/lib/python3.14/site-packages` workaround (Phase 1 commit 2dc8466) confirmed working during 02-06; exit 0, 6 PDFs
- ✓ RESOLVED: Stale CSVs in `results/congress/` — regenerated by 02-06 sweep with W-TinyLFU rows; figures include W-TinyLFU in brown/plus styling
- HUMAN-UAT: Visual sanity of `results/congress/figures/*.pdf` — deferred to Phase 6 writeup pass

## Deferred Items

Items deferred to v2 (from REQUIREMENTS.md):

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Validation | V2-01: Caffeine trace cross-validation (±2% agreement) | Deferred to v2 | Milestone 2 planning |
| Policy | V2-02: LHD or AdaptSize as 7th policy | Deferred to v2 | Milestone 2 planning |
| Trace | V2-03: Third trace domain (SEC EDGAR) | Deferred to v2 | Milestone 2 planning |

## Session Continuity

Last session: 2026-04-19T17:43:57.123Z
Stopped at: Phase 3 Plan 03 complete — ready for verification
Resume: execute Plan 03-02 (overnight 20K collection — checkpoint wave) via `python3 scripts/collect_court_trace.py --output traces/court_trace.csv --report results/court/collection_report.txt --target-rows 20000`; expected ~8h wall-clock based on observed smoke pacing (~1.27s/issued-request × ~23,530 issued for 20K at 85% success); --resume path coded but untested against a real partial — first live test is if 03-02 is interrupted
