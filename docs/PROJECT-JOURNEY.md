# Project Journey — civicache

**A chronological narrative of every decision, surprise, and turn taken across Milestone 2 of the civicache project — from kickoff (2026‑04‑16) to submission‑ready delivery (2026‑04‑22).**

This document is paired with `DECISIONS-MATRIX.md`. Use this for the *story*; use the matrix when someone drills into "why did you pick X over Y".

---

## Pre‑Milestone — Where Things Stood (Milestone 1)

Coming into Milestone 2, the base simulator already worked: five eviction policies (LRU, FIFO, CLOCK, S3‑FIFO, SIEVE) implemented in C++17 with a Makefile build, a 20K‑request Congress.gov trace collected via Python, replay‑Zipf re‑sampling because the raw trace had near‑zero locality, SHARDS sampling with FNV‑1a hashing validated against exact stack distances, MLE α estimation per Clauset et al., and a matplotlib plotting pipeline. Three rounds of code review had already caught nine bugs. The professor's midpoint feedback was positive on design but explicitly asked for **(a)** an AI‑use report and **(b)** more depth on *why* one algorithm wins another.

The Milestone 2 plan was: add a sixth policy (W‑TinyLFU), add a second real workload (CourtListener legal API), strengthen SHARDS rigor, build cross‑workload analysis infrastructure, and ship the final paper + AI‑use report + live demo.

---

## Phase 1 — Enabling Refactors & CourtListener Pilot (2026‑04‑18)

**Goal:** Unblock everything downstream by extracting reusable infrastructure and verifying the new data source actually works before committing to a multi‑hour collection run.

**The 6 things this phase did:**
1. Extracted FNV‑1a from `src/shards.cpp` into `include/hash_util.h` with four golden‑ratio‑derived seeds (`FNV_SEED_A..D`) so SHARDS, the upcoming CMS (Phase 2), and the upcoming Doorkeeper (Phase 4) could share one deterministic hash.
2. Banned `std::hash<std::string>` project‑wide for any code path needing reproducibility — libstdc++'s `std::hash` is version‑dependent and silently breaks cross‑machine determinism.
3. Split `replay_zipf` into `prepare_objects()` + `generate_replay_trace()` so the alpha sweep could call dedupe/shuffle once and the per‑α sampler 7×, instead of regenerating the full object list 7×.
4. Added an `accesses_per_sec` column to all simulation CSVs so downstream Pareto plots had the throughput axis.
5. Reorganized `results/` into `{congress, court, shards_large, compare}/` subdirs (created stub directories for the not‑yet‑populated workloads).
6. Registered a CourtListener token, configured `COURTLISTENER_API_KEY` in `.env`, and ran a 200‑request pilot across `/dockets/`, `/opinions/`, `/clusters/`, `/courts/` with a hard ≥70% success gate.

**Key decisions:**
- **CourtListener over PACER.** PACER charges per page; CourtListener (which mirrors PACER via the RECAP archive) gives free, token‑authenticated access at 5K requests/hour. Same legal‑public‑records contrast for the cross‑workload story; zero billing risk.
- **Pilot phase exists at all.** Could have skipped straight to the 20K production collection — but a 6‑hour run that fails halfway through because one endpoint is gated would burn an entire workday. The 200‑request pilot caught (and would have caught) gated endpoints, ID‑range issues, and pacing problems for ~5 minutes of runtime cost.
- **Throughput measured per (policy, cache‑size) cell** with `std::chrono::steady_clock` wall‑clock, not CPU time and not time‑series. Simpler, portable, and signal is strong at 500K‑request scale.

**What surprised us:** All four pilot endpoints passed the gate first try (90% / 74% / 90% / 100% success). No 403s anywhere — the planning concern that some endpoints might be gated turned out to be unfounded. Got to skip the fallback ID‑range narrowing logic entirely.

**What this enabled:** Phase 2 could now build CMS on a shared FNV‑1a, Phase 3 could trust the pilot's ID ranges for the production run, and the alpha sweep would now run noticeably faster after the `replay_zipf` refactor.

---

## Phase 2 — W‑TinyLFU Core (2026‑04‑19)

