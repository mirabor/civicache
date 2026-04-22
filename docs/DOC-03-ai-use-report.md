---
phase: 06-writeup-demo
produced: 2026-04-21
role: ai-use-report
requirement: DOC-03
---

# AI-Use Report — Caching Policy Simulator

*CS 2640, Spring 2026 — Final Submission*

## Opening: A Concrete Decision Moment

Early in Phase 4 of this project, Claude shipped a production implementation of S3-FIFO's ghost queue that evicted elements using `unordered_set::begin()`. The line read naturally — `ghost_.erase(ghost_.begin())` — it compiled, it passed the existing tests, and the policy's overall miss ratio landed in the range you would expect from a paper that cites Yang et al. (SOSP '23). But `begin()` on `std::unordered_set` returns an arbitrary element, not the oldest one. The ghost queue is supposed to be FIFO. What we had was a random-eviction ghost filter that happened to work because the bucket hashing produced reasonable-looking outputs on our workload.

Round 1 of code review caught it. I replaced the `unordered_set` with a `deque<string>` + `unordered_set<string>` pair for FIFO-ordered eviction. After the fix, S3-FIFO consistently ranked between SIEVE and CLOCK on our workload — matching the published results from the paper. Before the fix, it sometimes performed worse than CLOCK at small cache sizes, which contradicts the paper's finding. The implementation was confidently wrong in a way I almost did not verify.

This bug is the whole AI-collaboration story in miniature: fluent, plausible, structurally wrong. The rest of this report is about learning which instincts to develop.

## How This Project Was Built

The conventional frame for "I used Claude Code" is that a human wrote a spec and an AI wrote the code. That frame describes maybe a third of what actually happened on this project. Over six phases and roughly twenty-six executed plans, AI collaboration touched three distinct layers:

1. **Research-phase decisions.** Before any code got written for a given phase, there was a debate about *what* should get built. Whether to use PACER or CourtListener for the second trace source. Whether W-TinyLFU was the right sixth policy to add or whether LHD or AdaptSize would be better systems-course material. Whether the raw Congress trace's near-zero temporal locality disqualified it for policy comparison, and what to do about that if so. These decisions shaped the entire project and Claude was a full participant in them — often the one proposing options with honest tradeoff tables.

2. **GSD planning and orchestration.** The middle layer — how the multi-phase planning, subagent delegation, and parallel worktree execution structured the project — is where a surprising amount of value came from. Phase 4 ran four ablation axes in parallel worktrees; the reviewer subagent in Phase 5 caught a latent coupling that both the planner and the executor missed. This is not a single LLM call. It is a structured pattern of AI use that happens to be load-bearing for a project of this complexity under a deadline.

3. **Claude Code implementation partnership.** The actual code-writing. Phases 1-5 produced roughly 8,000 lines of C++ and Python across `src/`, `include/`, `scripts/`, and `tests/`. All of it was Claude drafts modified by review.

This report covers all three layers. The research-phase discussion gets equal depth with implementation because the project is not just the code — it is also the choices about what not to build.

## Research-Phase Decisions

Four pre-code decisions shaped the project more than any single implementation choice.

**CourtListener over PACER.** The original midpoint proposal named PACER as the second trace source. Claude researched PACER during Phase 1 and surfaced that PACER charges $0.10 per page with no free tier for academic research — roughly $500-$2,000 for the 20K-request trace this project needed. CourtListener, a sibling project at the Free Law Project, exposes the same case metadata through a REST v4 API with a free 5,000-requests-per-hour tier on an authenticated token. Claude proposed CourtListener; I verified the token access with a live 200-request pilot before committing. Retrospective: this was the right choice. The 20K Court trace landed in ~8 hours of wall-clock (four endpoint families, rate-limited with exponential backoff), and the paywall alternative would have ended the project.

**W-TinyLFU as the sixth policy.** The initial candidates for a sixth policy were LHD, AdaptSize, and W-TinyLFU. Claude's honest tradeoff: LHD is the most novel but has no public reference implementation (high risk); AdaptSize is more conservative but size-aware eviction is a different story than frequency admission; W-TinyLFU has a well-tested reference in Caffeine v3.1.8 and a strong academic paper (Einziger-Friedman 2017). I chose W-TinyLFU. Retrospective: this was the right call for correctness, but the Caffeine reference turned out to be an important input — not just for the code, but for knowing which six deviations from Caffeine were deliberate (CONSERVATIVE update, byte-bounded regions, empty-probation short-circuit, strict `>` admit, stats single-source invariant, dropped unused ctor members). The reference implementation did more than provide code; it defined the locus of debate.

**Replay-Zipf as the primary analysis approach.** The raw Congress.gov trace had Zipf alpha = 0.23 (nearly uniform) and a 98.9% one-hit-wonder ratio. This is because the collector generates random endpoint keys — there is no temporal locality in client-generated trace. All five policies produced ~98-99% miss ratio on the raw trace, which makes policy comparison meaningless. Claude proposed replay-Zipf mode — preserve the real (key, size) pairs from the collected trace, then overlay a controlled Zipf popularity distribution. This was a more invasive change than I initially expected (it touches trace_gen, the alpha sweep, and the validation tests), but without it there is no paper. Retrospective: the professor flagged client-generated traces as a compromise in the midpoint feedback. Replay-Zipf is the mitigation.

**SHARDS 1M validation via self-convergence.** Phase 4 validated SHARDS at the 1M-request scale. The Waldspurger paper reports 0.001 MAE at 1% sampling, but on 1M accesses there is no feasible "exact" baseline — computing exact stack distances is O(n × |unique_keys|), and at a million-plus accesses this is untenable even overnight. Claude proposed a self-convergence approach: treat the 10% sampling rate as the reference, measure MAE against it for 0.01%, 0.1%, and 1%, and use a 50K-sample oracle-regime cross-check where the exact algorithm does fit. This was a methodological concession but an honest one — the paper reports results from a context (SSD trace workloads, different skew) that our synthetic Zipf(α=0.8, 100K objects) does not match. Our 0.0378 MAE at 1% passed the loose sanity gate; claiming the paper's 0.001 at our workload would have been unsupported.

## GSD Planning and Orchestration

The "GSD" (Get Shit Done) framework structured this project as a sequence of phases, each with a research-phase, a discuss-checkpoint, a planning-phase, and an execute-phase. This is more overhead than single-shot AI use, and the overhead paid for itself repeatedly.

**Subagent delegation and the reviewer finding.** The Phase 5 planner designed the cross-workload analysis infrastructure. The Phase 5 executor implemented it. Both missed a latent coupling in `plot_winner_per_regime_bar`: the figure code does not filter to `BASE_POLICIES` while the table code does, so the figure and the table would silently diverge if the multi-seed sweep is ever extended to include ablation variants. The Phase 5 **reviewer subagent** — a separate Claude invocation with the explicit job of adversarial code review — caught this as WR-01 in `05-REVIEW.md`. This is a concrete example of the pattern working: three AI calls in series on the same code, with the third role being specifically skeptical of the first two.

**Parallel worktree execution.** Phase 4 decomposed into five plans across four ablation axes (SHARDS large-scale, Doorkeeper standalone, S3-FIFO ratio, SIEVE visited-bit). The orchestrator dispatched four of these plans to parallel git worktrees. Elapsed wall-clock was roughly 20 minutes for what would have been 60+ minutes of serial execution — and more importantly, each worktree operated in isolation so cross-plan file conflicts were impossible by construction. The GSD framework's plan-level `files_modified` declaration made this scheduling automatic.

**CONTEXT.md decision locking.** Each phase has a `CONTEXT.md` file with decisions keyed by ID (D-01, D-02, etc.) that get propagated into `PLAN.md`, then `SUMMARY.md`, then `STATE.md`. This is how "Claude suggested X, I chose Y because Z" stays traceable months later. Every SUMMARY.md in `.planning/phases/*/` cross-references the D-IDs that governed its implementation.

What did not work: early phases under-specified their task acceptance criteria, so Phase 2's "implement W-TinyLFU" plan landed with scope creep. Phase 5 added `check_anal_acceptance.py` and `check_wtlfu_acceptance.py` as pattern-enforced gates — grep-countable invariants plus runtime assertion scripts — after that pain point became obvious.

## Implementation Partnership

The `progress.tex` midpoint report described my role as the project design and Claude's role as writing code from those specifications. That is still the most accurate one-sentence framing of the collaboration. What Phase 4-5 added was specific examples of the partnership going both ways.

**Claude deviating ABOVE the plan.** Phase 4 Plan 04-01 (SHARDS 1M validation) had a plan action line that asserted "0.0001 × 50000 = 5 < 200 so it gets dropped" — implying only the 0.0001 sampling rate would be excluded by the 200-sample floor in the 50K oracle regime. But 0.001 × 50000 = 50, also below 200. Claude's implementation applied the guard uniformly (both 0.0001 and 0.001 get dropped), which is correct per the D-01 decision, even though the plan narrative only anticipated one rate getting excluded. The `04-01-SUMMARY.md` documents this as a Rule 1 deviation ("plan arithmetic was wrong; implementation was right"). This is the pattern where the plan is a specification of intent, and the implementation should match intent not literal text.

**Doorkeeper paper-faithful integration.** Plan 04-05 required Doorkeeper × W-TinyLFU integration with a pre-CMS filter matching Einziger-Friedman §4.3 exactly (filter before CMS increment, not after). Claude's initial read of the plan text was ambiguous on ordering; I re-checked the paper and locked D-05 as "paper-faithful pre-CMS filter" before Plan 04-05 started. The execution landed clean. The point is that the AI did not know the paper was pre-CMS versus post-CMS — the implementation would have matched whichever way the spec was written — and this is precisely the kind of detail where human oversight of the source material matters.

**Welch's t-test checkpoint.** Plan 05-04 introduced statistical significance testing for the cross-workload comparison. Claude proposed `scipy.stats.ttest_ind(equal_var=False)` (Welch's) over the student-t alternative; the one-sided versus two-sided decision was escalated to a checkpoint. I chose two-sided (we are interested in both "W-TinyLFU beats LRU" and "W-TinyLFU regresses vs LRU"). Retrospective: this was the right scope for the cross-workload story. The one-sided variant lives separately in `check_wtlfu_acceptance.py` where we specifically need a regression-guard direction for WTLFU-05.

