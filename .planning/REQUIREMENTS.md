# Requirements — civicache Milestone 2

**Project:** civicache — CS 2640 Final Project (Spring 2026)
**Last updated:** 2026-04-18
**Core value:** A defensible, well-analyzed comparison of cache eviction policies on real legislative + judicial API workloads, delivered as a submission-ready paper + code + AI-use report + live demo.

---

## Validated (existing capabilities — Milestone 1)

### Simulator core (SIM-01 through SIM-08)
- ✓ **SIM-01**: C++17 simulator compiles clean with Makefile, no external deps
- ✓ **SIM-02**: LRU, FIFO, CLOCK, S3-FIFO, SIEVE implementations correct and benchmarked
- ✓ **SIM-03**: Zipf trace generation with fixed per-object sizes
- ✓ **SIM-04**: MLE Zipf alpha estimator (Clauset et al. 2009) — recovers α=0.797 from true 0.8
- ✓ **SIM-05**: One-hit-wonder ratio analysis at 6 window lengths
- ✓ **SIM-06**: SHARDS MRC construction at 0.1%/1%/10% sampling
- ✓ **SIM-07**: Exact stack-distance validation against SHARDS (2% MAE at 10%)
- ✓ **SIM-08**: Alpha sensitivity sweep (α ∈ [0.6, 1.2])

### Trace infrastructure (TRACE-01, TRACE-02)
- ✓ **TRACE-01**: Congress.gov trace collector — 20,692 requests collected, rate-limited + backoff
- ✓ **TRACE-02**: Replay-Zipf mode overlays synthetic Zipf popularity on real keys/sizes

### Documentation + pipeline (PLOT-01, DOC-01)
- ✓ **PLOT-01**: matplotlib pipeline produces 6 figures (MRC, byte MRC, alpha, OHW, SHARDS MRC, workload)
- ✓ **DOC-01**: Progress report, PROCESS.md, README, codebase map, 4 research docs + summary

---

## v1 Requirements (Milestone 2 — to ship)

### Enabling refactors (REFACTOR-xx)

- [x] **REFACTOR-01**: Extract FNV-1a hash from `src/shards.cpp:85-98` into `include/hash_util.h` with 4 deterministic seeds (verified Phase 1)
- [x] **REFACTOR-02**: Refactor `replay_zipf()` to accept a pre-shuffled object list (avoids 7× redundant trace-gen during alpha sweep) (verified Phase 1)
- [x] **REFACTOR-03**: Add throughput measurement (`accesses/sec`) to simulation output — new CSV column (verified Phase 1)
- [x] **REFACTOR-04**: Reorganize `results/` into per-workload subdirs (`results/congress/`, `results/court/`, `results/shards_large/`, `results/compare/`) (verified Phase 1)

### W-TinyLFU policy (WTLFU-xx)

- [x] **WTLFU-01**: Implement `include/count_min_sketch.h` — 4-bit counters, depth=4, width=nextpow2(capacity-objects), conservative update, periodic halving every 10×W accesses
- [x] **WTLFU-02**: Implement `include/wtinylfu.h` — 1% window LRU + 99% main SLRU (80% protected / 20% probationary) + TinyLFU admission via CMS
- [x] **WTLFU-03**: Integrate W-TinyLFU into `CachePolicy` hierarchy and `make_policy()` dispatch
- [x] **WTLFU-04**: Unit test: 20-access hot object survives 1000-access sequential scan of unique keys (verified Phase 2 Plan 04 — `tests/test_wtinylfu.cpp::test_hot_survives_scan` PASS under `make test`)
- [x] **WTLFU-05**: Validation on Congress replay: W-TinyLFU beats LRU at α≥0.8 on every cache size; within ±2% of LRU at α=0 (verified Phase 2 Plan 06 — `scripts/check_wtlfu_acceptance.py --results-dir results/congress` exit 0; W-TinyLFU beats LRU monotonically by 7.84-21.55% across alpha {0.6..1.2}; Condition B one-sided regression guard per checkpoint decision)

### Doorkeeper ablation (DOOR-xx)

- [x] **DOOR-01**: Implement `include/doorkeeper.h` — Bloom filter with two hash functions, configurable bit-array size (verified Phase 4 Plan 02 — include/doorkeeper.h 79-line header-only class with Kirsch-Mitzenmacher double-hashing on FNV_SEED_A+B, 4× n_objects_hint bit sizing; tests/test_doorkeeper.cpp 3-gate coverage PASS including empirical FPR 0.0829 in [0.05, 0.25] sanity band; `make test` exit 0 on both wtinylfu + doorkeeper suites)
- [ ] **DOOR-02**: Add W-TinyLFU+Doorkeeper variant (gated by constructor flag)
- [ ] **DOOR-03**: Doorkeeper ablation figure: W-TinyLFU ± Doorkeeper on both workloads