**Goal:** A working, validated W‑TinyLFU policy plugged into the existing CachePolicy hierarchy — exhibiting the "hot object survives a scan" invariant and the expected α‑regime relationship to LRU on Congress replay.

**The 6 plans:**
1. **Caffeine pre‑work** — pull `FrequencySketch.java` and `BoundedLocalCache.java` from Caffeine v3.1.8, lock the CMS update rule and edge‑case admission rules **before** writing any C++. Output: `02-01-CAFFEINE-NOTES.md` documenting six deliberate deviations from Caffeine's reference.
2. `include/count_min_sketch.h` — 4‑bit counters, depth 4, width = `nextpow2(capacity_objects)`, conservative update, periodic halving every 10×W accesses.
3. `include/wtinylfu.h` + integration into `cache.h` and `make_policy()` — 1% window LRU + 99% main SLRU (80% protected / 20% probationary) with TinyLFU admission via the CMS.
4. `tests/test_wtinylfu.cpp` standalone test binary — pure C++17 `assert()`, no Catch2/googletest dependency. Tests CMS basics, the hot‑object‑survives‑scan invariant, aging cadence, and determinism across reruns.
5. Plotting integration — added W‑TinyLFU to `POLICY_COLORS` (brown `#8c564b`) and `POLICY_MARKERS` (`P` filled plus). Picked colors carefully to avoid collision with SIEVE's existing purple and S3‑FIFO's existing diamond.
6. WTLFU‑05 validation sweep — `scripts/check_wtlfu_acceptance.py` with three grep‑discoverable acceptance conditions (A1 mrc winning, A2 alpha‑sensitivity winning, B regression guard at α=0.6). Exit 0 ⇒ phase complete.

**Key decisions:**
- **Caffeine v3.1.8 is the reference, the paper is secondary.** When Caffeine source disagrees with the Einziger‑Friedman TinyLFU paper, Caffeine wins. The "Caffeine‑compatible" claim is stronger than "paper‑faithful" for a class‑project audience.
- **Roll our own CMS.** Rejected `xxhash`, `cityhash`, `wyhash`, and the `cm‑sketch` GitHub library. Project requirement is C++17 stdlib only; adding any external dep would force a CMakeLists rewrite.
- **No hill‑climbing adaptive window tuner.** Permanently omitted — Caffeine has it; we don't. Static 1%/99% split keeps the policy comparable across cache sizes and avoids a multi‑week implementation tangent.
- **Stats single‑source invariant.** Only `WTinyLFUCache::access()` calls `record(hit, size)` — its private window/probation/protected sub‑lists never touch `stats`. Enforced by a grep gate: `grep -cE "record\(\s*(true|false)" include/wtinylfu.h` must equal 4 forever.
- **Condition B regression guard semantics changed mid‑review.** WTLFU‑05's "within ±2% of LRU at α=0" was implemented as a *one‑sided* check `(WTLFU − LRU) / LRU ≤ 0.02` rather than a two‑sided `abs(...) ≤ 0.02`. Reason: at α=0.6, W‑TinyLFU beats LRU by ~7.84% — a two‑sided check would mark this as a failure, which is opposite of intent. The guard is a regression safety net against LFU‑family policies *underperforming* LRU on flat workloads, not a penalty for outperformance.

**What surprised us:** W‑TinyLFU monotonically dominated LRU across the entire α∈{0.6..1.2} grid with the gap *growing* from 7.84% at α=0.6 to 21.55% at α=1.2 — exactly the TinyLFU‑theory prediction that admission filters dominate when there's a hot tail to identify.

**What this enabled:** Phase 3's 6‑policy sweep could now legitimately compare W‑TinyLFU against the five baselines on a *new* workload, and Phase 4 had a real algorithm to ablate.

---

## Phase 3 — CourtListener Trace Collection & Replay Sweep (2026‑04‑19)

**Goal:** A real ≥20K‑request CourtListener trace on disk, plus a full 6‑policy replay‑Zipf sweep on it, producing the second‑workload data needed for Phase 5's cross‑workload comparison.

