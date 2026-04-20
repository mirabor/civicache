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
    "W-TinyLFU": "#8c564b",
    # Phase 4 Axis C (D-11 / ABLA-01) — S3-FIFO small-queue-ratio ablation.
    # Sequential red family so the 3 variants read as related on the ablation
    # figure. S3-FIFO-10 reuses the legacy S3-FIFO hex so the ablation panel
    # is visually consistent with the main MRC/alpha figures.
    "S3-FIFO-5":  "#ff7f7f",  # lighter red (lower small-queue ratio)
    "S3-FIFO-10": "#d62728",  # matches legacy "S3-FIFO" — the default alias
    "S3-FIFO-20": "#8b0000",  # darker red (higher small-queue ratio)
}

POLICY_MARKERS = {
    "LRU": "o",
    "FIFO": "s",
    "CLOCK": "^",
    "S3-FIFO": "D",
    "SIEVE": "v",
    "W-TinyLFU": "P",
    # Phase 4 Axis C — distinguishable markers for the 3 S3-FIFO variants.
    # S3-FIFO-10 reuses the legacy "D" so the ablation's baseline rate reads
    # identically to the main-figure S3-FIFO line.
    "S3-FIFO-5":  "<",
    "S3-FIFO-10": "D",
    "S3-FIFO-20": ">",
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


def plot_shards_convergence(results_dir, figures_dir):
    """SHARDS self-convergence MAE vs. compared rate (D-01/D-02). Annotates
    n_samples_compared and flags <200 with asterisk per D-01 caveat."""
    path = os.path.join(results_dir, "shards_convergence.csv")
    if not os.path.exists(path):
        return  # silently skip — only exists after `make shards-large`
    df = pd.read_csv(path).sort_values("compared_rate")
    if df.empty:
        return

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df["compared_rate"] * 100, df["mae"],
            marker="o", color="#1f77b4", linewidth=1.5, markersize=7)
    for _, row in df.iterrows():
        n = int(row["n_samples_compared"])
        label = f"n={n}"
        if n < 200:
            label += "*"  # D-01 caveat: below paper-recommended 200-sample floor
        ax.annotate(label,
                    xy=(row["compared_rate"] * 100, row["mae"]),
                    xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=9)
    ax.set_xscale("log")
    ax.set_xlabel("Compared Sampling Rate (%, log scale)")
    ax.set_ylabel(f"MAE vs. {df['reference_rate'].iloc[0] * 100:.0f}% reference")
    ax.set_title("SHARDS Self-Convergence at 1M Accesses")
    ax.set_ylim(bottom=0)
    # Add a small footnote about the caveat marker if any rate triggers it
    if (df["n_samples_compared"] < 200).any():
        fig.text(0.5, -0.02,
                 "* compared rate below paper-recommended 200-sample floor (D-01)",
                 ha="center", fontsize=8, style="italic")

    out = os.path.join(figures_dir, "shards_convergence.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_shards_mrc_overlay(results_dir, figures_dir):
    """PITFALLS M3 money-shot: SHARDS approximations overlaid on exact MRC.
    Reads shards_mrc.csv (1M-scale, 4 rates) + exact_mrc.csv (50K oracle) +
    shards_mrc_50k.csv (50K SHARDS, for the oracle-regime overlay).
    """
    shards_path = os.path.join(results_dir, "shards_mrc.csv")
    exact_path = os.path.join(results_dir, "exact_mrc.csv")
    if not os.path.exists(shards_path):
        return  # only exists after `make shards-large`

    shards_df = pd.read_csv(shards_path)
    exact_df = pd.read_csv(exact_path) if os.path.exists(exact_path) else None
    shards50k_path = os.path.join(results_dir, "shards_mrc_50k.csv")
    shards50k_df = pd.read_csv(shards50k_path) if os.path.exists(shards50k_path) else None

    fig, ax = plt.subplots(figsize=(8, 5))

    # Exact MRC (50K oracle) — solid black baseline
    if exact_df is not None:
        exact_col = "cache_size_objects" if "cache_size_objects" in exact_df.columns else "cache_size"
        ax.plot(exact_df[exact_col], exact_df["miss_ratio"],
                color="black", linewidth=2.0, label="Exact MRC (50K oracle)",
                linestyle="-", zorder=10)

    # 50K SHARDS overlays — dotted lines, thin/transparent to distinguish from 1M
    if shards50k_df is not None:
        size_col50 = "cache_size_objects" if "cache_size_objects" in shards50k_df.columns else "cache_size"
        for rate in sorted(shards50k_df["sampling_rate"].unique()):
            sub = shards50k_df[shards50k_df["sampling_rate"] == rate].sort_values(size_col50)
            ax.plot(sub[size_col50], sub["miss_ratio"],
                    linestyle=":", linewidth=1.0, alpha=0.5,
                    label=f"SHARDS {rate*100:g}% (50K)")

    # 1M SHARDS overlays — dashed lines, full opacity
    size_col = "cache_size_objects" if "cache_size_objects" in shards_df.columns else "cache_size"
    for rate in sorted(shards_df["sampling_rate"].unique()):
        sub = shards_df[shards_df["sampling_rate"] == rate].sort_values(size_col)
        ax.plot(sub[size_col], sub["miss_ratio"],
                linestyle="--", linewidth=1.5,
                label=f"SHARDS {rate*100:g}% (1M)")

    ax.set_xlabel("Cache Size (objects)")
    ax.set_ylabel("Miss Ratio")
    ax.set_title("SHARDS Approximation vs. Exact MRC")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax.set_ylim(bottom=0)

    out = os.path.join(figures_dir, "shards_mrc_overlay.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def plot_ablation_s3fifo(figures_dir, congress_dir="results/congress",
                          court_dir="results/court"):
    """S3-FIFO small-queue-ratio ablation figure (D-11 / ABLA-01).

    2-workload-panel grid sharing y-axis: Congress | Court. Each panel plots
    miss_ratio vs. Zipf alpha for the 3 small_frac variants (S3-FIFO-5,
    S3-FIFO-10, S3-FIFO-20) at fixed 1% cache (D-13, via the simulator's
    --alpha-sweep code path that hardcodes wb/100 at src/main.cpp alpha loop).

    Reads results/{congress,court}/ablation_s3fifo.csv produced by
    `make ablation-s3fifo`. Both CSVs must exist for the figure to render;
    if either is missing the function silently skips (standard Phase 4 plot
    convention — lets `make plots` run standalone after partial sweeps).

    Writes results/<workload>/figures/ablation_s3fifo.pdf. Because the
    existing `make plots` pipeline derives `figures_dir` from `--workload`,
    this function is called once per invocation — the figure content is
    identical across workload invocations (same data, same renderer) but
    the PDF is written into each per-workload figures_dir so either
    workload's figure set is self-contained.
    """
    cong_path = os.path.join(congress_dir, "ablation_s3fifo.csv")
    court_path = os.path.join(court_dir, "ablation_s3fifo.csv")
    if not (os.path.exists(cong_path) and os.path.exists(court_path)):
        print(f"  Skipping S3-FIFO ablation plot: both "
              f"{cong_path} and {court_path} required")
        return

    c_df = pd.read_csv(cong_path); c_df["workload"] = "Congress"
    k_df = pd.read_csv(court_path); k_df["workload"] = "Court"
    df = pd.concat([c_df, k_df], ignore_index=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, wl in zip([ax1, ax2], ["Congress", "Court"]):
        sub_all = df[df["workload"] == wl]
        # Sort policies so the legend order is 5 -> 10 -> 20 rather than
        # lexicographic (which would put 10 before 5 due to string sort).
        policies_sorted = sorted(
            sub_all["policy"].unique(),
            key=lambda p: int(p.split("-")[-1]) if p.split("-")[-1].isdigit() else 0,
        )
        for policy in policies_sorted:
            sub = sub_all[sub_all["policy"] == policy].sort_values("alpha")
            color = POLICY_COLORS.get(policy, "gray")
            marker = POLICY_MARKERS.get(policy, "x")
            ax.plot(sub["alpha"], sub["miss_ratio"],
                    marker=marker, markersize=5, label=policy,
                    color=color, linewidth=1.5)
        ax.set_xlabel("Zipf Alpha")
        ax.set_title(wl)
        ax.set_ylim(bottom=0)
    ax1.set_ylabel("Miss Ratio (1% cache)")
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="small_frac")
    fig.suptitle("S3-FIFO small-queue-ratio sensitivity (D-11 / ABLA-01)")

    out = os.path.join(figures_dir, "ablation_s3fifo.pdf")
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
    plot_shards_convergence(results_dir, figures_dir)
    plot_shards_mrc_overlay(results_dir, figures_dir)
    # Phase 4 ablation figures: 2-workload panel layouts. Each reads both
    # Congress + Court ablation CSVs and writes into the current workload's
    # figures_dir, so `make plots WORKLOAD=congress` and `make plots
    # WORKLOAD=court` each refresh their own copy. Silently skipped when
    # either source CSV is missing.
    plot_ablation_s3fifo(figures_dir)
    plot_workload(args.traces_dir, figures_dir, args.workload)
    print("Done.")


if __name__ == "__main__":
    main()