## Bugs Found and Fixed — Audited Count

As of 2026-04-21, the bug count across `PROCESS.md` body is **9** — matching the original midpoint quotation of "9-bug list" because the re-audit confirmed the original count rather than revising it. The breakdown, re-counted at write time directly from the `PROCESS.md` tables rather than from memory:

### Round 1 (code review, PROCESS.md:148-152)

| Bug | Severity | Description | Fix |
|-----|----------|-------------|-----|
| MRC units | Critical | Stack distances (object count) compared against cache sizes (bytes) | Pass `ws.unique_objects` instead of `total_bytes / 10` |
| Per-access random sizes | Critical | `generate_zipf_trace` drew a new random size on every access, not per object | Pre-generate one size per object in a vector |
| 404s in trace | Warning | Non-200 responses logged as real cache objects | Filter `resp.status_code != 200` |
| Makefile deps | Warning | Header changes didn't trigger rebuild | Added `-MMD -MP` and `-include $(OBJECTS:.o=.d)` |

### Round 2 (code review, PROCESS.md:158-162)

| Bug | Severity | Description | Fix |
|-----|----------|-------------|-----|
| S3-FIFO: no freq tracking in small | Critical | Hits in small queue didn't increment frequency. Eviction from small checked ghost instead of freq. Misses always went to small, ignoring ghost. | Added `freq` field to `SmallEntry`; eviction promotes on `freq > 0`; ghost hits on miss go directly to main. |
| S3-FIFO: random ghost eviction | Critical | Ghost was `unordered_set`; `begin()` evicts an arbitrary element, not the oldest (the opening-hook bug) | Replaced with `deque<string>` + `unordered_set<string>` for FIFO-ordered eviction |
| ZipfGenerator OOB | Critical | `lower_bound` returns `end()` when `r > cdf_.back()` (FP accumulation). Used as array index. | Clamp: `if (it == cdf_.end()) return cdf_.size() - 1` |
| Size not updated on hit | Critical | LRU, FIFO, CLOCK, S3-FIFO, SIEVE didn't update stored size when re-accessed with a different size; `current_size_` would drift. | Update stored size and adjust `current_size_` in the hit path of all five policies |