**The 3 plans:**
1. **Production collector** — `scripts/collect_court_trace.py`, a 609‑line sibling (not replacement) of the pilot script. Ten‑row smoke‑verified before committing the full run.
2. **Overnight 20K collection** — committed `traces/court_trace.csv` (20,001 lines, 5K rows per endpoint) after an 8h 56m runtime. All 4 endpoint families cleared the ≥70% success gate.
3. **6‑policy sweep + figures** — `make run-sweep WORKLOAD=court TRACE=traces/court_trace.csv` + `make plots WORKLOAD=court`, producing `results/court/{mrc.csv, alpha_sensitivity.csv, workload_stats.json, figures/*.pdf}`. Congress sweep behavior preserved byte‑identical for back‑compat.

**Key decisions:**
- **80/20 metadata‑vs‑full split on opinions only** via the CourtListener `?fields=` query parameter. 80% of opinion calls strip the `plain_text` body (1–5 KB responses); 20% fetch the full document (20–500 KB). Dockets, clusters, and courts always fetch the default response. This decision is what gives Court its long‑tail size distribution — a deliberately‑constructed contrast with Congress's near‑uniform sizes.
- **Equal 25% per endpoint** in the 20K target. Predictable workload characterization; clean symmetry; if any endpoint underperformed mid‑run the fallback would narrow its ID range by 33%.
- **5‑consecutive‑429 hard‑stop** with a one‑line FATAL diagnostic and non‑zero exit. Better to fail loudly after ~5 minutes of throttling than keep hammering the API for an hour. The `--resume` flag handles continuation after the throttle window clears.
- **`traces/court_trace.csv` committed to git.** ~1.2 MB, same order as the existing committed Congress trace. Locks the dataset against CourtListener API drift (RECAP ingests new filings constantly, so ID ranges shift) and preserves grader reproducibility.
- **404s skipped from the trace, counted in the report.** Failed requests don't enter the CSV (matches Congress trace semantics) but they *do* count in `collection_report.txt`'s per‑endpoint tally.

**What surprised us:** The collection took almost 9 hours instead of the planned 6.1 — the 0.8s base + 0.4s jitter pacing was honest, but network RTT averaged ~0.07s on top of every request. Lesson: budget ~25% headroom on long collection runs.

**What this enabled:** Phase 4 had two real workloads to ablate against, and Phase 5 had `results/court/` populated symmetrically with `results/congress/`.

---

## Phase 4 — SHARDS Large‑Scale Validation & Ablations (2026‑04‑20)

**Goal:** Defensible rigor claims along three independent axes — SHARDS at 1M scale across four sampling rates, Doorkeeper as an ablation variant, and parameter‑sensitivity ablations on S3‑FIFO and SIEVE.

**The 5 plans, executed in 2 waves of independent work axes:**

**Axis A — SHARDS large‑scale (Plan 04‑01).** Generated a 1M‑access synthetic Zipf(α=0.8, 100K objects, seed=42) trace. Added a `--shards-rates` CLI flag replacing the hardcoded `{0.001, 0.01, 0.1}`. Reported 4 sampling rates {0.01%, 0.1%, 1%, 10%} with self‑convergence MAE table (all rates compared against 10% as reference). Parallel 50K oracle regime via the existing `--shards-exact` path so the writeup has both "self‑consistency at 1M" and "exact‑oracle MAE at 50K" numbers. Sanity gate `MAE(1%, 10%) = 0.0378 < 0.05` passed.

**Axis B — Doorkeeper (Plans 04‑02 + 04‑05).** Built `include/doorkeeper.h` as a header‑only Bloom filter with Kirsch‑Mitzenmacher double‑hashing on `FNV_SEED_A` + `FNV_SEED_B`. Integrated as a sibling variant `wtinylfu-dk` (baseline `wtinylfu` stays Doorkeeper‑free per Caffeine precedent). Implemented as a *pre‑CMS record filter* per the Einziger‑Friedman §4.3 paper semantics — first‑touch keys go to the Bloom filter, second‑touch flows through to the CMS. CMS aging fires a callback that clears the Doorkeeper, keeping freshness aligned. Empirical FPR at load=1.0 was 0.0829, within the [0.05, 0.25] sanity band.

