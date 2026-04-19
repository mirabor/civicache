#!/usr/bin/env python3
"""
Generate figures from cache simulator CSV outputs.

Reads from results/ and writes PDFs to results/figures/.
Usage: python3 scripts/plot_results.py [--results-dir results]
"""

# CSV schemas (kept in sync with src/main.cpp):
#   mrc.csv:              cache_frac, cache_size_bytes, policy, miss_ratio,
#                         byte_miss_ratio, accesses_per_sec
#   alpha_sensitivity.csv: alpha, policy, miss_ratio, byte_miss_ratio,
#                         accesses_per_sec
#   shards_mrc.csv:       sampling_rate, cache_size_objects, miss_ratio,
#                         accesses_per_sec
#   one_hit_wonder.csv:   window_frac, ohw_ratio
#   exact_mrc.csv:        cache_size_objects, miss_ratio
#   shards_error.csv:     sampling_rate, mae, max_abs_error, num_points
# Readers below tolerate older CSVs that lack accesses_per_sec (REFACTOR-03):
# the column is used only if present; existing miss-ratio plots do not depend
# on it. Throughput/Pareto plots are deferred to Phase 5 (ANAL-01).

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Clean plot style: no grid, legend outside, readable fonts
plt.rcParams.update({
    "font.size": 11,
    "font.family": "serif",
    "axes.grid": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "figure.dpi": 150,
})

POLICY_COLORS = {
    "LRU": "#1f77b4",
    "FIFO": "#ff7f0e",
    "CLOCK": "#2ca02c",
    "S3-FIFO": "#d62728",
    "SIEVE": "#9467bd",
}

POLICY_MARKERS = {
    "LRU": "o",
    "FIFO": "s",
    "CLOCK": "^",
    "S3-FIFO": "D",
    "SIEVE": "v",
}


def _has_throughput(df):
    """True if the DataFrame carries the accesses_per_sec column."""
    return "accesses_per_sec" in df.columns