### SHARDS denominator bug (PROCESS.md:164-165)

The `build_mrc` function computed `estimated_total = total_sampled_ / rate_` and divided hit counts by that. But the histogram stores raw sampled counts, not scaled counts. Dividing sampled hits by `total_sampled / rate` effectively multiplied the miss ratio by `(1 - hit_fraction * rate)` instead of `(1 - hit_fraction)`. This produced MAE of 0.63-0.70 against exact MRCs. Fixed by using `total_sampled_` directly as the denominator.

**PROCESS.md body total: 9 bugs.** (4 Round 1 + 4 Round 2 + 1 SHARDS denominator.)

### Post-PROCESS.md: Phase 5 code review (05-REVIEW.md)

`PROCESS.md` was last updated at the end of Phase 3. Phases 4-5 produced additional findings that the reviewer subagent caught in `05-REVIEW.md`: **2 warnings plus 10 info items, total 12 issues**.

- **2 warnings:**
  - **WR-01** — `plot_winner_per_regime_bar::winner_on` does not filter to `BASE_POLICIES` while `compare_workloads.py::_winner_in_group` does. Latent coupling: figure and table would silently diverge if ablation variants are ever added to the multi-seed sweep.
  - **WR-02** — Regime dispatch at `plot_results.py:819-849` is an `if/elif` chain with no `else` branch. Silent NameError trap or stale-value propagation if a fifth regime is added without a matching branch.