**Axis C — S3‑FIFO ratio ablation (Plan 04‑03).** Extended `S3FIFOCache` ctor with `double small_frac=0.1` (default preserves Phase 1). Added three policy variants `s3fifo-5`, `s3fifo-10`, `s3fifo-20`. Headline finding: smaller small‑queue ratio monotonically wins on both workloads, with a 6.3pp gap at Court α=1.2 vs only 1.2pp on Congress — a publishable result against the SOSP'23 paper's 10% default.

**Axis D — SIEVE visited‑bit ablation (Plan 04‑04).** Extended `SIEVECache` ctor with `bool promote_on_hit=true`. New `sieve-noprom` policy variant. Headline finding: SIEVE‑NoProm monotonically loses to SIEVE at every α on both workloads, gap peaks at +15.4pp on Congress (α=1.0) — empirically confirms the NSDI'24 paper's lazy‑promotion claim as the dominant contributor to SIEVE's scan resistance.

**Key decisions:**
- **Keep the 0.01% sampling rate with a flagged caveat** rather than dropping it. At 1M × 0.01% = 100 samples, below Waldspurger's ≥200‑sample floor — but a grep‑visible `n_samples` column in the convergence CSV plus a footnote in the figure caption preserves the data point honestly.
- **Self‑convergence with 10% as reference**, not adjacent‑pair MAE. Three rows: MAE(0.01% vs 10%), MAE(0.1% vs 10%), MAE(1% vs 10%). The monotone‑convergence claim ("as sampling rate rises, MAE shrinks") is directly answerable from the table.
- **Pre‑CMS record filter, not admission‑gate short‑circuit, for Doorkeeper.** The Einziger‑Friedman paper's "Doorkeeper absorbs 50–70% of one‑hit‑wonder CMS pressure" claim is only defensible under pre‑record filtering. The architecture research had originally suggested an admission‑gate placement; we explicitly overrode that with a paper citation.
- **Default ctor parameters preserve back‑compat byte‑identically.** Every new ctor param (`small_frac=0.1`, `promote_on_hit=true`, `use_doorkeeper=false`) defaults to the Phase 1 hardcoded value. The 6‑policy sweep regenerates byte‑for‑byte against pre‑Phase‑4 outputs (only `accesses_per_sec` throughput noise differs, expected).
- **Synthetic 1M trace gitignored, regenerated on demand.** ~45 MB; <10s regen via the C++ `--emit-trace` path with deterministic seed=42. No need to commit 45 MB of regenerable bytes.

**What surprised us:** The Doorkeeper ablation result was *marginal*, not dramatic. Congress saw essentially zero effect (within ±0.22pp noise across all α). Court showed a -0.72pp win at α=1.1 + -0.66pp at α=1.2 but a +0.52pp *loss* at α=0.6. This matches Caffeine's production decision to omit DK by default — and is a stronger story for the paper than "Doorkeeper helps everywhere" would be.

**What this enabled:** Phase 5 had ablation CSVs to consult when explaining mechanisms, and the writeup could honestly claim "every figure has a methodology section that justifies the numbers."

---

## Phase 5 — Cross‑Workload Analysis Infrastructure (2026‑04‑21)

**Goal:** Final comparison artifacts — the numbers and tables the paper is built from. Cross‑workload comparison plots, multi‑seed confidence intervals, workload‑characterization table, and winner‑per‑regime analysis.

**The 6 plans:**
1. **`--seed N` CLI flag** (the single C++ exception this phase) threaded into `generate_zipf_trace`, `replay_zipf`, and `prepare_objects`. Default value preserves Phase 1‑4 byte‑for‑byte. The `--emit-trace` literal `42` at line 182 deliberately preserved for SHARDS‑01 trace provenance.
2. **Regenerate Congress workload_stats.json** (a leftover gap from Phase 3 which only ran the script against Court).
3. **Multi‑seed orchestrator** — `scripts/run_multiseed_sweep.py` runs the full 5‑seed × 6‑policy × 2‑workload × MRC+alpha grid. 10 cache_sim invocations, 20 per‑seed CSVs, 58.2s wall‑clock — 30× under the 30‑min soft ceiling.
4. **Aggregation pipeline** — `scripts/compare_workloads.py` reads the per‑seed CSVs, computes 5‑seed mean ± std + Welch's unequal‑variance t‑test via `scipy.stats.ttest_ind(equal_var=False)`. First scipy use in the codebase. Welch's verified W‑TinyLFU's dominance over LRU on Congress at every α∈{0.6..1.2} with p ∈ [1.2e-06, 8.7e-08].
5. **Cross‑workload plot functions** — 4 new functions in `plot_results.py`: `compare_mrc_2panel` (canonical paper hero with ±1σ bands), `compare_policy_delta`, `compare_mrc_overlay`, `winner_per_regime_bar`.
6. **ANAL‑03/04 tables + acceptance gate** — workload‑characterization table (10 rows, Congress vs Court side‑by‑side) and winner‑per‑regime table (4 regimes × 2 workloads). `scripts/check_anal_acceptance.py` exit‑gate mirroring the Phase 2 pattern.