### CourtListener trace (TRACE-xx)

- [x] **TRACE-03**: Register CourtListener account, obtain API token, store as `COURTLISTENER_API_KEY` env var (verified Phase 1)
- [x] **TRACE-04**: Pilot 200-request run (4 endpoints: `/dockets/`, `/opinions/`, `/clusters/`, `/courts/`) to tune ID ranges for ≥70% success rate (verified Phase 1 — 90%/74%/90%/100%)
- [x] **TRACE-05**: Implement `scripts/collect_court_trace.py` — 0.8s + 0-0.4s jitter, backoff, 80% metadata / 20% full plain_text mix (verified Phase 3 Plan 01 — scripts/collect_court_trace.py at e9d8557, 609 lines; all 26 grep-discoverable invariants pass including D-02 minimal field set, [0,30,90] 429 ramp, 5-consec hard-stop with exact FATAL diagnostic, module-level + per-request urlparse host allowlist, --resume by endpoint-prefix classification; 10-row smoke against live CourtListener API in 14s exit 0 — actual 20K data collection is TRACE-06 / Plan 03-02)
- [x] **TRACE-06**: Collect ≥20K-request CourtListener trace (verified Phase 3 Plan 02 — traces/court_trace.csv at f9b60de, 20,001 lines; 5,000 successful rows per endpoint per D-05; 8h 56m runtime; per-endpoint success docket 89.1% / opinion 71.5% / cluster 85.6% / court 100% all ≥70% gate; results/court/collection_report.txt committed via .gitignore D-15 exemption)
- [x] **TRACE-07**: Run full policy sweep (6 policies) on court trace via replay-Zipf (verified Phase 3 Plan 03 — make run-sweep WORKLOAD=court TRACE=traces/court_trace.csv produced results/court/mrc.csv (36 rows: 6 policies × 6 cache fractions) + alpha_sensitivity.csv (42 rows: 6 policies × 7 alphas) with W-TinyLFU rows present; 5 figures regenerated via make plots WORKLOAD=court; W-TinyLFU monotonically dominates at all α on court trace, consistent with Phase 2's Congress finding)

### SHARDS large-scale validation (SHARDS-xx)

- [x] **SHARDS-01**: Generate 1M-access synthetic Zipf trace (α=0.8, 100K objects) (verified Phase 4 Plan 01 — traces/shards_large.csv 1,000,001 lines, generated by `./cache_sim --emit-trace --num-requests 1000000 --num-objects 100000 --alpha 0.8` with hardcoded seed=42; gitignored per D-15)
- [x] **SHARDS-02**: Extend sampling rates to 0.01%/0.1%/1%/10% and run SHARDS on the 1M trace (verified Phase 4 Plan 01 — results/shards_large/shards_mrc.csv contains all 4 rates {0.0001, 0.001, 0.01, 0.1}; the 0.0001 rate caveat (81 samples < 200 floor) is flagged via n_samples_compared column in shards_convergence.csv)
- [x] **SHARDS-03**: Report self-convergence (no exact oracle — infeasible at 1M scale): MAE between adjacent rates, error vs sampling-rate figure (verified Phase 4 Plan 01 — results/shards_large/shards_convergence.csv with schema reference_rate,compared_rate,mae,max_abs_error,num_points,n_samples_reference,n_samples_compared; 3 rows vs 10% reference per D-02 monotone-vs-10% framing; figures/shards_convergence.pdf + figures/shards_mrc_overlay.pdf render the error-vs-rate + PITFALLS M3 money-shot)

### Ablation studies (ABLA-xx)

- [ ] **ABLA-01**: S3-FIFO small-queue ratio sweep (5%, 10%, 20%) on both workloads at fixed cache size
- [ ] **ABLA-02**: SIEVE visited-bit ablation — SIEVE without promotion on hit vs with, on both workloads

### Analysis infrastructure (ANAL-xx)

- [ ] **ANAL-01**: `scripts/compare_workloads.py` — reads both result trees, produces cross-workload comparison plots and summary tables
- [ ] **ANAL-02**: Multi-seed runs (5 seeds) for all final policy comparisons with confidence intervals
- [ ] **ANAL-03**: Cross-workload table: workload characterization (α, OHW, size dist, working set) for Congress vs Court
- [ ] **ANAL-04**: Winner-per-regime analysis (which policy wins when: small cache, high skew, mixed sizes, etc.)

### Writeup (DOC-xx)

- [ ] **DOC-02**: Final report (class-report length) — workload char table up front, policy comparison, SHARDS validation, ablations, winner-per-regime, practitioner decision tree
- [ ] **DOC-03**: AI-use report — what worked/didn't with Claude Code, including PROCESS.md 9-bug list as concrete learning moments
- [ ] **DOC-04**: Live simulator demo script (`demo.sh`) — <60s runtime, pre-loaded <10K trace, screen-recording backup, tested 3+ times on target laptop

---

## v2 Requirements (deferred — only if runway allows)

- ⋯ **V2-01**: Caffeine trace cross-validation (run our W-TinyLFU on a Caffeine-published workload for ±2% agreement)
- ⋯ **V2-02**: LHD or AdaptSize as 7th policy
- ⋯ **V2-03**: Third trace domain (SEC EDGAR)

## Out of Scope

- **Production deployment** — this is a simulator, not a runtime cache
- **Multi-threading / concurrent access** — single-threaded by design
- **Cost-based eviction (GDSF, LFUDA)** beyond W-TinyLFU — scope containment
- **Real server-side access logs** — Congress.gov/CourtListener don't publish these; replay-Zipf is the mitigation
- **W-TinyLFU hill-climbing** — adaptive window sizing adds ~200 LoC and complicates comparison without helping the core story
- **Caffeine line-by-line port** — roll-your-own CMS is simpler and sufficient for comparison purposes
- **PACER direct access** — paywalled ($500-$2000 for 20K trace), rejected in favor of free CourtListener
- **Gated CourtListener endpoints** (`/docket-entries/`, `/recap-documents/`, `/recap-query/`) — return 403 without special access; not needed for workload comparison

---

## Traceability — Phase Mapping

All 29 v1 requirements below are mapped to exactly one Milestone 2 phase. See `.planning/ROADMAP.md` for phase details.

| Requirement | Phase | Status |
|-------------|-------|--------|
| REFACTOR-01 | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| REFACTOR-02 | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| REFACTOR-03 | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| REFACTOR-04 | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| TRACE-03    | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| TRACE-04    | Phase 1 — Enabling Refactors & CourtListener Pilot | Verified |
| WTLFU-01    | Phase 2 — W-TinyLFU Core | Complete |
| WTLFU-02    | Phase 2 — W-TinyLFU Core | Complete |
| WTLFU-03    | Phase 2 — W-TinyLFU Core | Complete |
| WTLFU-04    | Phase 2 — W-TinyLFU Core | Complete |
| WTLFU-05    | Phase 2 — W-TinyLFU Core | Complete |
| TRACE-05    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Complete |
| TRACE-06    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Complete |
| TRACE-07    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Complete |
| SHARDS-01   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Complete |
| SHARDS-02   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Complete |
| SHARDS-03   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Complete |
| DOOR-01     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Complete |
| DOOR-02     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| DOOR-03     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| ABLA-01     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| ABLA-02     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| ANAL-01     | Phase 5 — Cross-Workload Analysis Infrastructure | Pending |
| ANAL-02     | Phase 5 — Cross-Workload Analysis Infrastructure | Pending |
| ANAL-03     | Phase 5 — Cross-Workload Analysis Infrastructure | Pending |
| ANAL-04     | Phase 5 — Cross-Workload Analysis Infrastructure | Pending |
| DOC-02      | Phase 6 — Writeup & Demo | Pending |
| DOC-03      | Phase 6 — Writeup & Demo | Pending |
| DOC-04      | Phase 6 — Writeup & Demo | Pending |

**Coverage:** 29/29 v1 requirements mapped (100%). No orphans, no duplicates.

**Phase totals:**

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 — Enabling Refactors & CourtListener Pilot | REFACTOR-01..04, TRACE-03, TRACE-04 | 6 |
| 2 — W-TinyLFU Core | WTLFU-01..05 | 5 |
| 3 — CourtListener Trace Collection & Replay Sweep | TRACE-05, TRACE-06, TRACE-07 | 3 |
| 4 — SHARDS Large-Scale Validation & Ablations | SHARDS-01..03, DOOR-01..03, ABLA-01..02 | 8 |
| 5 — Cross-Workload Analysis Infrastructure | ANAL-01..04 | 4 |
| 6 — Writeup & Demo | DOC-02..04 | 3 |
| **Total** | | **29** |
