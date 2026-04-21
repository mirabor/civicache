#!/usr/bin/env python3
"""
Cross-workload aggregation: load multi-seed CSVs from Plan 05-03, compute
mean/std/p_value/significant per (group, policy) cell, write aggregated CSVs
for downstream plots (Plan 05-05) and regime tables (Plan 05-06).

Reads:
    results/compare/multiseed/{congress,court}/{mrc,alpha_sensitivity}_seed{42,7,13,23,31}.csv

Writes:
    results/compare/aggregated/{congress,court}/mrc_aggregated.csv
    results/compare/aggregated/{congress,court}/alpha_sensitivity_aggregated.csv

Aggregation semantics (D-02):
    - Group by (cache_frac, policy) for MRC; (alpha, policy) for alpha-sensitivity.
    - mean = miss_ratio.mean() across 5 seeds; std = miss_ratio.std(ddof=1).
    - p_value = scipy.stats.ttest_ind(policy_vals, lru_vals, equal_var=False) — Welch's.
    - significant = (p_value < 0.05); LRU rows get p_value=NaN, significant=True.

Usage:
    python3 scripts/compare_workloads.py [--compare-dir results/compare]
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

# Module-level constants — grep-discoverable per Phase 2 check_wtlfu_acceptance.py pattern.
SEEDS = [42, 7, 13, 23, 31]                  # D-05: 5-seed CI
REFERENCE_CACHE_FRAC = 0.01                  # D-01 OHW-regime cell
HIGH_SKEW_ALPHAS = [1.0, 1.1, 1.2]           # D-01 high-skew regime
SMALL_CACHE_FRAC = 0.001                     # D-01 small-cache regime
P_SIG = 0.05                                 # D-02 Welch's t-test significance threshold
WORKLOADS = ["congress", "court"]
STEMS = ["mrc", "alpha_sensitivity"]
LRU_KEY = "LRU"


def load_multiseed(multiseed_dir, workload, stem):
    """Load all 5 per-seed CSVs for one (workload, stem) cell; return merged DataFrame.

    Missing seeds print a warning and are skipped (n < 5 at downstream aggregation);
    the `n` column in the aggregated CSV exposes the actual count.
    """
    dfs = []
    for seed in SEEDS:
        path = os.path.join(multiseed_dir, workload, f"{stem}_seed{seed}.csv")
        if not os.path.exists(path):
            print(f"  Warning: {path} not found — skipping seed {seed}", file=sys.stderr)
            continue
        df = pd.read_csv(path)
        df["seed"] = seed
        dfs.append(df)
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def aggregate(df, group_cols, pass_through_cols=()):
    """Aggregate per-seed values into mean/std/p_value/significant per (group, policy).

    Args:
        df: merged DataFrame with seed column added by load_multiseed.
        group_cols: list of column names to group by (e.g., ['cache_frac'] or ['alpha']).
        pass_through_cols: extra columns to preserve via mean() (e.g., 'cache_size_bytes').

    Returns:
        DataFrame with columns: *group_cols, *pass_through_cols, policy, mean, std, n,
        p_value, significant — sorted by (*group_cols, policy) for reproducibility.
    """
    rows = []
    for key_vals, group_df in df.groupby(group_cols):
        # Normalize key_vals to a tuple even when groupby single-column.
        if not isinstance(key_vals, tuple):
            key_vals = (key_vals,)
        # LRU reference values for Welch's t-test.
        lru_vals = group_df.loc[group_df["policy"] == LRU_KEY, "miss_ratio"].values
        if len(lru_vals) < 2:
            # Cannot run t-test without ≥ 2 LRU samples. Falls through to NaN p-values.
            lru_vals = None

        for policy, pol_df in group_df.groupby("policy"):
            vals = pol_df["miss_ratio"].values
            n = len(vals)
            mean_v = float(vals.mean()) if n > 0 else float("nan")
            std_v = float(vals.std(ddof=1)) if n > 1 else float("nan")

            # Welch's t-test vs LRU per D-02.
            if policy == LRU_KEY or lru_vals is None or n < 2:
                p_value = float("nan")
                # LRU is the reference, so 'significant' is True by definition
                # (no comparison made). For non-LRU with n<2, also True — can't test.
                significant = True
            else:
                try:
                    _, p_value = stats.ttest_ind(vals, lru_vals, equal_var=False)
                    # scipy returns NaN when both samples have zero variance (T-05-04-02).
                    if np.isnan(p_value):
                        significant = False
                    else:
                        significant = bool(p_value < P_SIG)
                except (ValueError, ZeroDivisionError):
                    p_value = float("nan")
                    significant = False

            row = dict(zip(group_cols, key_vals))
            for pt in pass_through_cols:
                if pt in pol_df.columns:
                    row[pt] = float(pol_df[pt].mean())
            row["policy"] = policy
            row["mean"] = mean_v
            row["std"] = std_v
            row["n"] = n
            row["p_value"] = p_value
            row["significant"] = significant
            rows.append(row)

    agg = pd.DataFrame(rows)
    if agg.empty:
        return agg
    # Deterministic sort for reproducibility (T-05-04-04).
    sort_cols = list(group_cols) + ["policy"]
    return agg.sort_values(sort_cols).reset_index(drop=True)


def write_aggregated(agg_df, out_path):
    """Write aggregated DataFrame with os.makedirs + to_csv pattern
    (matches scripts/workload_stats_json.py line 120-123 idiom)."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    agg_df.to_csv(out_path, index=False)
    print(f"  Wrote {out_path} ({len(agg_df)} rows)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--compare-dir", default="results/compare",
                    help="Base compare/ directory (default: results/compare)")
    ap.add_argument("--congress-dir", default=None,
                    help="Override Congress workload subdir name (default: 'congress')")
    ap.add_argument("--court-dir", default=None,
                    help="Override Court workload subdir name (default: 'court')")
    args = ap.parse_args()

    multiseed_dir = os.path.join(args.compare_dir, "multiseed")
    aggregated_dir = os.path.join(args.compare_dir, "aggregated")

    if not os.path.isdir(multiseed_dir):
        print(f"Error: {multiseed_dir} not found — run "
              f"scripts/run_multiseed_sweep.py first.", file=sys.stderr)
        return 1

    # Allow per-workload subdir overrides (rare; default is the workload name itself).
    workload_subdirs = {
        "congress": args.congress_dir or "congress",
        "court": args.court_dir or "court",
    }

    print(f"=== Aggregating 5-seed CSVs from {multiseed_dir} ===")

    for workload in WORKLOADS:
        subdir = workload_subdirs[workload]

        # MRC aggregation: group by cache_frac, pass cache_size_bytes through.
        mrc_df = load_multiseed(multiseed_dir, subdir, "mrc")
        if mrc_df is None:
            print(f"  Warning: no MRC CSVs for {workload} — skipping", file=sys.stderr)
        else:
            mrc_agg = aggregate(mrc_df, ["cache_frac"],
                                pass_through_cols=("cache_size_bytes",))
            # Reorder columns to match documented schema.
            mrc_schema = ["cache_frac", "cache_size_bytes", "policy",
                          "mean", "std", "n", "p_value", "significant"]
            mrc_agg = mrc_agg[[c for c in mrc_schema if c in mrc_agg.columns]]
            write_aggregated(mrc_agg,
                             os.path.join(aggregated_dir, workload, "mrc_aggregated.csv"))

        # Alpha-sensitivity aggregation: group by alpha, no pass-through.
        alpha_df = load_multiseed(multiseed_dir, subdir, "alpha_sensitivity")
        if alpha_df is None:
            print(f"  Warning: no alpha_sensitivity CSVs for {workload} — skipping",
                  file=sys.stderr)
        else:
            alpha_agg = aggregate(alpha_df, ["alpha"])
            alpha_schema = ["alpha", "policy", "mean", "std", "n", "p_value", "significant"]
            alpha_agg = alpha_agg[[c for c in alpha_schema if c in alpha_agg.columns]]
            write_aggregated(alpha_agg,
                             os.path.join(aggregated_dir, workload,
                                          "alpha_sensitivity_aggregated.csv"))

    print("=== Aggregation complete. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
