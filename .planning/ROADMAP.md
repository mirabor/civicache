# Roadmap: civicache — Milestone 2

**Project:** civicache (CS 2640 Final Project, Spring 2026)
**Milestone:** 2 (submission-ready extension of base simulator)
**Granularity:** Standard (6 phases)
**Created:** 2026-04-18

## Overview

The base simulator (LRU, FIFO, CLOCK, S3-FIFO, SIEVE + Congress.gov replay-Zipf + SHARDS) is complete and validated. Milestone 2 delivers a submission-ready extension: a sixth policy (W-TinyLFU with Count-Min Sketch and an optional Doorkeeper ablation), a second real-world workload (CourtListener REST v4), larger-scale SHARDS rigor (1M-access synthetic trace with four sampling rates), cross-workload analysis, and the final deliverables (class-report paper, AI-use report per the professor's request, live demo). Execution order follows the research build order: enabling refactors + CourtListener pilot run in parallel first, then W-TinyLFU core (depends on the hash refactor), then trace collection and sweep, then SHARDS large-scale work plus ablations (Doorkeeper, S3-FIFO ratio, SIEVE visited-bit), then cross-workload analysis infrastructure, and finally the writeup and demo (with ≥1 week budget for writing).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Enabling Refactors & CourtListener Pilot** - Extract FNV-1a, refactor replay_zipf, add throughput metric, reorganize results tree, register CourtListener token and run 200-request pilot across planned endpoints (completed 2026-04-18)
- [x] **Phase 2: W-TinyLFU Core** - Implement Count-Min Sketch and W-TinyLFU (1%/99% window/SLRU, conservative update + periodic halving), integrate into CachePolicy hierarchy, validate on Congress replay (completed 2026-04-19; all 5 WTLFU-01..05 requirements verified; WTLFU-05 gate via scripts/check_wtlfu_acceptance.py exit 0)
- [x] **Phase 3: CourtListener Trace Collection & Replay Sweep** - Implement court-records collector, collect ≥20K-request trace, run full 6-policy sweep on court trace via replay-Zipf (completed 2026-04-19; TRACE-05/06/07 all verified; 20,001-line traces/court_trace.csv committed via .gitignore D-15 exemption; Makefile WORKLOAD=court parameterization with Congress back-compat preserved)
- [ ] **Phase 4: SHARDS Large-Scale Validation & Ablations** - Generate 1M-access synthetic trace, extend SHARDS to 0.01%/0.1%/1%/10% sampling with self-convergence reporting, implement Doorkeeper + ablation figure, S3-FIFO ratio sweep, SIEVE visited-bit ablation
- [ ] **Phase 5: Cross-Workload Analysis Infrastructure** - Build compare_workloads.py, run multi-seed (5-seed) final sweep on both traces with confidence intervals, produce workload-characterization table and winner-per-regime analysis
- [ ] **Phase 6: Writeup & Demo** - Deliver final class-report (workload char → policy comparison → SHARDS validation → ablations → winner-per-regime → practitioner decision tree), AI-use report (including PROCESS.md 9-bug list), and <60s demo.sh tested 3+ times on target laptop

## Phase Details

### Phase 1: Enabling Refactors & CourtListener Pilot
**Goal**: Unblock downstream work — the hash refactor is required by W-TinyLFU, the replay_zipf refactor is required for the multi-seed cross-workload sweep, and the CourtListener token + pilot must succeed before any real collection is attempted.
**Depends on**: Nothing (first phase — builds on completed Milestone 1)
**Requirements**: REFACTOR-01, REFACTOR-02, REFACTOR-03, REFACTOR-04, TRACE-03, TRACE-04
**Success Criteria** (what must be TRUE):
  1. `include/hash_util.h` exists with FNV-1a and 4 deterministic seeds; `src/shards.cpp` uses it; `std::hash` absent from cache code
  2. `replay_zipf` accepts a pre-shuffled object list; a 7-alpha sweep on the Congress trace completes noticeably faster than the prior regeneration-per-alpha baseline
  3. Simulator CSV output contains a new `accesses_per_sec` column; `results/` is reorganized into `{congress, court, shards_large, compare}/` subdirectories
  4. `COURTLISTENER_API_KEY` is configured and a 200-request pilot across `/dockets/`, `/opinions/`, `/clusters/`, `/courts/` returns ≥70% success with no 403s from gated endpoints
**Plans**: 6 plans across 4 execution waves
- [x] 01-01-PLAN.md — Extract FNV-1a into include/hash_util.h with 4 seeds + self-test (Wave 1, autonomous, REFACTOR-01)
- [x] 01-02-PLAN.md — Split replay_zipf into prepare_objects + generate_replay_trace; hoist out of alpha sweep (Wave 2, autonomous, REFACTOR-02)
- [x] 01-03-PLAN.md — Add accesses_per_sec column to mrc/alpha/shards CSVs; plot_results tolerance (Wave 3, autonomous, REFACTOR-03)
- [x] 01-04-PLAN.md — Reorganize results/ into per-workload subdirs; add --workload flag; update Makefile (Wave 4, autonomous, REFACTOR-04)
- [x] 01-05-PLAN.md — Register CourtListener account, configure COURTLISTENER_API_KEY, verify via curl (Wave 1, checkpoint, TRACE-03)
- [x] 01-06-PLAN.md — Build scripts/pilot_court_trace.py, run 200-request pilot, enforce ≥70% gate (Wave 2, autonomous, TRACE-04)

### Phase 2: W-TinyLFU Core
**Goal**: A working, validated W-TinyLFU policy plugged into the existing CachePolicy hierarchy — correct behavior on the "hot object survives scan" invariant and the expected α-regime relationship to LRU on Congress replay.
**Depends on**: Phase 1 (needs `hash_util.h` and the throughput CSV column)
**Requirements**: WTLFU-01, WTLFU-02, WTLFU-03, WTLFU-04, WTLFU-05
**Success Criteria** (what must be TRUE):
  1. `include/count_min_sketch.h` exists — 4-bit counters, depth=4, width=nextpow2(capacity-objects), conservative update, periodic halving every 10×W accesses, deterministic seed
  2. `include/wtinylfu.h` exists — 1% window LRU + 99% main SLRU (80% protected / 20% probationary) + TinyLFU admission via CMS; selectable through `make_policy("wtinylfu", ...)`
  3. Unit test passes: a 20-access hot object survives a subsequent 1000-access sequential scan of unique keys
  4. W-TinyLFU beats LRU at α≥0.8 across every cache size on Congress replay-Zipf; W-TinyLFU is within ±2% of LRU at α=0 (uniform)
**Plans**: 6 plans across 5 execution waves
- [x] 02-01-PLAN.md — Caffeine v3.x pre-work: pull FrequencySketch.java + BoundedLocalCache.java, lock CMS update rule + D-08a..D-08e edge-case rules (Wave 1, BLOCKING, autonomous) — completed 2026-04-19, commit 665c767, output `.planning/phases/02-w-tinylfu-core/02-01-CAFFEINE-NOTES.md` (549 lines, 6 deviations documented)
- [x] 02-02-PLAN.md — include/count_min_sketch.h: 4-bit packed CMS, depth=4, width=nextpow2, FNV-1a seeded, periodic halving (Wave 2, autonomous, WTLFU-01)
- [x] 02-03-PLAN.md — include/wtinylfu.h + cache.h subordinate-include + main.cpp make_policy widen + --policies dispatch (Wave 3, autonomous, WTLFU-02 + WTLFU-03) — completed 2026-04-18, commits 9613a30+6880a34+8599b60, output include/wtinylfu.h (228 lines)
- [x] 02-04-PLAN.md — tests/test_wtinylfu.cpp standalone test binary + Makefile test target (Wave 4, autonomous, WTLFU-04) — completed 2026-04-19, commits 2e48457+28cc8ab, outputs tests/test_wtinylfu.cpp (198 lines, 4 tests PASS) + Makefile test target with build/test/ object dir (D-07)
- [x] 02-05-PLAN.md — scripts/plot_results.py POLICY_COLORS/MARKERS W-TinyLFU entry (Wave 4, autonomous, WTLFU-02) — completed 2026-04-19, commit b089209, +2 lines to scripts/plot_results.py (POLICY_COLORS['W-TinyLFU']=#8c564b, POLICY_MARKERS['W-TinyLFU']=P); Rule 3 hygiene added __pycache__ to .gitignore
- [x] 02-06-PLAN.md — Validation sweep on Congress trace + scripts/check_wtlfu_acceptance.py (Wave 5, autonomous, WTLFU-05) — completed 2026-04-19, commit 10f96e3, output scripts/check_wtlfu_acceptance.py (147 lines, exit 0 on sweep CSVs); W-TinyLFU beats LRU monotonically 7.84-21.55% across alpha {0.6..1.2}; Condition B one-sided per checkpoint decision (regression guard intent, not penalty for outperformance); `make plots` regenerated 6 PDFs with W-TinyLFU brown/plus styling

### Phase 3: CourtListener Trace Collection & Replay Sweep
**Goal**: A real ≥20K-request CourtListener trace exists on disk, and all six policies have been run on it via replay-Zipf, producing the second-workload data needed for cross-workload analysis.
**Depends on**: Phase 1 (pilot verified + results layout), Phase 2 (W-TinyLFU exists so the 6-policy sweep is feasible)
**Requirements**: TRACE-05, TRACE-06, TRACE-07
**Success Criteria** (what must be TRUE):
  1. `scripts/collect_court_trace.py` exists with 0.8s + 0-0.4s jitter, Retry-After + exponential backoff, 80% metadata / 20% full `plain_text` mix, and a hard host allowlist for `www.courtlistener.com`
  2. `results/court/trace.csv` (or equivalent — per CONTEXT D-15 the committed path is `traces/court_trace.csv`) contains ≥20,000 successful `(timestamp, key, size)` rows with per-endpoint success tallies logged
  3. A full 6-policy sweep (LRU, FIFO, CLOCK, S3-FIFO, SIEVE, W-TinyLFU) on the court trace via replay-Zipf completes and writes MRC/byte-MRC/alpha-sensitivity CSVs under `results/court/`
**Plans**: 3 plans across 3 execution waves
- [x] 03-01-PLAN.md — Build scripts/collect_court_trace.py (D-01..D-11) with 80/20 ?fields= mix, 0.8s+0.4s jitter, Retry-After ramp [0,30,90], 5-consec-429 hard-stop, host allowlist, --resume; smoke-verified via 10-row run (Wave 1, autonomous, TRACE-05) — completed 2026-04-19, commit e9d8557, 609 lines, 10-row smoke in 14s exit 0
- [x] 03-02-PLAN.md — Run overnight 20K collection; produce traces/court_trace.csv (≥20,001 lines) + results/court/collection_report.txt; commit both per D-15 (Wave 2, checkpoint overnight run, TRACE-06) — completed 2026-04-19, commit f9b60de, 20,001 lines, 5K per endpoint, 8h 56m runtime, all 4 endpoints ≥70% gate
- [x] 03-03-PLAN.md — scripts/workload_stats_json.py (D-13); Makefile WORKLOAD+TRACE parameterization; `make run-sweep WORKLOAD=court TRACE=traces/court_trace.csv` 6-policy replay-Zipf sweep; regenerate figures via `make plots WORKLOAD=court` (Wave 3, autonomous, TRACE-06 + TRACE-07) — completed 2026-04-19, commits 2136cd7 + d160c97; results/court/{mrc.csv, alpha_sensitivity.csv, workload_stats.json, figures/*.pdf} produced; Congress back-compat preserved (make -n run-sweep default renders identically); court α_mle=1.028, unique=15018, median 1381 bytes, max 462KB — matches STACK.md court-vs-Congress contrast prediction

### Phase 4: SHARDS Large-Scale Validation & Ablations
**Goal**: Defensible rigor claims — SHARDS self-convergence at 1M scale across four sampling rates, plus the three ablation figures (Doorkeeper, S3-FIFO ratio, SIEVE visited-bit) that the writeup's "winner per regime" story needs.
**Depends on**: Phase 2 (W-TinyLFU exists, required for Doorkeeper variant), Phase 3 (both workloads exist, required for ablations on both)
**Requirements**: SHARDS-01, SHARDS-02, SHARDS-03, DOOR-01, DOOR-02, DOOR-03, ABLA-01, ABLA-02
**Success Criteria** (what must be TRUE):
  1. A 1M-access synthetic Zipf(α=0.8) trace with 100K objects exists under `results/shards_large/` and SHARDS produces MRCs at 0.01%/0.1%/1%/10% sampling with ≥200 samples each
  2. A published self-convergence table exists reporting MAE between adjacent sampling rates and an error-vs-sampling-rate figure (no exact oracle — infeasible at 1M scale)
  3. `include/doorkeeper.h` exists (Bloom filter, two hash functions, configurable size); W-TinyLFU+Doorkeeper variant is gated by a constructor flag; the ablation figure shows W-TinyLFU ± Doorkeeper on both workloads
  4. S3-FIFO small-queue ratio sweep (5%, 10%, 20%) and SIEVE visited-bit ablation (on vs off) have both been run on both workloads at a fixed cache size, with CSVs written under `results/congress/` and `results/court/`
**Plans**: TBD

### Phase 5: Cross-Workload Analysis Infrastructure
**Goal**: Final comparison artifacts — the numbers and tables the report is built from. Cross-workload comparison plots, multi-seed confidence intervals, workload-characterization table, and winner-per-regime analysis.
**Depends on**: Phase 4 (SHARDS rigor + all ablations complete)
**Requirements**: ANAL-01, ANAL-02, ANAL-03, ANAL-04
**Success Criteria** (what must be TRUE):
  1. `scripts/compare_workloads.py` reads `results/congress/` and `results/court/` and produces cross-workload comparison plots and a summary table under `results/compare/`
  2. The final policy comparison was run with 5 seeds per (policy, cache-size, α) cell on both workloads; plots show mean ± std-dev bands; differences smaller than 2σ are flagged not-significant
  3. A workload-characterization table exists with α, OHW ratio, unique objects, median size, 95th-percentile size, and working-set bytes — Congress and Court side by side
  4. A winner-per-regime table/figure exists identifying which policy wins under which conditions (small cache, high skew, mixed sizes, OHW regime) across both workloads
**Plans**: TBD

### Phase 6: Writeup & Demo
**Goal**: The three final deliverables the professor evaluates — class-report paper, AI-use report (specifically requested), and a live <60s demo that actually works on the target laptop.
**Depends on**: Phase 5 (all analysis complete — the paper cannot be written without final numbers)
**Requirements**: DOC-02, DOC-03, DOC-04
**Success Criteria** (what must be TRUE):
  1. `DOC-02` final report exists as a submission-ready PDF with: workload characterization table up front, policy comparison (both workloads, full MRC + error bands), SHARDS validation section with 4-rate table, ablation figures, winner-per-regime + practitioner decision tree at end
  2. `DOC-03` AI-use report exists and includes the PROCESS.md 9-bug list framed as concrete AI-collaboration learning moments (not successes-only)
  3. `demo.sh` exists, sources `.env`, sets `DYLD_LIBRARY_PATH`, runs a pre-loaded <10K-access trace through the simulator in <60s total wall-clock, and has been tested end-to-end at least 3 times on the target demo laptop
  4. A screen-recording backup of the full working demo exists and is ready to cut to if the live run hangs

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Enabling Refactors & CourtListener Pilot | 6/6 | Complete | 2026-04-18 |
| 2. W-TinyLFU Core | 6/6 | Complete | 2026-04-19 |
| 3. CourtListener Trace Collection & Replay Sweep | 3/3 | Complete | 2026-04-19 |
| 4. SHARDS Large-Scale Validation & Ablations | 0/TBD | Not started | - |
| 5. Cross-Workload Analysis Infrastructure | 0/TBD | Not started | - |
| 6. Writeup & Demo | 0/TBD | Not started | - |
