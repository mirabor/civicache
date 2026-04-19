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

- [ ] **WTLFU-01**: Implement `include/count_min_sketch.h` — 4-bit counters, depth=4, width=nextpow2(capacity-objects), conservative update, periodic halving every 10×W accesses
- [ ] **WTLFU-02**: Implement `include/wtinylfu.h` — 1% window LRU + 99% main SLRU (80% protected / 20% probationary) + TinyLFU admission via CMS
- [ ] **WTLFU-03**: Integrate W-TinyLFU into `CachePolicy` hierarchy and `make_policy()` dispatch
- [ ] **WTLFU-04**: Unit test: 20-access hot object survives 1000-access sequential scan of unique keys
- [ ] **WTLFU-05**: Validation on Congress replay: W-TinyLFU beats LRU at α≥0.8 on every cache size; within ±2% of LRU at α=0

### Doorkeeper ablation (DOOR-xx)

- [ ] **DOOR-01**: Implement `include/doorkeeper.h` — Bloom filter with two hash functions, configurable bit-array size
- [ ] **DOOR-02**: Add W-TinyLFU+Doorkeeper variant (gated by constructor flag)
- [ ] **DOOR-03**: Doorkeeper ablation figure: W-TinyLFU ± Doorkeeper on both workloads

### CourtListener trace (TRACE-xx)

- [x] **TRACE-03**: Register CourtListener account, obtain API token, store as `COURTLISTENER_API_KEY` env var (verified Phase 1)
- [x] **TRACE-04**: Pilot 200-request run (4 endpoints: `/dockets/`, `/opinions/`, `/clusters/`, `/courts/`) to tune ID ranges for ≥70% success rate (verified Phase 1 — 90%/74%/90%/100%)
- [ ] **TRACE-05**: Implement `scripts/collect_court_trace.py` — 0.8s + 0-0.4s jitter, backoff, 80% metadata / 20% full plain_text mix
- [ ] **TRACE-06**: Collect ≥20K-request CourtListener trace
- [ ] **TRACE-07**: Run full policy sweep (6 policies) on court trace via replay-Zipf

### SHARDS large-scale validation (SHARDS-xx)

- [ ] **SHARDS-01**: Generate 1M-access synthetic Zipf trace (α=0.8, 100K objects)
- [ ] **SHARDS-02**: Extend sampling rates to 0.01%/0.1%/1%/10% and run SHARDS on the 1M trace
- [ ] **SHARDS-03**: Report self-convergence (no exact oracle — infeasible at 1M scale): MAE between adjacent rates, error vs sampling-rate figure

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
| WTLFU-01    | Phase 2 — W-TinyLFU Core | Pending |
| WTLFU-02    | Phase 2 — W-TinyLFU Core | Pending |
| WTLFU-03    | Phase 2 — W-TinyLFU Core | Pending |
| WTLFU-04    | Phase 2 — W-TinyLFU Core | Pending |
| WTLFU-05    | Phase 2 — W-TinyLFU Core | Pending |
| TRACE-05    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Pending |
| TRACE-06    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Pending |
| TRACE-07    | Phase 3 — CourtListener Trace Collection & Replay Sweep | Pending |
| SHARDS-01   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| SHARDS-02   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| SHARDS-03   | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
| DOOR-01     | Phase 4 — SHARDS Large-Scale Validation & Ablations | Pending |
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