**Key decisions:**
- **5 seeds is the minimum that makes Welch's t-test credible at p<0.05** without over‑investing in sweep wall‑clock. Single‑seed runs can't distinguish real policy differences from RNG noise; 10 seeds would be 2× the cost for diminishing returns on confidence.
- **Mean ± 1σ visual bands on plots, Welch's t‑test in tables.** Rigor goes where rigor matters — the `n.s.` column in the comparison table is what reviewers will scrutinize; plots stay eyeball‑friendly.
- **BASE_POLICIES restriction on regime analysis.** The 6‑policy main grid is the story; ablations (s3fifo‑5/20, sieve‑noprom, wtinylfu‑dk) have their own Phase 4 figures. Filter applied in `_winner_in_group` to keep zero ablation contamination in `winner_per_regime.{md,json}`.
- **Regimes defined by existing grid cells**, not arbitrary thresholds. Small cache = the smallest existing cache_frac (0.001). High skew = α∈{1.0, 1.1, 1.2}. Mixed sizes = byte‑MRC on Court only (the empirically heavy‑tailed workload). OHW regime = whichever workload has higher OHW ratio. Every definition reuses an existing grid; nothing arbitrary for the paper to defend.

**What surprised us:** The empirical α_mle for the *raw* Congress trace was 0.231, not 0.797 — the planner had misread a regression test result ("0.797 MLE recovers from synthetic α=0.8") as raw‑trace characterization. Caught at write time. The 0.231 figure (near‑uniform raw trace) is consistent with PROJECT.md's explicit "random queries with near‑zero temporal locality" framing and is precisely *why* replay‑Zipf overlay is the only way to get a meaningful policy comparison on Congress data.

Also surprising: SIEVE *won* on Congress high‑skew regime (mean‑across‑3‑alphas), contradicting Phase 2's "W‑TinyLFU dominates" narrative. Cause: at uniform‑ish α≈1.0 with low one‑hit‑wonder pressure, SIEVE's visited‑bit scan resistance edges out W‑TinyLFU's admission filter that has nothing to filter. This *became* the centerpiece of the paper's mechanism deep‑dive.

**Code review findings (deferred):** WR‑01 — `plot_winner_per_regime_bar` in `plot_results.py` doesn't filter to `BASE_POLICIES` while `compare_workloads.py` does. Today this doesn't diverge because the multi‑seed sweep uses default 6 policies; if someone extended it to include ablations, the figure and table would silently disagree. WR‑02 — regime dispatch in `plot_results.py:819-849` has no `else` clause; adding a 5th regime would propagate stale variables. Both deferred to v2 since neither manifests today.

**What this enabled:** Phase 6 had the canonical `compare_mrc_2panel.pdf` (the paper hero), the workload characterization numbers, and a winner‑per‑regime table to build the practitioner decision tree from.

---

## Phase 6 — Writeup & Demo (2026‑04‑22)

**Goal:** The three final deliverables the professor evaluates — class‑report paper PDF, AI‑use report (specifically requested), and a live <60s demo that actually works on the target laptop.

**The 7 plans, executed in 3 waves:**

