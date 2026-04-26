# Decisions Matrix — civicache

**Every load‑bearing decision made across Milestone 2, organized by category. For each: when it was made, what category it fits, current status, evidence link, and outcome.**

Use this when someone drills into "why did you pick X over Y" or "what happens to Z if I change A". Use `PROJECT-JOURNEY.md` for the chronological narrative.

**Categories used:**
- **A. Architecture** — code structure, file layout, integration points, data structures
- **M. Methodology** — statistical rigor, validation strategies, sampling, experimental design
- **S. Scope** — what's in/out, deferral choices, scope‑creep redirects
- **T. Tooling** — build system, language, dependencies, environment
- **F. Framing** — narrative, naming, presentation, paper structure
- **W. Workflow** — process, parallelism, conventions, gates

**Status values:**
- **Kept** — decision held through delivery, no overrides
- **Revised** — decision was changed mid‑project; revision documented in evidence
- **Deferred** — explicitly punted to v2 or post‑milestone
- **Overridden** — earlier decision was superseded by a later phase

---

## Project‑Level Decisions (PROJECT.md Key Decisions table)

| ID | Category | Decision | Rationale | Status | Evidence | Outcome |
|---|---|---|---|---|---|---|
| KD‑01 | S | CourtListener (vs PACER, OpenSecrets, SEC EDGAR) as second trace source | Stays in legal/public‑records domain; contrasting size distribution; richer endpoint taxonomy; PACER charges per page, CourtListener is free | Kept | `.planning/PROJECT.md:81`, Phase 1 pilot validation | 4 endpoint families pass 200‑req pilot; 20K trace at 9h wall‑clock |
| KD‑02 | A | W‑TinyLFU (vs simple admission filter or basic TinyLFU) as 6th policy | Most impressive of the three options; matches Caffeine; frequency sketch is good systems‑course material | Kept | `.planning/PROJECT.md:82`, Phase 2 | 6th policy added; dominates LRU monotonically α∈{0.6..1.2} |
| KD‑03 | M | Larger SHARDS validation trace synthetic (1M), not real | Real traces are rate‑limited; synthetic gives enough scale to meaningfully test 0.1% and 0.01% sampling | Kept | `.planning/PROJECT.md:83`, Phase 4 | 1M Zipf trace; 4‑rate self‑convergence MAE table |
| KD‑04 | F | Live simulator demo over static slides | More engaging; shows the system working; parameter sweeps illustrate findings in real time | Kept | `.planning/PROJECT.md:84`, Phase 6 | demo.sh in 4s wall‑clock; recording backup committed |
| KD‑05 | M | Replay‑Zipf as primary analysis approach | Raw traces have near‑zero temporal locality (random client queries); replay‑Zipf preserves real keys/sizes with controlled popularity | Kept | `.planning/PROJECT.md:85`; reconfirmed Phase 5 with raw Congress α_mle=0.231 | All comparative analysis done via replay‑Zipf; raw‑trace results would have been undifferentiated noise |
| KD‑06 | M | 5‑seed multi‑run with Welch's t‑test for final comparison | Single‑seed can't distinguish real differences from RNG noise; 5 seeds is min for credible Welch's at p<0.05 | Kept | `.planning/PROJECT.md:86`, Phase 5 D‑05 | 58.2s wall‑clock for full sweep; W‑TinyLFU dominance over LRU on Congress at p∈[1.2e‑06, 8.7e‑08] |
| KD‑07 | M | BASE_POLICIES restriction on regime analysis (exclude ablation variants) | Regimes define the main story; ablations have own Phase 4 figures and would muddy winner‑per‑regime table | Kept | `.planning/PROJECT.md:87`, Phase 5 D‑01 | Zero ablation contamination in `winner_per_regime.{md,json}` |

---

