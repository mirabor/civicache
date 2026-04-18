# Cache Policy Simulator for Legislative API Workloads

**CS 2640 Final Project**

Compares five cache eviction policies — LRU, FIFO, CLOCK, S3-FIFO, and SIEVE — on synthetic Zipf workloads and real Congress.gov API traces. Includes SHARDS-based miss ratio curve (MRC) construction for efficient cache sizing analysis.

## Policies

| Policy | Description |
|--------|-------------|
| **LRU** | Least Recently Used — doubly-linked list + hash map |
| **FIFO** | First-In First-Out — no promotion on cache hit |
| **CLOCK** | Approximation of LRU with visited bits and a clock hand |
| **S3-FIFO** | Small FIFO (10%) + Main FIFO (90%) + ghost filter with 2-bit frequency counters |
| **SIEVE** | Lazy promotion with a roving hand pointer (NSDI '24) |

## Build

Requires a C++17 compiler. No external C++ dependencies.

```bash
make          # builds cache_sim
```

## Run

### Synthetic benchmark (default)

```bash
make run
# or directly:
./cache_sim
```

This generates a 500K-request Zipf trace (alpha=0.8, 50K objects) and runs all five policies at varying cache sizes.

### Full analysis with alpha sweep and SHARDS

```bash
make run-sweep
```

### CLI options

```
./cache_sim [options]
  --trace <file>         Use a trace CSV instead of synthetic generation
  --cache-sizes <list>   Comma-separated cache size fractions (e.g., 0.01,0.05,0.1)
  --policies <list>      Comma-separated policies: lru,fifo,clock,s3fifo,sieve
  --output-dir <dir>     Output directory (default: results)
  --num-requests <n>     Number of synthetic requests (default: 500000)
  --num-objects <n>      Number of unique objects (default: 50000)
  --alpha <a>            Zipf alpha for single run (default: 0.8)
  --alpha-sweep          Run alpha sensitivity sweep (0.6 to 1.2)
  --shards               Run SHARDS MRC construction
  --shards-exact         Also compute exact stack distances (slow)
  --replay-zipf          Resample a real trace with Zipf popularity (use with --trace)
```

### Collect a real trace from Congress.gov

Requires a [Congress.gov API key](https://api.congress.gov/).

```bash
export CONGRESS_API_KEY=your_key_here
python3 scripts/collect_trace.py --requests 5000 --output traces/congress_trace.csv
```

Then run the simulator on it. Use `--replay-zipf` to overlay Zipf popularity on real keys/sizes:

```bash
./cache_sim --trace traces/congress_trace.csv --replay-zipf --alpha-sweep --shards
```

### Generate plots

Requires Python 3 with dependencies listed in `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make plots
# Figures saved to results/figures/
```

## Output

Results are written to `results/` as CSV files:

- `mrc.csv` — miss ratio vs. cache size for all policies
- `alpha_sensitivity.csv` — miss ratio vs. Zipf alpha
- `one_hit_wonder.csv` — OHW ratio at different window lengths
- `shards_mrc.csv` — SHARDS approximate MRC at multiple sampling rates
- `exact_mrc.csv` — exact MRC (if `--shards-exact` was used)

Plots are saved to `results/figures/` as PDFs.

## Project Structure

```
├── include/
│   ├── cache.h              # Five eviction policy implementations
│   ├── trace_gen.h          # Trace generation and loading
│   ├── workload_stats.h     # Workload characterization
│   └── shards.h             # SHARDS MRC construction
├── src/
│   ├── main.cpp             # CLI driver
│   ├── trace_gen.cpp         # Zipf generator + trace I/O
│   ├── workload_stats.cpp    # Alpha estimation (MLE), OHW ratio
│   └── shards.cpp            # SHARDS spatial sampling
├── scripts/
│   ├── collect_trace.py      # Congress.gov API trace collector
│   └── plot_results.py       # matplotlib figure generation
├── Makefile
└── README.md
```

## References

- Waldspurger, C. et al. "Efficient MRC Construction with SHARDS." USENIX FAST 2015.
- Yang, J. et al. "FIFO Queues Are All You Need for Cache Eviction." SOSP 2023.
- Zhang, Y. et al. "SIEVE Is Simpler Than LRU." NSDI 2024.
- Clauset, A. et al. "Power-Law Distributions in Empirical Data." SIAM Review, 2009.
