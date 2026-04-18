# civicache — CS 2640 Final Project

## What This Is

A C++17 cache eviction policy simulator that compares five policies (LRU, FIFO, CLOCK, S3-FIFO, SIEVE) on legislative API workloads. The base simulator is already complete: all five policies are implemented, validated against each other, and exercised on a 20K-request Congress.gov trace with replay-Zipf popularity overlay. SHARDS miss-ratio-curve construction is implemented and validated against exact stack distances (2% MAE at 10% sampling).

This PROJECT.md covers the **remaining work**: extending the evaluation to a second domain (PACER court records), adding a sixth policy (W-TinyLFU), validating SHARDS at larger scales, and producing the final deliverables (paper, code, AI-use report, live demo).

## Core Value

The ONE thing that must work: a defensible, well-analyzed comparison of cache eviction policies on **real legislative/judicial API workloads** that produces a clear finding (which policies work, which don't, and why), packaged as a submission-ready report with reproducible code.

Everything else — second trace, W-TinyLFU, SHARDS rigor — strengthens this core story but isn't the story itself.

## Context

- **Course:** CS 2640 (Modern Storage Systems), Spring 2026
- **Deadline:** End of semester (4+ weeks runway)
- **Existing artifacts:** Full simulator, 20K Congress.gov trace, replay-Zipf results, progress report, PROCESS.md, codebase map
- **Professor feedback on midpoint:** Positive on design; flagged that client-generated traces are a compromise (already mitigated by replay-Zipf); explicitly asked for an AI-use report
- **Built so far with:** Claude Code as an implementation collaborator; three rounds of code review caught 9 bugs

## Requirements

### Validated (existing capabilities)

- ✓ **SIM-01**: C++17 simulator compiles clean with Makefile — existing
- ✓ **SIM-02**: LRU, FIFO, CLOCK, S3-FIFO, SIEVE implementations correct and benchmarked — existing
- ✓ **SIM-03**: Zipf trace generation with per-object sizes — existing
- ✓ **SIM-04**: MLE Zipf alpha estimator (Clauset et al.) — existing
- ✓ **SIM-05**: One-hit-wonder ratio analysis — existing
- ✓ **SIM-06**: SHARDS MRC at 0.1%/1%/10% sampling — existing
- ✓ **SIM-07**: Exact stack distance validation against SHARDS — existing
- ✓ **SIM-08**: Alpha sensitivity sweep — existing
- ✓ **TRACE-01**: Congress.gov trace collector with rate-limiting + backoff — existing
- ✓ **TRACE-02**: Replay-Zipf mode overlays Zipf popularity on real keys/sizes — existing
- ✓ **PLOT-01**: matplotlib pipeline produces 6 figures (MRC, byte MRC, alpha, OHW, SHARDS MRC, workload) — existing
- ✓ **DOC-01**: Progress report, PROCESS.md, README, codebase map — existing

### Active (new work for submission)

**Second trace source (PACER/CourtListener):**

- [ ] **TRACE-03**: Research PACER vs CourtListener/RECAP access — pick viable source
- [ ] **TRACE-04**: Implement court-records trace collector with rate-limiting
- [ ] **TRACE-05**: Collect a ≥20K-request court records trace
- [ ] **TRACE-06**: Run all policies on court records via replay-Zipf; compare to Congress

**W-TinyLFU policy:**

- [ ] **SIM-09**: Implement Count-Min Sketch frequency counter (frequency sketch)
- [ ] **SIM-10**: Implement W-TinyLFU policy (1% window LRU + 99% main with TinyLFU admission + Doorkeeper Bloom filter)
- [ ] **SIM-11**: Add W-TinyLFU to the policy comparison in main.cpp and all sweeps

**SHARDS rigor:**

- [ ] **SIM-12**: Generate a ≥1M-access synthetic trace for SHARDS validation
- [ ] **SIM-13**: Report SHARDS error at 0.01%/0.1%/1%/10% on the large trace (targets 0.1% MAE at 1% sampling per the paper)

**Analysis & writeup:**

- [ ] **ANAL-01**: Cross-workload comparison: Congress vs court records (same 6 policies, 2 traces)
- [ ] **ANAL-02**: Discuss when each policy wins (skew, size distribution, OHW regime)
- [ ] **DOC-02**: Final report (flexible length, class-report style)
- [ ] **DOC-03**: AI-use report documenting what worked/didn't with Claude Code (professor request)
- [ ] **DOC-04**: Live-demo script for presentation (simulator runs with parameter sweeps)

### Out of Scope

- Production-grade caching system or real storage integration — this is a simulator
- Tracking real server-side traffic — we only replay synthetic popularity over real object metadata; Congress.gov and PACER don't publish access logs
- Multi-tier caching / distributed caches — single-tier object cache only
- Cost-based eviction (GDSF, LFUDA, etc.) beyond W-TinyLFU — scope containment
- Threading / concurrent cache access — simulator is single-threaded by design
- A third trace source — two domains are enough for the cross-workload story

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PACER (vs OpenSecrets, SEC EDGAR) as second trace | Stays in public-records legal-adjacent domain; contrasting size distribution (legal documents tend to be larger than bill JSON); richer endpoint taxonomy | — Pending |
| W-TinyLFU (vs just admission filter or basic TinyLFU) | Most impressive of the three options; matches what Caffeine ships; adding a frequency sketch is good systems-course material | — Pending |
| Larger SHARDS validation trace (synthetic, not real) | Real traces are rate-limited; synthetic gives enough scale (1M+ accesses) to meaningfully test 0.1% and 0.01% sampling | — Pending |
| Live simulator demo | More engaging than static slides; shows the system working; parameter sweeps let us illustrate findings in real time | — Pending |
| Replay-Zipf kept as primary analysis approach | Raw traces have near-zero temporal locality because they're client-generated random queries; replay-Zipf uses real keys/sizes with controlled popularity, which is what actually makes policy comparison meaningful | ✓ Validated in existing work |

## Risks

- **PACER trace collection is the highest-risk unknown.** Need to research access (PACER fees vs RECAP/CourtListener free tier), rate limits, and whether the endpoint structure supports the same replay-Zipf approach as Congress. Trace collection took a few hours for Congress (20K at ~1.6s/request); court records might be slower or require different throttling. This risk should be addressed early in the roadmap.
- **W-TinyLFU correctness.** Count-Min Sketch + Bloom filter + two cache regions is the most complex policy by far. Plan to validate against published W-TinyLFU results on known workloads before trusting our numbers.
- **Cross-workload story quality.** The writeup needs to say something interesting about *why* policies differ (or don't) across Congress vs PACER. If the two traces produce similar policy rankings, the writeup is duller. Mitigation: if the numbers are similar, the *similarity* itself is a finding (policies robust across legal public-records workloads).
- **Scope creep.** 4+ weeks runway is comfortable but not infinite. Budget time for report writing (often underestimated) and demo prep.

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after initialization*