## Phase 1 — Refactors & CourtListener Pilot

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 1‑D01 | M | Throughput = one value per (policy, cache‑size) cell, `accesses_per_sec` column | Kept | `01-CONTEXT.md:25`, `mrc.csv` schema | Schema unchanged through delivery |
| 1‑D02 | M | Throughput measured via `std::chrono::steady_clock` wall‑clock, not CPU time | Kept | `01-CONTEXT.md:26` | Simple, portable, signal strong at 500K scale |
| 1‑D03 | A | Alpha sweep + SHARDS runs also produce throughput values | Kept | `01-CONTEXT.md:27` | Enables Pareto plots downstream (not used in Phase 6 — kept anyway for completeness) |
| 1‑D04 | A | Preserve existing Congress results — `git mv results/*.csv results/congress/` + empty stubs for `results/{court,shards_large,compare}/` | Kept | `01-CONTEXT.md:30` | Stubs populated by Phases 3/4/5 respectively |
| 1‑D05 | A | `scripts/plot_results.py` reads from `results/{workload}/` subdirs; `--workload` flag (default `congress` for back‑compat) | Kept | `01-CONTEXT.md:31` | Phase 3 ran `make plots WORKLOAD=court` first time |
| 1‑D06 | A | Main.cpp `--output-dir` flag keeps current semantics; callers pass `results/congress/` or `results/court/` explicitly | Kept | `01-CONTEXT.md:32` | Simulator stays workload‑agnostic |
| 1‑D07 | M | Pilot endpoint <70% success → narrow ID range and rerun until ≥70% | Kept (unused) | `01-CONTEXT.md:35` | All 4 endpoints passed first try; fallback never fired |
| 1‑D08 | M | Pilot script emits per‑endpoint tally (200s/404s/403s/429s/other); success = 200 + size > 0 | Kept | `01-CONTEXT.md:36`, `scripts/pilot_court_trace.py` | Carried forward to Phase 3 production collector |
| 1‑D09 | S | Fundamentally gated endpoint (403 pattern) → drop from mix; don't keep retrying | Kept (unused) | `01-CONTEXT.md:37` | No 403 patterns observed |
| 1‑D10 | A | `replay_zipf` split into `prepare_objects(raw_trace, seed) → vector<(key, size)>` and `generate_replay_trace(objects, num_requests, alpha, seed)` | Kept | `01-CONTEXT.md:40-43` | Alpha sweep now calls prepare_objects ONCE, generate_replay_trace 7× |
| 1‑D11 | A | Existing `replay_zipf()` stays as thin wrapper for back‑compat | Kept | `01-CONTEXT.md:43` | `main.cpp` callers unchanged |
| 1‑D12 | A | `include/hash_util.h` contains `fnv1a_64(s, seed=FNV_BASIS)` + 4 named seed constants `FNV_SEED_A..D` | Kept | `01-CONTEXT.md:46-49` | Used by SHARDS, CMS (Phase 2), Doorkeeper (Phase 4) |
| 1‑D13 | A | `src/shards.cpp` replaces local FNV‑1a with shared one (`SHARDS_SEED = FNV_BASIS`) | Kept | `01-CONTEXT.md:49` | Zero behavioral change |
| 1‑D14 | A | `std::hash<std::string>` banned project‑wide for anything needing determinism | Kept | `01-CONTEXT.md:50` | libstdc++ implementation is version‑dependent |

---