- **10 info items:** encoding-unspecified `open()` calls (Windows-unsafe for the `α` glyph); `.values` vs `.to_numpy()` on Series; four inconsistent float-comparison idioms across modules; `--seeds` CLI accepting silent duplicates; the `pipe_count < 40` schema-fragile SC-3 heuristic; `significant=True` semantics for LRU reference rows counter-intuitive; file-restore-on-fail risk in `test_red_path_missing_regime_md`; data-dependent test assertion in `test_wtlfu_significant_high_alpha_congress`; `round(2)` coercion assuming 1-decimal alpha grid; scratch-dir leak on partial `run_multiseed_sweep.py` runs.

Neither warning currently produces wrong results — both are *latent* couplings that would manifest if future work extends the multi-seed sweep to include ablation variants (WR-01) or adds a regime beyond the current four (WR-02). Both are documented in `05-REVIEW.md` and deferred to v2 per `PROJECT.md` V2-06 framing.

**Total audited count across all sources: 9 (PROCESS.md body) + 12 (Phase 5 review) = 21 issues.** (Per D-07 — the final number is determined by the audit at write-time, not pinned to "9" from the midpoint framing. The midpoint "9" was correct for PROCESS.md body; the 12 additional items are post-Phase-3 findings PROCESS.md does not yet cover.)

In addition, Phase 4 plan summaries record a small number of minor plan-vs-implementation deviations — Plan 04-01 Rule 1 arithmetic correction, Plan 04-01 Rule 3 grep-visibility cosmetic, Plan 04-05 Rule 3 comment-self-match cosmetic — but these are *plan-narrative corrections caught during execution*, not latent correctness bugs in shipped code. The Rule 1 in Plan 04-01 is the interesting case: the plan text was slightly wrong about arithmetic; the implementation matched the D-01 decision intent and correctly dropped both 0.0001 and 0.001 in the 50K oracle regime. We count these separately from the audit total because they represent the plan→code boundary, not the code→review boundary.

## What Did Not Work — Learning Moments

Five named patterns where AI collaboration needed correction. Framing these as learning moments rather than as AI failures — the point is what instinct to develop, not what to blame.

**1. Over-trusting confident-sounding wrong answers.** The S3-FIFO ghost eviction bug (opening hook) is the canonical example. Claude wrote `ghost_.erase(ghost_.begin())` and it looked correct at first review. The deeper instance: Phase 4 Plan 04-05's initial paper-reading loop. Claude's first-pass summary of Einziger-Friedman §4.3 was ambiguous on whether the Doorkeeper is pre-CMS or post-CMS in the admission pipeline. When the ambiguity showed up in the plan action text, I had to re-read the paper myself to lock D-05. **Lesson: when the AI confidently summarizes a paper, verify by reading the paper — especially on subtle details like evaluation order.**

**2. Bugs Claude shipped that review caught.** Beyond the S3-FIFO bug: the SHARDS denominator (PROCESS.md:164-165), the ZipfGenerator OOB (Round 2), size-not-updated-on-hit across all five policies (Round 2). Phase 5's WR-01 coupling also falls here — the Phase 5 planner missed it, the Phase 5 executor missed it, the reviewer subagent caught it. **Lesson: plan multiple review passes on critical sections. Different prompt framings catch different errors. One "write the code" call + one "find issues" call is more reliable than a single longer session.**

**3. The planner-misread-source pattern.** Phase 5 Plan 05-02 (workload_stats.json regeneration): the planner read "0.797 MLE-recovers-from-synthetic-alpha=0.8" as "raw Congress alpha = 0.797" — a regression-test value misread as a data claim about the trace. The executor caught it at write-time, confirmed empirically that raw Congress α_mle is 0.231 (near-uniform), and patched via a SUMMARY.md deviation note with a clear explanation. No code change was needed; the rendering code was correct. **Lesson: chained LLM calls can compound misreadings when one call's output becomes another's input. Acceptance tests that check for empirical values as opposed to hoped-for values catch this.**