def plot_mrc(results_dir, figures_dir):
    """Miss ratio vs. cache size (all 5 policies)."""
    path = os.path.join(results_dir, "mrc.csv")
    if not os.path.exists(path):
        print(f"  Skipping MRC plot: {path} not found")
        return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for policy in df["policy"].unique():
        sub = df[df["policy"] == policy].sort_values("cache_frac")
        color = POLICY_COLORS.get(policy, "gray")
        marker = POLICY_MARKERS.get(policy, "x")
        ax.plot(sub["cache_frac"] * 100, sub["miss_ratio"],
                marker=marker, markersize=5, label=policy,
                color=color, linewidth=1.5)

    ax.set_xlabel("Cache Size (% of working set)")
    ax.set_ylabel("Miss Ratio")
    ax.set_title("Miss Ratio Curves")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_ylim(bottom=0)

    out = os.path.join(figures_dir, "mrc.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_byte_mrc(results_dir, figures_dir):
    """Object miss ratio vs. byte miss ratio side by side."""
    path = os.path.join(results_dir, "mrc.csv")
    if not os.path.exists(path):
        print(f"  Skipping byte MRC plot: {path} not found")
        return

    df = pd.read_csv(path)
    if "byte_miss_ratio" not in df.columns:
        print(f"  Skipping byte MRC plot: no byte_miss_ratio column")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)

    for policy in df["policy"].unique():
        sub = df[df["policy"] == policy].sort_values("cache_frac")
        color = POLICY_COLORS.get(policy, "gray")
        marker = POLICY_MARKERS.get(policy, "x")
        ax1.plot(sub["cache_frac"] * 100, sub["miss_ratio"],
                 marker=marker, markersize=5, label=policy,
                 color=color, linewidth=1.5)
        ax2.plot(sub["cache_frac"] * 100, sub["byte_miss_ratio"],
                 marker=marker, markersize=5, label=policy,
                 color=color, linewidth=1.5)

    ax1.set_xlabel("Cache Size (% of working set)")
    ax1.set_ylabel("Miss Ratio")
    ax1.set_title("Object Miss Ratio")
    ax1.set_ylim(bottom=0)

    ax2.set_xlabel("Cache Size (% of working set)")
    ax2.set_title("Byte Miss Ratio")
    ax2.set_ylim(bottom=0)
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left")

    out = os.path.join(figures_dir, "byte_mrc.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_alpha_sensitivity(results_dir, figures_dir):
    """Miss ratio vs. Zipf alpha (all 5 policies)."""
    path = os.path.join(results_dir, "alpha_sensitivity.csv")
    if not os.path.exists(path):
        print(f"  Skipping alpha plot: {path} not found")
        return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for policy in df["policy"].unique():
        sub = df[df["policy"] == policy].sort_values("alpha")
        color = POLICY_COLORS.get(policy, "gray")
        marker = POLICY_MARKERS.get(policy, "x")
        ax.plot(sub["alpha"], sub["miss_ratio"],
                marker=marker, markersize=5, label=policy,
                color=color, linewidth=1.5)

    ax.set_xlabel("Zipf Alpha")
    ax.set_ylabel("Miss Ratio (1% cache)")
    ax.set_title("Alpha Sensitivity")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_ylim(bottom=0)

    out = os.path.join(figures_dir, "alpha_sensitivity.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_ohw(results_dir, figures_dir):
    """One-hit-wonder ratio vs. window length."""
    path = os.path.join(results_dir, "one_hit_wonder.csv")
    if not os.path.exists(path):
        print(f"  Skipping OHW plot: {path} not found")
        return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df["window_frac"] * 100, df["ohw_ratio"],
            marker="o", color="#1f77b4", linewidth=1.5, markersize=6)
    ax.set_xlabel("Window Size (% of trace)")
    ax.set_ylabel("One-Hit-Wonder Ratio")
    ax.set_title("One-Hit Wonders vs. Window Length")
    ax.set_ylim(0, 1)

    out = os.path.join(figures_dir, "ohw.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_shards(results_dir, figures_dir):
    """SHARDS approximate MRC vs. exact MRC overlay."""
    shards_path = os.path.join(results_dir, "shards_mrc.csv")
    exact_path = os.path.join(results_dir, "exact_mrc.csv")

    if not os.path.exists(shards_path):
        print(f"  Skipping SHARDS plot: {shards_path} not found")
        return

    df = pd.read_csv(shards_path)

    fig, ax = plt.subplots(figsize=(7, 4.5))

    # Detect column name (cache_size_objects or legacy cache_size)
    size_col = "cache_size_objects" if "cache_size_objects" in df.columns else "cache_size"

    # Plot each sampling rate
    rate_colors = {0.001: "#ff7f0e", 0.01: "#2ca02c", 0.1: "#9467bd"}
    for rate in sorted(df["sampling_rate"].unique()):
        sub = df[df["sampling_rate"] == rate].sort_values(size_col)
        color = rate_colors.get(rate, "gray")
        ax.plot(sub[size_col], sub["miss_ratio"],
                label=f"SHARDS {rate*100:.1f}%",
                color=color, linewidth=1.2, alpha=0.8)

    # Overlay exact MRC if available
    if os.path.exists(exact_path):
        exact = pd.read_csv(exact_path)
        exact_col = "cache_size_objects" if "cache_size_objects" in exact.columns else "cache_size"
        ax.plot(exact[exact_col], exact["miss_ratio"],
                label="Exact", color="black", linewidth=2, linestyle="--")

    ax.set_xlabel("Cache Size (objects)")
    ax.set_ylabel("Miss Ratio")
    ax.set_title("SHARDS Approximate vs. Exact MRC")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_ylim(bottom=0)

    out = os.path.join(figures_dir, "shards_mrc.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_workload(traces_dir, figures_dir, workload="congress"):
    """Size distribution histogram and endpoint type breakdown."""
    # Look for the trace CSV
    trace_path = os.path.join(traces_dir, f"{workload}_trace.csv")
    if not os.path.exists(trace_path):
        print(f"  Skipping workload plot: {trace_path} not found")
        return

    df = pd.read_csv(trace_path)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

    # Size distribution histogram
    sizes = df["size"]
    ax1.hist(sizes, bins=50, color="#1f77b4", edgecolor="white", linewidth=0.3)
    ax1.axvline(sizes.median(), color="#d62728", linestyle="--", linewidth=1.2,
                label=f"Median ({int(sizes.median())} B)")
    ax1.axvline(sizes.mean(), color="#ff7f0e", linestyle="--", linewidth=1.2,
                label=f"Mean ({int(sizes.mean())} B)")
    ax1.set_xlabel("Response Size (bytes)")
    ax1.set_ylabel("Count")
    ax1.set_title("Response Size Distribution")
    ax1.legend()

    # Endpoint type breakdown
    def get_endpoint_type(key):
        if isinstance(key, str):
            return key.split("/")[0]
        return "unknown"

    df["endpoint_type"] = df["key"].apply(get_endpoint_type)
    counts = df["endpoint_type"].value_counts()
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    ax2.bar(counts.index, counts.values, color=colors[:len(counts)],
            edgecolor="white", linewidth=0.5)
    ax2.set_xlabel("Endpoint Type")
    ax2.set_ylabel("Request Count")
    ax2.set_title("Requests by Endpoint Type")

    # Add percentage labels on bars
    total = counts.sum()
    for i, (idx, val) in enumerate(counts.items()):
        ax2.text(i, val + total * 0.01, f"{val/total*100:.1f}%",
                 ha="center", fontsize=9)

    fig.tight_layout()
    out = os.path.join(figures_dir, "workload.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_shards_error(results_dir, figures_dir):
    """Bar chart of SHARDS MAE and max error by sampling rate."""
    path = os.path.join(results_dir, "shards_error.csv")
    if not os.path.exists(path):
        return  # silently skip, only exists after --shards-exact

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(5, 4))
    x = np.arange(len(df))
    width = 0.35
    labels = [f"{r*100:.1f}%" for r in df["sampling_rate"]]

    ax.bar(x - width/2, df["mae"], width, label="MAE", color="#1f77b4")
    ax.bar(x + width/2, df["max_abs_error"], width, label="Max Error", color="#d62728")
    ax.set_xlabel("Sampling Rate")
    ax.set_ylabel("Absolute Error (miss ratio)")
    ax.set_title("SHARDS Approximation Error")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()

    out = os.path.join(figures_dir, "shards_error.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    parser = argparse.ArgumentParser(description="Plot cache simulation results")
    parser.add_argument("--workload", default="congress",
                        help="Workload subdir under results/ (default: congress)")
    parser.add_argument("--results-dir", default=None,
                        help="Directory containing CSV outputs "
                             "(overrides --workload-derived path)")
    parser.add_argument("--traces-dir", default="traces",
                        help="Directory containing raw trace CSVs")
    args = parser.parse_args()

    # Derive results_dir from --workload unless --results-dir is passed
    # explicitly (D-05 back-compat).
    results_dir = args.results_dir or os.path.join("results", args.workload)

    figures_dir = os.path.join(results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    print(f"Generating figures for workload '{args.workload}' from {results_dir}...")
    plot_mrc(results_dir, figures_dir)
    plot_byte_mrc(results_dir, figures_dir)
    plot_alpha_sensitivity(results_dir, figures_dir)
    plot_ohw(results_dir, figures_dir)
    plot_shards(results_dir, figures_dir)
    plot_shards_error(results_dir, figures_dir)
    plot_workload(args.traces_dir, figures_dir, args.workload)
    print("Done.")


if __name__ == "__main__":
    main()