## Phase 2 — W‑TinyLFU Core

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 2‑D01 | A | W‑TinyLFU is byte‑bounded throughout (1% window / 99% main / 80% protected / 20% probation in bytes) | Kept | `02-CONTEXT.md:33`, `include/wtinylfu.h` | Mirrors other 5 policies' byte‑bounded contract |
| 2‑D02 | A | CMS width = `nextpow2(n_objects_hint)` where `n_objects_hint = capacity_bytes / avg_object_size_from_workload_stats` | Kept | `02-CONTEXT.md:34`, `src/main.cpp` | Threaded from `workload_stats.cpp` pre‑scan |
| 2‑D03 | A | CMS depth = 4; aging threshold = `10 × (width × depth)` accesses | Kept | `02-CONTEXT.md:35` | Locked from research/STACK.md L5; deliberately deviates from Caffeine's `10 × maxSize` |
| 2‑D04 | T | Standalone test binary `tests/test_wtinylfu.cpp` with own `main()`; new Makefile `test` target | Kept | `02-CONTEXT.md:39` | Pure C++17 `assert()`, no external test framework |
| 2‑D05 | M | Test coverage: CMS basics, aging cadence, hot‑object‑survives‑scan, determinism | Kept | `02-CONTEXT.md:40-44` | All 4 tests PASS in `make test`; Phase 4 extended with `test_doorkeeper` |
| 2‑D06 | T | No third‑party test framework (no Catch2, googletest) | Kept | `02-CONTEXT.md:45` | Matches "no external deps" project constraint |
| 2‑D07 | T | `make test` uses separate `build/test/` object dir; `make && make test` doesn't invalidate main cache_sim | Kept | `02-CONTEXT.md:46` | Phase 4 `test_doorkeeper` follows same convention |
| 2‑D08 | A | Mirror Caffeine v3.1.8 byte‑for‑byte; pull source pre‑implementation; lock D‑08a..D‑08e edge cases | Kept | `02-CONTEXT.md:50-55`, `02-01-CAFFEINE-NOTES.md` | 6 deliberate deviations documented |
| 2‑D08a | A | Empty probation segment → candidate admitted unconditionally | Kept | `02-CONTEXT.md:51` | Deviation from Caffeine's protected/window victim‑escalation |
| 2‑D08b | A | Main SLRU has spare byte capacity → candidate admitted unconditionally | Kept | `02-CONTEXT.md:52` | Only run admission test when main is at‑or‑over budget |
| 2‑D08c | A | Probation→protected promotion fires on ANY hit during probation residency (Caffeine default, not paper's "second hit" rule) | Kept | `02-CONTEXT.md:53` | |
| 2‑D08d | A | Protected overflow on promotion → demoted protected LRU‑tail entry → probation MRU (not tail) | Kept | `02-CONTEXT.md:54` | Caffeine's `reorderProbation` behavior |
| 2‑D08e | A | Admission test tie (`freq(candidate) == freq(victim)`) → reject candidate | Kept | `02-CONTEXT.md:55` | Deviates from Caffeine's 1/128 hash‑DoS random admit (no adversarial threat model in our setting) |
| 2‑D09 | W | Pre‑work task explicitly fetches Caffeine source + diffs against project; flags every deviation with justification | Kept | `02-CONTEXT.md:57`, `02-01-CAFFEINE-NOTES.md` | The single most valuable workflow decision in the project |
| 2‑D10 | A | CMS self‑manages aging; public API `record/estimate/reset/force_age` (force_age = test‑only hook) | Kept | `02-CONTEXT.md:62-65` | `force_age()` enables D‑05 deterministic aging test |
| 2‑D11 | A | CMS uses FNV‑1a from `hash_util.h` with 4 existing seeds; one FNV call per row | Kept | `02-CONTEXT.md:66` | Reuses Phase 1's `FNV_SEED_A..D` |
| 2‑L01 | T | Header‑only C++17 for `wtinylfu.h` and `count_min_sketch.h`; no new external deps | Kept | `02-CONTEXT.md:70` | |
| 2‑L02 | F | Mirror Caffeine, NOT paraphrase paper | Kept | `02-CONTEXT.md:71` | Drives D‑08 |
| 2‑L03 | T | Roll our own CMS; rejected xxhash/cityhash/wyhash/cm‑sketch lib | Kept | `02-CONTEXT.md:72` | Project's no‑external‑deps constraint |
| 2‑L04 | A | CMS counter width 4 bits, depth 4 (Caffeine standard) | Kept | `02-CONTEXT.md:73` | |
| 2‑L05 | A | Aging cadence: halve every counter after every `10 × (width × depth)` records | Kept | `02-CONTEXT.md:74` | Verified against `FrequencySketch.java` during pre‑work |
| 2‑L06 | A | 1% window LRU + 99% main SLRU (80% protected / 20% probation) — Caffeine defaults | Kept | `02-CONTEXT.md:75` | NO hill‑climbing |
| 2‑L07 | A | Admission test: `freq(candidate) > freq(victim)`; ties reject candidate | Kept | `02-CONTEXT.md:76` | |
| 2‑L08 | S | Hill‑climbing adaptive window tuner OMITTED | Kept (deferred) | `02-CONTEXT.md:77` | Permanent omission; do not revisit |
| 2‑L09 | S | Doorkeeper DEFERRED to Phase 4 | Kept (deferred until P4) | `02-CONTEXT.md:78` | Implemented as ablation in Phase 4 |
| 2‑L10 | A | Reuse `hash_util.h` from Phase 1 with 4 seeds | Kept | `02-CONTEXT.md:79` | |
| 2‑L11 | A | `wtinylfu.h` is subordinate header included from `cache.h`; `count_min_sketch.h` is peer for standalone testability | Kept | `02-CONTEXT.md:80` | |
| 2‑L12 | A | **Stats single‑source invariant** — only `WTinyLFUCache` records to `CacheStats`; private sub‑lists never touch stats | Kept | `02-CONTEXT.md:81`; grep‑gated everywhere | Most cited invariant in the project; preserved through Phases 3‑5 |
| 2‑L13 | W | Pre‑work (task 0): pull Caffeine v3.x source; verify formulas; capture edge‑case rules | Kept | `02-CONTEXT.md:82`, `02-01-CAFFEINE-NOTES.md` | Output: 549‑line Caffeine notes; blocked implementation tasks until committed |
| 2‑R01 | M | Condition B regression guard: ONE‑SIDED `(WTLFU − LRU) / LRU ≤ 0.02`, not two‑sided `abs(...) ≤ 0.02` | **Revised** mid‑Plan 02‑06 | `STATE.md:86`, `scripts/check_wtlfu_acceptance.py` | At α=0.6, W‑TinyLFU beats LRU by 7.84%; two‑sided would mark this as failure (opposite of intent) |

---

## Phase 3 — CourtListener Trace Collection & Replay Sweep

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 3‑D01 | M | 80/20 metadata‑vs‑full opinion split via `?fields=` query parameter; per‑request random draw seeded for determinism | Kept | `03-CONTEXT.md:32`, `scripts/collect_court_trace.py` | Source of Court's long‑tail size distribution |
| 3‑D02 | A | Minimal field set for 80% calls: `id, absolute_url, type, date_filed, author_id` | Kept | `03-CONTEXT.md:33` | Target response ~1‑5 KB |
| 3‑D03 | S | 80/20 applies only to `/opinions/`; dockets/clusters/courts always default response | Kept | `03-CONTEXT.md:34` | Keeps control surface narrow |
| 3‑D04 | M | CSV `size` column = actual `len(response.content)`, regardless of content | Kept | `03-CONTEXT.md:35` | If 20%‑full opinion has `plain_text=null`, row records true size; no retry |
| 3‑D05 | S | Equal 25% per endpoint (5,000 successful rows each) | Kept | `03-CONTEXT.md:39` | Predictable workload characterization |
| 3‑D06 | M | Keep pilot's ID ranges for production; <60% on first 500 of any endpoint → narrow by 33% | Kept (unused) | `03-CONTEXT.md:40` | Pilot success rates 90/74/90/100 acceptable; fallback never fired |
| 3‑D07 | M | 20K target = 20K successful rows in CSV; collector keeps issuing until `wc -l ≥ 20,001` | Kept | `03-CONTEXT.md:43` | Actual: ~24K issued at ~85% success; ~9h wall‑clock |
| 3‑D08 | A | CSV append‑per‑row with `flush()` after every successful request | Kept | `03-CONTEXT.md:44` | Allows resume on crash without losing in‑flight work |
| 3‑D09 | A | `--resume` flag reads existing CSV, counts per endpoint, computes remaining targets | Kept (unused) | `03-CONTEXT.md:45` | Without `--resume`, refuses to overwrite non‑empty CSV |
| 3‑D10 | M | Failed requests (404/403/429/network) skipped from trace CSV; counted in `collection_report.txt` tally | Kept | `03-CONTEXT.md:46` | Matches Phase 1 D‑08 + Congress trace semantics |
| 3‑D11 | M | 429 handling: Retry‑After + exponential ramp `[0, 30, 90]`; 5 consecutive 429s → hard‑stop with FATAL diagnostic | Kept | `03-CONTEXT.md:47` | Per‑endpoint counter; clamps Retry‑After to [0, 120] |
| 3‑D12 | M | Sweep grid identical to Congress (α∈{0.6..1.2}, cache_frac{0.001..0.1}); zero simulator changes | Kept | `03-CONTEXT.md:51` | Direct cross‑workload comparability for Phase 5 |
| 3‑D13 | M | Workload pre‑characterization runs in Phase 3 (lightweight); `workload_stats.json` written before sweep | Kept | `03-CONTEXT.md:52` | Catches size‑distribution surprises before 10‑min sweep |
| 3‑D14 | A | Output layout under `results/court/` mirrors Congress exactly; flat layout, no subdirs | Kept | `03-CONTEXT.md:53` | Followed by Phase 4 ablations and Phase 5 compare/ |
| 3‑D15 | A | `traces/court_trace.csv` committed to git (~1.2 MB) | Kept | `03-CONTEXT.md:57` | Locks dataset against CourtListener API drift; deviates from default `traces/*` gitignore via affirmative re‑include |

---

## Phase 4 — SHARDS Large‑Scale Validation & Ablations

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 4‑D01 | M | Keep 0.01% sampling rate with flagged caveat (100 samples vs 200 floor); `n_samples` column makes caveat grep‑visible | Kept | `04-CONTEXT.md:46`, `shards_convergence.csv` schema | Better than dropping the data point; honesty in figure caption |
| 4‑D02 | M | Self‑convergence MAE reported with 10% as reference (3 rows: 0.01%/0.1%/1% all vs 10%); not adjacent‑pair, not pairwise matrix | Kept | `04-CONTEXT.md:47` | Direct monotone‑convergence claim from the table |
| 4‑D03 | M | Parallel 50K oracle regime via existing `--shards-exact` path; first 50K of 1M trace; `shards_error.csv` schema unchanged | Kept | `04-CONTEXT.md:48` | Two regimes side‑by‑side: oracle MAE at 50K + self‑convergence at 1M |
| 4‑D04 | M | MAE alignment via `build_mrc(max_cache_size=unique_objects, num_points=100)` uniform 100‑point grid across all rates | Kept | `04-CONTEXT.md:49` | Pointwise MAE without interpolation |
| 4‑D05 | A | Doorkeeper as **pre‑CMS record filter** (paper‑faithful), NOT admission‑gate short‑circuit | Kept (overrides earlier ARCHITECTURE.md plan) | `04-CONTEXT.md:53` | Einziger‑Friedman §4.3 semantic; explicitly overrides architecture pattern 3 |
| 4‑D06 | A | Doorkeeper bit‑array length = `4 × n_objects_hint` (4 bits per element); FPR target ~13% | Kept | `04-CONTEXT.md:54`, `include/doorkeeper.h` | Reuses CMS's `n_objects_hint` |
| 4‑D07 | A | Doorkeeper hash: Kirsch‑Mitzenmacher double‑hashing on `FNV_SEED_A` + `FNV_SEED_B`; 2 hashes (not k>2) | Kept | `04-CONTEXT.md:55` | Reuses Phase 1 hash_util.h |
| 4‑D08 | A | DK‑variant via policy string `wtinylfu-dk`; ctor `(cap, hint, use_doorkeeper=false)` defaults preserve Phase 2 | Kept | `04-CONTEXT.md:56` | One make_policy branch; baseline wtinylfu unchanged |
| 4‑D09 | A | CMS `on_age` callback (`std::function<void()>`) wires DK reset; default empty = zero overhead | Kept | `04-CONTEXT.md:57` | Aging stays aligned between CMS and DK |
| 4‑D10 | A | DK‑on variant uses same CMS in admission; DK only gates what's recorded into CMS | Kept | `04-CONTEXT.md:58` | Keeps ablation interpretable: "same admission, different counting" |
| 4‑D11 | A | S3‑FIFO `small_frac` ctor param + 3 policy strings (`s3fifo-5`, `s3fifo-10`, `s3fifo-20`); legacy `s3fifo` aliases `s3fifo-10` | Kept | `04-CONTEXT.md:62` | Single ablation sweep: `--policies s3fifo-5,s3fifo-10,s3fifo-20` |
| 4‑D12 | A | SIEVE `promote_on_hit` ctor flag + `sieve-noprom` policy string; legacy `sieve` unchanged | Kept | `04-CONTEXT.md:63` | One‑line guard at `cache.h:413` |
| 4‑D13 | M | Ablation sweeps fix cache at 1% of working set (matches Phase 2 alpha‑sensitivity convention) | Kept | `04-CONTEXT.md:64` | Plus full alpha grid for parameter‑sensitivity |
| 4‑D14 | M | Ablation sweeps run on BOTH workloads (Congress + Court) | Kept | `04-CONTEXT.md:65` | Per ROADMAP SC‑4; output pairs `results/{congress,court}/ablation_*.csv` |
| 4‑D15 | A | `traces/shards_large.csv` gitignored, regenerated on demand (~10s) | Kept | `04-CONTEXT.md:69` | Deterministic under seed=42; no API‑drift protection needed |
| 4‑D16 | A | Output layout: `shards_mrc.csv` + new `shards_convergence.csv` schema; `shards_error.csv` schema unchanged | Kept | `04-CONTEXT.md:70-74` | New schema captures D‑01 caveat via `n_samples_compared` column |
| 4‑D17 | W | Dedicated Makefile targets per axis (`shards-large`, `ablation-{s3fifo,sieve,doorkeeper}`); independent of Phase 3's `WORKLOAD=`/`TRACE=` plumbing | Kept | `04-CONTEXT.md:76` | Phase 3's `run-sweep` target untouched; phase‑04 composition target added |
| 4‑D18 | A | One src/main.cpp change: `--shards-rates` CLI flag replacing hardcoded `{0.001, 0.01, 0.1}` | Kept | `04-CONTEXT.md:77` | Default value preserves Phase 1 back‑compat |
| 4‑D19 | W | Four independent work axes — plan in parallel waves; no inter‑axis dependencies except Doorkeeper integration (B Part 2 depends on B Part 1) | Kept | `04-CONTEXT.md:81-86` | Wave 1 = Axes A/B Part 1/C/D; Wave 2 = Axis B Part 2 |

---

## Phase 5 — Cross‑Workload Analysis Infrastructure

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 5‑D01 | M | Regime definitions reuse existing grid cells: small=0.001 only, high‑skew α∈{1.0, 1.1, 1.2}, mixed‑sizes=Court byte‑MRC, OHW=empirical higher‑OHW workload | Kept | `05-CONTEXT.md:67-72` | No arbitrary thresholds for the paper to defend |
| 5‑D02 | M | Welch's unequal‑variance t‑test via `scipy.stats.ttest_ind(equal_var=False)`; flag `n.s.` if p ≥ 0.05 | Kept | `05-CONTEXT.md:75-76`, `scripts/compare_workloads.py` | First scipy use in codebase |
| 5‑D03 | M | CI bands on plots = mean ± 1σ via `fill_between(...alpha=0.2)` | Kept | `05-CONTEXT.md:80` | Literal to ROADMAP SC‑2 |
| 5‑D04 | F | 4 cross‑workload plot functions: `compare_mrc_2panel` (canonical paper hero), `compare_policy_delta`, `compare_mrc_overlay`, `winner_per_regime_bar` | Kept | `05-CONTEXT.md:84-90` | All 4 land in `results/compare/figures/` |
| 5‑D05 | M | Multi‑seed coverage = full grid (6 policies × 13 cells × 2 workloads × 5 seeds = 780 sim cells) | Kept | `05-CONTEXT.md:96-100` | Wall‑clock 58.2s, 30× under 30‑min ceiling |
| 5‑D06 | A | `--seed N` CLI flag on `cache_sim`; threaded into `generate_zipf_trace`, `replay_zipf`, `prepare_objects`; `--emit-trace` literal `42` preserved | Kept | `05-CONTEXT.md:103-106`, `src/main.cpp:140` | Single C++ change in Phase 5; back‑compat preserved byte‑identically |
| 5‑D07 | A | Regenerate Congress workload_stats.json (Phase 3 only ran it for Court) | Kept | `05-CONTEXT.md:110-113` | Wave 1 task; gitignored output |
| 5‑D08 | F | Tables emit primary markdown + secondary JSON; LaTeX deferred to Phase 6 pandoc one‑liner | Kept (LaTeX deferred) | `05-CONTEXT.md:117-119` | Markdown landed in `workload_characterization.md` and `winner_per_regime.md` |
| 5‑D09 | A | `results/compare/` layout: `multiseed/` (raw per‑seed) + `aggregated/` (mean+std+p) + `figures/` + 4 markdown/JSON tables | Kept | `05-CONTEXT.md:122-141` | All gitignored per D‑15 (Phase 3) |
| 5‑D10 | M | Acceptance gate `scripts/check_anal_acceptance.py` mirrors Phase 2 `check_wtlfu_acceptance.py` pattern; 4 SC structurally verified | Kept | `05-CONTEXT.md:146-152` | Exit 0 = phase complete |

---

## Phase 6 — Writeup & Demo

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| 6‑D01 | F | **Lead the paper with the surprise finding** — page‑1 hero figure + W‑TinyLFU‑dominates‑Court vs ties‑on‑Congress headline | Kept | `06-CONTEXT.md:24` | Hook‑driven structure responds to professor's "explain why" midpoint ask |
| 6‑D02 | F | Hybrid formal + first‑person tone — third for results/methodology, first for justification + DOC‑03 | Kept | `06-CONTEXT.md:25` | Standard CS class‑report register |
| 6‑D03 | F | One deep finding + breadth elsewhere — SIEVE≈W‑TinyLFU‑on‑Congress mechanism is 1‑2 page §5 centerpiece | Kept | `06-CONTEXT.md:26` | The bridge from "describe" to "explain mechanism" |
| 6‑D04 | F | Figure‑led opening on page 1 — `compare_mrc_2panel.pdf` with caption pointing at high‑α divergence | Kept | `06-CONTEXT.md:27` | |
| 6‑D05 | F | Practitioner decision tree lives in conclusion — `winner_per_regime_bar.pdf` + 4‑rule table | Kept | `06-CONTEXT.md:28` | The take‑home payoff |
| 6‑D06 | F | DOC‑03 decision‑log format — chronological "Claude suggested X, I chose Y because Z" | Kept | `06-CONTEXT.md:32` | Matches professor's "what worked and didn't" framing |
| 6‑D07 | F | Audited PROCESS.md bug count, NOT pinned to literal "9" | Kept | `06-CONTEXT.md:33` | Audit at write time landed at 21 (9 body + 12 Phase 5 review) |
| 6‑D08 | F | Balanced‑but‑careful honesty on failures — concrete what‑didn't‑work moments framed as learning | Kept | `06-CONTEXT.md:34` | Avoids sanitized successes‑only tone |
| 6‑D09 | F | Scope: Claude Code + GSD planning/orchestration meta‑layer | Kept | `06-CONTEXT.md:35` | Signals sophisticated AI collaboration |
| 6‑D10 | F | Research‑phase discussion gets equal weight with implementation | Kept | `06-CONTEXT.md:36` | Whole‑project view: CourtListener vs PACER, replay‑Zipf, 6th policy choice |
| 6‑D11 | F | 6‑8 figures main body + 10‑12 appendix; main body narrative, appendix for reproducibility | Kept (slightly exceeded) | `06-CONTEXT.md:39` | Final: ~10 main + 10 appendix; D‑14 dedicated ablation section justifies main‑body overshoot |
| 6‑D12 | F | Must‑have main‑body figures: `compare_mrc_2panel`, `winner_per_regime_bar`, `shards_mrc_overlay` | Kept | `06-CONTEXT.md:40-43` | All embedded |
| 6‑D13 | F | 2nd‑tier main‑body figures: `alpha_sensitivity` (×2 workloads), `ablation_doorkeeper` (×2), `workload.pdf` (×2) | Kept (after revision) | `06-CONTEXT.md:44-47`, plan‑checker W‑4 fix | `workload.pdf` initially missed; checker caught; added in revision |
| 6‑D14 | F | Dedicated "Ablations" §7 with all 3 ablation figures together | Kept | `06-CONTEXT.md:48` | Rigor signal |
| 6‑D15 | F | Live 6‑policy sweep on small trace (`./cache_sim` runs visibly, miss‑ratio table prints live, figure renders) | Kept | `06-CONTEXT.md:54` | Demo measured at 4s wall‑clock vs 60s budget |
| 6‑D16 | F | Single full‑demo screen recording as backup; cut to recording if live demo fails | Kept | `06-CONTEXT.md:55` | 4.2 MB committed to `docs/demo-backup.mov` |
| 6‑D17 | A | demo.sh self‑sources `.env` (sets `DYLD_LIBRARY_PATH` + `PYTHONPATH` + API keys) | Kept | `06-CONTEXT.md:56` | Single‑command invocation on target laptop |
| 6‑D18 | M | 3 rehearsals logged to `demo-rehearsal.log`; capture wall‑clock + stdout per run | Kept | `06-CONTEXT.md:57`, `demo-rehearsal.log` | Wall‑clocks: 4s/3s/4s; all PASS verdicts |
| 6‑D19 | M | ~5K‑request pre‑loaded demo trace = first 5K verbatim from `congress_trace.csv` | Kept | `06-CONTEXT.md:58` | Branch A (verbatim) chosen over Branch B (seeded sample) for determinism |

---

## Cross‑Phase Workflow Decisions (GSD Meta‑Layer)

| ID | Cat | Decision | Status | Evidence | Notes |
|---|---|---|---|---|---|
| W‑01 | W | All phases follow research → discuss‑phase → plan‑phase → execute‑phase → verify pipeline | Kept | `.planning/` skill structure | 6 phases, 33 plans, all atomic commits |
| W‑02 | W | Worktree‑isolated parallel execution within waves where files don't overlap | Kept | Phase 4 axes A/B/C/D, Phase 5 plans 04+05, Phase 6 plans 04+05 | Sequential dispatch with `run_in_background: true` to avoid `.git/config.lock` contention |
| W‑03 | W | Locked CONTEXT.md per phase before planning begins; decisions are durable inputs | Kept | 6 CONTEXT.md files (1090 total lines) | Plan checker verifies plans honor locked decisions |
| W‑04 | W | Plan checker iteration loop max 3 rounds; revision targets specific issues | Kept | Phase 6 iteration 2 → PASS | All phases passed within 1‑2 iterations |
| W‑05 | W | Atomic per‑task commits in execute phase; SUMMARY.md committed before worktree removal | Kept | All 33 plan summaries on git | Worktree force‑remove pattern preserves uncommitted SUMMARY.md via safety net |
| W‑06 | W | Phase verification = goal‑backward check against SC + locked decisions, not just task completion | Kept | 6 VERIFICATION.md files | Phase 6 verifier confirmed 19/19 decisions honored |
| W‑07 | M | Code review gate after execution; deferred fixes captured in CONTEXT decisions log | Kept | Phase 5 WR‑01/WR‑02 deferred to v2 | Latent‑coupling issues identified but non‑manifest |

---

## Deferred Items (V2 / Out of Scope)

| ID | Cat | Decision | Status | Evidence | Why Deferred |
|---|---|---|---|---|---|
| V2‑01 | M | Caffeine trace cross‑validation (±2% agreement) | Deferred | `.planning/STATE.md:121`, `06-CONTEXT.md:170` | Needs access to published Caffeine benchmark traces |
| V2‑02 | A | LHD or AdaptSize as 7th policy (size‑aware eviction) | Deferred | `STATE.md:122`, `06-CONTEXT.md:171` | Scope containment for Milestone 2 |
| V2‑03 | M | Third trace domain (SEC EDGAR) — public‑records trilogy | Deferred | `STATE.md:123`, `06-CONTEXT.md:172` | Two domains enough for cross‑workload story |
| V2‑04 | M | Multi‑seed α∈{1.3, 1.4, 1.5} extension on Congress | Deferred | `06-CONTEXT.md:175` | Single‑seed crossover test exists; multi‑seed is cheap (~30s) but not blocking |
| V2‑05 | M | Multi‑seed byte‑MRC aggregation | Deferred | `06-CONTEXT.md:176` | One‑line change to compare_workloads.py; deferred for scope |
| V2‑06 | A | Code review WR‑01 + WR‑02 latent‑coupling fixes in plot_results.py | Deferred | `STATE.md:139-140`, `06-CONTEXT.md:177` | Only manifests if future work adds ablation variants to multi‑seed sweep |
| OOS‑01 | S | Production‑grade caching system or real storage integration | Out of scope | `PROJECT.md:70` | This is a simulator |
| OOS‑02 | S | Tracking real server‑side traffic | Out of scope | `PROJECT.md:71` | Congress.gov + PACER don't publish access logs |
| OOS‑03 | S | Multi‑tier or distributed caching | Out of scope | `PROJECT.md:72` | Single‑tier object cache only |
| OOS‑04 | S | Cost‑based eviction (GDSF, LFUDA) beyond W‑TinyLFU | Out of scope | `PROJECT.md:73` | Scope containment |
| OOS‑05 | S | Threading / concurrent cache access | Out of scope | `PROJECT.md:74` | Simulator is single‑threaded by design |
| OOS‑06 | S | Hill‑climbing adaptive window tuner for W‑TinyLFU | Permanently omitted | `02-CONTEXT.md:77` (L‑8) | Multi‑week implementation tangent |
| OOS‑07 | S | Doorkeeper at admission‑gate placement (vs pre‑CMS record filter) | Rejected | `04-CONTEXT.md:53`, available as v2 secondary ablation if challenged | Paper‑faithful pre‑CMS placement chosen |

---

## Most‑Cited Invariants (Decisions That Constrained Multiple Phases)

These are the load‑bearing decisions that downstream phases either explicitly inherited or were grep‑gated against:

1. **L‑12 (Phase 2): Stats single‑source invariant** — `grep -cE "record\(\s*(true|false)" include/wtinylfu.h` must equal 4. Verified across Phases 2, 3, 4 (every plan). Survived Doorkeeper integration without modification.

2. **D‑14 (Phase 1): `std::hash` banned** — applies to all PRNG seeding work (Phase 5 D‑06 `--seed` plumbing follows this); FNV‑1a from `hash_util.h` is the only sanctioned hash for determinism.

3. **D‑15 (Phase 3): `traces/` committed exception, `results/` gitignored** — Phase 4 followed for `shards_large.csv` (gitignored), Phase 5 followed for `compare/` outputs (gitignored).

4. **L‑6 (Phase 2): Caffeine 1%/99% + 80/20 SLRU defaults, NO hill‑climbing** — survived through Phase 4 ablations (parameter sweep was scoped to S3‑FIFO and SIEVE, not W‑TinyLFU's window split).

5. **D‑08 (Phase 2): Caffeine‑mirrored admission edge cases (D‑08a..e)** — Phase 4 Doorkeeper integration (D‑10) explicitly preserves these by adding pre‑CMS filtering, never touching admission logic.

6. **KD‑05 (Project): Replay‑Zipf as primary analysis** — every cross‑workload claim in Phases 3‑6 uses replay‑Zipf, not raw trace replay. Phase 5 reconfirmed with empirical α_mle=0.231 on raw Congress.

---

## Decisions That Were Revised or Overridden

Three decisions changed mid‑project. Each is worth knowing because it represents a real learning moment:

1. **Phase 2 R‑01 — Condition B regression guard semantics changed mid‑Plan 02‑06.** Originally specified as two‑sided `abs(WTLFU − LRU) / LRU ≤ 0.02`. Implemented one‑sided `(WTLFU − LRU) / LRU ≤ 0.02` after observing W‑TinyLFU beats LRU by 7.84% at α=0.6 — the original spec would have flagged outperformance as a failure. Caught at the acceptance‑gate stage, not in code review.

2. **Phase 4 D‑05 — Doorkeeper placement overrode an earlier ARCHITECTURE.md plan.** The architecture research document had originally suggested Doorkeeper as an admission‑gate short‑circuit (Pattern 3). Phase 4 overrode this with a paper‑faithful pre‑CMS record filter placement, citing Einziger‑Friedman §4.3. The override is documented in `04-CONTEXT.md:53` with the rationale.

3. **Phase 5 D‑02 — α_mle correction.** The Phase 5 planner initially misread a regression test result ("0.797 MLE recovers from synthetic α=0.8") as raw‑trace characterization. The actual raw Congress trace is α_mle=0.231 (near‑uniform). Caught at write time during Plan 05‑02. The 0.231 figure is what landed in the paper and is consistent with PROJECT.md's "random queries with near‑zero temporal locality" framing.

---

*Generated 2026‑04‑26 from `.planning/PROJECT.md`, six per‑phase `CONTEXT.md` files (1,090 lines), `.planning/STATE.md` accumulated context, and the 33 plan SUMMARY.md files. ~108 decisions inventoried; ~95 included here (cosmetic decisions like marker‑color choices omitted).*