**4. Environment issues not visible to the AI.** The macOS `libexpat` symbol mismatch (Python 3.14's pyexpat requiring a newer `_XML_SetAllocTrackerActivationThreshold` symbol than `/usr/lib/libexpat.1.dylib` ships) required manual `DYLD_LIBRARY_PATH` intervention. Claude cannot test this — the build fails without the env var, and Claude has no access to the target machine. I debugged this for ~45 minutes before the Phase 1 Makefile workaround (`DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib`) landed at commit 2dc8466. The `demo.sh` explicitly sources this per D-17 so it does not recur at demo time. **Lesson: environment issues belong to the human in the loop; an AI that works on generic "Linux/macOS" assumptions will drop context-specific breakage on the floor.**

**5. Plan specificity pays.** The earliest plans said things like "implement SHARDS" in one sentence. Phase 1-2 bug-per-plan was noticeably higher than Phase 4-5. Later plans acquired byte-level behavioral criteria (`rate * trace.size() >= 200` in Plan 04-01 verbatim), grep-countable invariants (`record\(\s*(true|false)` = 4 in `wtinylfu.h` for L-12 stats-single-source), and runtime acceptance scripts (`check_anal_acceptance.py`). The per-plan bug count dropped visibly. **Lesson: the GSD framework's `read_first` mandate plus `acceptance_criteria` grep set plus runtime assertion gate is not overhead — it is the signal-to-noise filter. Without it, the AI ships code that passes plausibility review but not structural review.**

## What Worked — Concrete Wins

Three named patterns where AI collaboration produced clear value.

**1. Scaffolding velocity.** Phase 1's refactor work — `hash_util.h` extraction, `replay_zipf` split, `accesses_per_sec` column addition, `results/` directory reorganization — was roughly four plans at an average of ~8 minutes each for a total of ~45 minutes wall-clock. Manual refactors of this scope (moving functions across files, updating all call sites, adding dependency tracking to the Makefile, regenerating results) would be a half-day's work at minimum. The AI does not read the whole codebase each time — but with specific `files_modified` declarations and `read_first` requirements, it reads the right ~200 lines and ships the right ~40-line patch.

**2. Parallel ablation execution.** Phase 4 ran four ablation axes in parallel worktrees (SHARDS 1M validation, Doorkeeper standalone, S3-FIFO ratio, SIEVE visited-bit). Per-plan wall-clock was 6-13 minutes; the elapsed time for the whole phase was ~20 minutes. The measured metrics in `STATE.md`'s Performance Metrics table show Plan 04-01 at 6m25s, 04-02 at ~6m, 04-04 at ~5m39s, 04-05 at ~13m — and yet the phase finished faster than any single serial run because they ran concurrently. This is not a single-LLM-call pattern. It is multi-agent orchestration, and it produced a 3× wall-clock speedup for a phase with four independent axes.

**3. Decision traceability.** Every `SUMMARY.md` in `.planning/phases/*/` cross-references the decision IDs from its matching `CONTEXT.md`. Future-me reading the code can answer "why is Welch's t-test two-sided and not one-sided?" by grepping `D-` in the Plan 05-04 SUMMARY. "Why does W-TinyLFU use CONSERVATIVE update and not Caffeine's STANDARD update?" → grep D-05 or CAFFEINE-NOTES §6 row 2. This is a collaboration discipline the GSD framework enforces, and it is the reason this AI-use report can be written at all — without the D-ID trail the retrospective would be guesswork.

## Closing

The whole-project view, not just the code-collaboration view: this is less "Claude wrote the code" and more "the project is a three-way conversation between product intent (my design choices, guided by the research-phase decisions), structural discipline (GSD orchestration, subagent review, discuss-checkpoint locking), and implementation effort (Claude Code actually typing the bytes)." The failures were mostly at the interfaces between layers — the planner misreading source for the executor, the paper-summary step leaving ambiguity for the spec, the environment assumptions hitting an actual laptop. The wins were mostly from layer separation — parallel worktrees because plans declared file ownership, the reviewer subagent because the role was distinct from the writer, the cross-workload Welch's-t backing because the acceptance script ran AFTER the implementer claimed done.

For a roughly six-week course project, this produced a defensibly-rigorous simulator (six policies, replay-Zipf mode, SHARDS-validated MRC curves, `check_wtlfu_acceptance.py` regression gate), a 20K-request real Court workload (CourtListener REST v4, rate-limited, SSRF-guarded), a 5-seed Welch's-t-backed cross-workload comparison (`compare_workloads.py`, aggregated CSVs, `winner_per_regime.md`), plus an honest bug log that now audits to 21 issues across PROCESS.md body and Phase 5 review. Significantly more than I could have built alone in the same time — and more importantly, more rigorously than I would have built it alone, because the framework forced acceptance criteria and review passes I would not have imposed on myself.
