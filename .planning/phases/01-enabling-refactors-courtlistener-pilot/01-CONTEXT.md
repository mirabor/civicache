# Phase 1: Enabling Refactors & CourtListener Pilot — Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 unblocks every downstream phase. Scope is:

1. **Hash extraction** — Pull FNV-1a from `src/shards.cpp` into `include/hash_util.h` so SHARDS and W-TinyLFU can share one deterministic hash implementation
2. **replay_zipf refactor** — Split into `prepare_objects()` + `generate_replay_trace()` so the alpha sweep doesn't regenerate the full object list 7× per run
3. **Throughput measurement** — Add `accesses_per_sec` column to simulation output CSVs
4. **Results directory reorganization** — Migrate existing Congress results into per-workload subdirs (`results/congress/`, and create empty `results/{court,shards_large,compare}/`)
5. **CourtListener access setup** — Register account, obtain API token, configure env var
6. **CourtListener pilot run** — 200-request sanity check across `/dockets/`, `/opinions/`, `/clusters/`, `/courts/` with ≥70% success gate

What's explicitly NOT in this phase: CourtListener production collection (Phase 3), W-TinyLFU implementation (Phase 2), Doorkeeper (Phase 4), any analysis or writeup.
</domain>

<decisions>
## Implementation Decisions

### Throughput measurement
- **D-01:** Granularity = one value per (policy, cache-size) cell, stored as a new `accesses_per_sec` column in `results/*/mrc.csv`. Matches existing sweep output structure, gives cache-size-level signal for Pareto plots downstream.
- **D-02:** Measurement method = `std::chrono::steady_clock` wall-clock around the `run_simulation()` call (not CPU time, not time-series). Rationale: simpler, portable, and signal is strong at 500K-request scale.
- **D-03:** Alpha sweep and SHARDS runs should also produce throughput values so downstream phases can plot miss-ratio vs throughput Pareto curves.

### Results directory migration
- **D-04:** Preserve existing Congress results — `git mv results/*.csv results/congress/` (and matching logic in plotting scripts). Empty stub dirs for `results/{court,shards_large,compare}/` should exist so future phases just write into them.
- **D-05:** Update `scripts/plot_results.py` to read from `results/{workload}/` subdirs. Add a `--workload` flag (defaulting to `congress` for backward compat of existing invocations).
- **D-06:** Main.cpp `--output-dir` flag keeps its current semantics — callers now pass `results/congress/` or `results/court/` explicitly. The simulator itself doesn't need to know about workload identity.

### CourtListener pilot failure policy
- **D-07:** If an endpoint's pilot success rate is <70%, narrow its ID-range heuristic and rerun until ≥70%. Phase 1 does not complete until all 4 planned endpoints pass the gate. Rationale: better to catch ID-range issues now than in the middle of a multi-hour production collection.
- **D-08:** Pilot script should emit a per-endpoint success tally (count of 200s / 404s / 403s / 429s / other). Success = HTTP 200 with size > 0.
- **D-09:** If an endpoint is fundamentally gated (403 pattern across random IDs), drop it from the endpoint mix and document in the pilot report — don't keep retrying.

### replay_zipf API shape
- **D-10:** Split into two functions in `trace_gen.cpp`:
  - `prepare_objects(const std::vector<TraceEntry>& raw_trace, uint64_t seed)` — dedupe, shuffle, return `std::vector<std::pair<std::string, uint64_t>>` (key, size)
  - `generate_replay_trace(const std::vector<std::pair<std::string, uint64_t>>& objects, uint64_t num_requests, double alpha, uint64_t seed)` — sample by Zipf(alpha) over the shuffled list
- **D-11:** Existing `replay_zipf()` stays as a thin wrapper calling both functions (backwards compat with current `main.cpp` usage). The alpha sweep path calls `prepare_objects` ONCE and `generate_replay_trace` 7× with different alpha values.

### FNV-1a hash and seeds
- **D-12:** `include/hash_util.h` contains:
  - `inline uint64_t fnv1a_64(const std::string& s, uint64_t seed = FNV_BASIS)` — the existing FNV-1a, parameterized on basis offset
  - Four named constants: `FNV_SEED_A`, `FNV_SEED_B`, `FNV_SEED_C`, `FNV_SEED_D` — hardcoded 64-bit primes derived from the golden ratio (e.g., `0x9e3779b97f4a7c15` family)
- **D-13:** `src/shards.cpp` replaces its local FNV-1a with the shared one; no behavioral change expected (`SHARDS_SEED = FNV_BASIS`).
- **D-14:** `std::hash<std::string>` is banned project-wide for anything that needs determinism across runs — violates reproducibility because libstdc++'s implementation is version-dependent.