**Wave 1 (parallel‑ish — Makefile/.gitignore overlap forced sequential):**
1. **Paper LaTeX scaffold** — `docs/DOC-02-final-report.tex` with preamble + 11 `\input{}` stubs + bibliography + `make paper` target. LaTeX over markdown+pandoc because `progress.tex` already builds via `latexmk` on the target laptop (zero environment risk). Plan 06‑01 owns the Makefile `.PHONY` line and declares both `paper` AND `demo` to prevent a parallel‑edit race.
2. **Demo infrastructure** — `traces/demo_trace.csv` (first 5K verbatim rows from `congress_trace.csv` per D‑19) + `demo.sh` sourcing `.env` and setting `DYLD_LIBRARY_PATH` + `make demo` target. Dry‑run measured: 4s wall‑clock, full 6‑policy sweep at 4 cache sizes, miss‑ratio table prints live, figure renders.
3. **DOC‑03 AI‑use report** — chronological decision‑log format. Audited bug count at write time: 9 in PROCESS.md body (Round 1: 4, Round 2: 4, SHARDS denominator: 1) + 12 from Phase 5 code review = 21 total issues. Plan deliberately did *not* hardcode the literal "9" from the midpoint feedback. Coverage spans Claude Code implementation moments, GSD meta‑layer planning/orchestration, and research‑phase decisions (CourtListener vs PACER, picking W‑TinyLFU, choosing replay‑Zipf).

**Wave 2 (parallel — disjoint section files):**
4. **Paper body breadth** — §2 Related Work, §3 Workload Characterization (10‑row table), §4 Policy Comparison (per‑workload α figures), §6 SHARDS Validation (4‑rate table), §7 Ablations (all 3 ablation figures together per D‑14).
5. **Paper depth** — §5 Mechanism Deep‑Dive (the centerpiece — SIEVE‑as‑admission‑filter‑in‑disguise + per‑α gap table + α∈{1.3..1.5} addendum), §8 Byte‑MRC methodology warning (σ=0.21 Court outlier), §9 Conclusion (D‑05 practitioner decision tree + V2 limitations), §10 Reproducibility Appendix (10 figures per D‑11 mandate).

**Wave 3:**
6. **Final PDF build** — `make paper` → 20‑page `docs/DOC-02-final-report.pdf` (681 KB). 4 undefined `\ref{}` warnings caught and auto‑fixed during the build (cross‑plan label naming drift between Plans 04 and 05). Latexmk log check: 0 missing‑figure warnings. Plus README.md updates (W‑TinyLFU row, live‑demo section, docs/ tree, Einziger/Caffeine citations).
7. **Demo rehearsals + screen recording** — the only non‑autonomous plan in the milestone. Three end‑to‑end runs of `demo.sh` on the target laptop logged to `demo-rehearsal.log` (wall‑clocks: 4s / 3s / 4s). Single full screen recording committed to `docs/demo-backup.mov` (4.2 MB, under the 10 MB threshold so committed directly without .gitignore changes).

**Key decisions:**
- **Lead the paper with the surprise finding** (D‑01). Open with the page‑1 hero `compare_mrc_2panel.pdf` and the headline that W‑TinyLFU dominates Court by 4–5pp but ties SIEVE on Congress. The rest of the paper unpacks *why*. Hook‑driven structure directly answers the professor's "explain why one algorithm wins" midpoint ask.
- **One deep finding + breadth elsewhere** (D‑03). The SIEVE≈W‑TinyLFU‑on‑Congress mechanism gets a 1–2 page §5 centerpiece. Everything else (SHARDS validation, ablations, byte‑MRC outlier) gets paragraph‑length treatment. This is the bridge from "describe results" to "explain mechanism" the professor asked for.
- **Decision‑log format for DOC‑03** (D‑06). Chronological log of concrete decisions ("Claude suggested X, I chose Y because Z"; "Claude missed this bug, I caught it in review"). Honest‑but‑careful framing of failures as learning moments — diplomatic register appropriate for a graded report; avoids sanitized successes‑only tone.
- **Paper has 6–8 main body figures + 10–12 appendix** (D‑11). Main body carries the narrative; appendix is for reproducibility‑minded readers. Forces editorial discipline without losing data. Ended at ~10 main + 10 appendix, slightly above the 8 target — acceptable given the dedicated ablations section.
- **Demo backup is single full‑run screen recording** (D‑16). One end‑to‑end recording. If the live demo fails, cut to the recording — audience gets the same content. Simple, low‑effort, literal match to the "screen‑recording backup" requirement.
- **Pre‑flight figure existence check** before `make paper` (B‑2 fix). `results/**` is gitignored; on a fresh checkout the figures don't exist. The pre‑flight loop enumerates ~20 expected figure paths, fails fast with a regeneration command if any are missing. Catches a class of cryptic latexmk errors that would otherwise non‑deterministically appear in CI or post‑`make clean` states.

