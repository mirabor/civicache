#!/usr/bin/env python3
"""
Generate figures from cache simulator CSV outputs.

Reads from results/ and writes PDFs to results/figures/.
Usage: python3 scripts/plot_results.py [--results-dir results]
"""

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

    # Plot each sampling rate
    rate_colors = {0.001: "#ff7f0e", 0.01: "#2ca02c", 0.1: "#9467bd"}
    for rate in sorted(df["sampling_rate"].unique()):
        sub = df[df["sampling_rate"] == rate].sort_values("cache_size")
        color = rate_colors.get(rate, "gray")
        ax.plot(sub["cache_size"] / 1e6, sub["miss_ratio"],
                label=f"SHARDS {rate*100:.1f}%",
                color=color, linewidth=1.2, alpha=0.8)

    # Overlay exact MRC if available
    if os.path.exists(exact_path):
        exact = pd.read_csv(exact_path)
        ax.plot(exact["cache_size"] / 1e6, exact["miss_ratio"],
                label="Exact", color="black", linewidth=2, linestyle="--")

    ax.set_xlabel("Cache Size (MB)")
    ax.set_ylabel("Miss Ratio")
    ax.set_title("SHARDS Approximate vs. Exact MRC")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.set_ylim(bottom=0)

    out = os.path.join(figures_dir, "shards_mrc.pdf")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


def main():
    parser = argparse.ArgumentParser(description="Plot cache simulation results")
    parser.add_argument("--results-dir", default="results",
                        help="Directory containing CSV outputs")
    args = parser.parse_args()

    figures_dir = os.path.join(args.results_dir, "figures")
    os.makedirs(figures_dir, exist_ok=True)

    print("Generating figures...")
    plot_mrc(args.results_dir, figures_dir)
    plot_alpha_sensitivity(args.results_dir, figures_dir)
    plot_ohw(args.results_dir, figures_dir)
    plot_shards(args.results_dir, figures_dir)
    print("Done.")


if __name__ == "__main__":
    main()