### Claude's Discretion
- Specific FNV basis/prime constants (just use the standard FNV-1a constants; any golden-ratio-derived seeds work for the 4 CMS rows as long as they differ)
- File naming for the new header — `hash_util.h` is fine
- Whether to add a unit test for the extracted FNV-1a before trusting it (yes, add a trivial round-trip self-test; caller can ignore)
- Exact endpoint ID-range heuristics for the CourtListener pilot (start from the research SUMMARY.md suggestions; tune empirically during the pilot)
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-specific research
- `.planning/research/STACK.md` — CourtListener v4 API spec, rate limits, endpoint taxonomy, W-TinyLFU parameter defaults (Caffeine wiki)
- `.planning/research/ARCHITECTURE.md` — hash_util.h extraction rationale, replay_zipf refactor plan, results layout
- `.planning/research/PITFALLS.md` — C1/C2/C3/C4 (PACER vs CL, 5k/hr throttle, gated endpoints, 10-min query cache) + m3 (court ID mapping)
- `.planning/research/SUMMARY.md` — locked decisions table, suggested build order

### Project-level refs
- `.planning/PROJECT.md` — Core value, validated capabilities from Milestone 1, risks
- `.planning/REQUIREMENTS.md` — Full REQ-ID list, phase traceability
- `.planning/codebase/ARCHITECTURE.md` — Existing system structure (CachePolicy hierarchy, data flow, CSV schemas)
- `.planning/codebase/STRUCTURE.md` — Directory layout + naming conventions
- `.planning/codebase/CONVENTIONS.md` — C++ style (trailing-underscore members, header-only policies), Python style

### Code to read before modifying
- `src/shards.cpp:85-98` — current FNV-1a implementation to be extracted
- `src/trace_gen.cpp` (full) — current `replay_zipf` to be split
- `src/main.cpp` — orchestration of sweeps, alpha sweep loop that benefits from refactor
- `scripts/collect_trace.py` — Congress collector pattern to mirror for CourtListener pilot
- `scripts/plot_results.py` — existing plotting needs to find data in new subdir layout

### External API
- https://www.courtlistener.com/help/api/rest/v4/ — CourtListener REST v4 docs (Context7: `/websites/courtlistener_help_api_rest`)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **FNV-1a in `src/shards.cpp:85-98`** — working implementation, just needs to be lifted into a header. Zero behavioral change after extraction.
- **`collect_trace.py` Congress collector** — exact template for the CourtListener pilot: rate-limiting loop with exponential backoff, jitter, CSV output. Copy-modify pattern, don't generalize.
- **`replay_zipf` in `src/trace_gen.cpp`** — existing logic is correct, just needs to be split so the shuffle+dedupe step is extracted.
- **`main.cpp` alpha-sweep loop** — already calls `replay_zipf` 7 times per run; after the refactor, it should call `prepare_objects` once and loop over `generate_replay_trace`.

### Established Patterns
- **Trailing-underscore convention** for C++ member variables — `hand_`, `buffer_`, `map_` (see `cache.h`)
- **Header-only policies** — no `.cpp` file for cache policies. `hash_util.h` should follow the same "inline utility in header" pattern.
- **CSV-as-contract** — all simulator/script interchange is CSV. Any schema change (adding `accesses_per_sec`) must update both the C++ writer and the Python reader.
- **`std::chrono::steady_clock`** is already used in `main.cpp` for the SHARDS timing — reuse the same pattern for throughput.
- **`.env` for secrets** — `CONGRESS_API_KEY` already committed to the pattern; `COURTLISTENER_API_KEY` goes in the same file.

### Integration Points
- `hash_util.h` → included by `src/shards.cpp` (now), `include/count_min_sketch.h` (Phase 2), `include/wtinylfu.h` (Phase 2)
- New `prepare_objects` / `generate_replay_trace` → called by `main.cpp` alpha-sweep loop and, in Phase 5, by the multi-seed sweep driver
- `accesses_per_sec` column → read by `scripts/plot_results.py` and (Phase 5) `scripts/compare_workloads.py`
- `results/{workload}/` layout → read by all plotting scripts; `scripts/compare_workloads.py` (Phase 5) will join across subdirs
</code_context>

<specifics>
## Specific Ideas

- Reuse the existing `.env` + `DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib` activation pattern — don't try to fix the Homebrew Python libexpat issue in this phase
- The pilot script should live at `scripts/pilot_court_trace.py` (separate from the production `scripts/collect_court_trace.py` that Phase 3 will create) so it's clear the pilot is throwaway verification code
- Emit a summary line at the end of the pilot: `200s / 404s / 403s / 429s / total` per endpoint so the ≥70% gate is trivially checkable
- FNV-1a self-test: call `fnv1a_64("hello")` and assert it equals the known FNV-1a 64-bit result (from Wikipedia) at startup — catches bit-width mistakes early
</specifics>

<deferred>
## Deferred Ideas

- **Doorkeeper implementation** — Phase 4 (optional ablation, not core W-TinyLFU)
- **CourtListener production collection** (≥20K requests) — Phase 3
- **`scripts/compare_workloads.py`** — Phase 5
- **Multi-seed confidence intervals** — Phase 5
- **Fixing the macOS Homebrew libexpat linkage properly** — not in scope; env-var workaround is fine for course project

None of these belong in Phase 1. Do not absorb.
</deferred>

---

*Phase: 01-enabling-refactors-courtlistener-pilot*
*Context gathered: 2026-04-16*