**What surprised us:** The plan‑checker found 2 blockers + 5 warnings on the first revision pass — including catching the Makefile `.PHONY` race between Plans 01 and 02 (same wave, both editing the same line). The fix landed cleanly: refactor Plan 01 to own the `.PHONY` ownership entirely, leaving Plan 02 to append only the `demo:` target body. Wave 1 parallelism preserved with zero overlapping byte ranges.

Verifier verdict: **PASS** — 4/4 success criteria, 3/3 requirements, 19/19 locked decisions honored, 0 unresolved refs.

---

## Project Arc — What This Looked Like End‑to‑End

| Date | Phase | Plans | Net Output |
|------|-------|-------|------------|
| 2026‑04‑16 | Pre‑milestone planning | — | PROJECT.md, ROADMAP.md, REQUIREMENTS.md, research stack |
| 2026‑04‑18 | 1 — Refactors + CL pilot | 6 | `hash_util.h`, refactored `replay_zipf`, throughput column, results subdirs, CourtListener token + 200‑request pilot |
| 2026‑04‑19 | 2 — W‑TinyLFU core | 6 | `count_min_sketch.h`, `wtinylfu.h`, `test_wtinylfu.cpp`, validation sweep + `check_wtlfu_acceptance.py` |
| 2026‑04‑19 | 3 — Court collection + sweep | 3 | `collect_court_trace.py` (609 lines), `traces/court_trace.csv` (20K rows, 9‑hour collection), 6‑policy sweep on Court |
| 2026‑04‑20 | 4 — SHARDS rigor + ablations | 5 | 1M trace generator, 4‑rate SHARDS, `doorkeeper.h`, 3 ablation studies × 2 workloads |
| 2026‑04‑21 | 5 — Cross‑workload analysis | 6 | `--seed` flag, `run_multiseed_sweep.py`, `compare_workloads.py` (Welch's t‑test), 4 cross‑workload figures, characterization + winner tables |
| 2026‑04‑22 | 6 — Writeup + demo | 7 | 20pp DOC‑02 PDF, 3.5K‑word DOC‑03, `demo.sh` (4s wall‑clock), 3 rehearsals + 4.2 MB screen recording |

**Six phases. 33 plans. Five and a half days from refactor‑kickoff to verified deliverables. ~108 locked decisions across all phases (see `DECISIONS-MATRIX.md`).**

**Three things that mattered most:**
1. **The pilot phase.** Spending 5 minutes on a 200‑request CourtListener pilot before committing to a 9‑hour production collection saved a workday's worth of risk.
2. **Caffeine pre‑work before W‑TinyLFU implementation.** Pulling Caffeine v3.1.8 source and locking 6 deviation rules *before* writing C++ prevented an entire category of "we matched the paper but not the production reference" bugs.
3. **The mechanism deep‑dive.** What started as "explain why one algorithm wins" in midpoint feedback became the paper's centerpiece — and the ablations empirically validated the mechanism story instead of just asserting it.

**One thing that surprised us most:** the SIEVE‑wins‑on‑Congress finding from the regime analysis. It contradicted the Phase 2 narrative and forced a deeper look at the workload shape — which produced the SIEVE‑as‑admission‑filter‑in‑disguise insight that the paper centers on.

**One thing we'd do differently:** budget more headroom on long collection runs. The CourtListener collection took ~9 hours instead of the planned ~6.1 because per‑request network RTT (~0.07s) compounded on top of pacing. A 30% headroom rule would have set expectations correctly.

---

*Generated 2026‑04‑26 from `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, six per‑phase `CONTEXT.md` files, `PROCESS.md`, and the 33 plan SUMMARY.md files.*
