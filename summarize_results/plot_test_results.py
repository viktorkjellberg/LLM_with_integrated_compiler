#!/usr/bin/env python3
"""
Bar plot of test outcomes per language, baseline and agent side by side.

Each bar is stacked to 100% of runs:
  green = passed tests, red = compiled but failed tests, gray = did not compile.

Tasks whose test spec in all_tasks.xlsx is marked 'Assert': 'Manual'
are removed before anything is counted.

Usage:
    python plot_pass_rate_by_language.py \
        --results combined_results_all.csv \
        --tasks all_tasks.xlsx \
        --out pass_rate_by_language.png
"""
import argparse
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = {"Passed": "#2e9e4f", "Failed": "#d64541", "Not compiled": "#9e9e9e"}
TYPES = ["baseline", "agent"]
MANUAL_RE = re.compile(r"""['"]assert['"]\s*:\s*['"]manual['"]""", re.IGNORECASE)


def manual_tasks(tasks_path):
    """Return the set of task names whose tests are marked Manual."""
    tasks = pd.read_excel(tasks_path)
    is_manual = tasks["Tests"].astype(str).apply(lambda s: bool(MANUAL_RE.search(s)))
    return set(tasks.loc[is_manual, "Task_Name"].astype(str).str.strip())


def classify(df):
    """Label each run as Passed, Failed or Not compiled."""
    return np.select(
        [df["Compile_Result"] == 0, df["Test_Result"] == 1],
        ["Not compiled", "Passed"],
        default="Failed",
    )


def main():

    results = "summary/combined_results_all.csv"
    tasks = "../data/all_tasks.xlsx"
    out = "summary/pass_rate_by_language.png"

    df = pd.read_csv(results)
    df["Task_Name"] = df["Task_Name"].astype(str).str.strip()

    # 1. Remove manual tasks
    manual = manual_tasks(tasks)
    before = len(df)
    df = df[~df["Task_Name"].isin(manual)].copy()
    print(f"Removed {len(manual)} manual tasks ({before - len(df)} of {before} runs). "
          f"{df['Task_Name'].nunique()} tasks remain.")

    # 2. Outcome shares per language and type
    df["Outcome"] = classify(df)
    shares = (
        df.groupby(["Language", "Type"])["Outcome"]
        .value_counts(normalize=True)
        .mul(100)
        .unstack(fill_value=0)
        .reindex(columns=list(COLORS), fill_value=0)
    )
    counts = df.groupby(["Language", "Type"]).size()

    # Sort languages by agent pass rate, highest first
    languages = (
        shares.xs("agent", level="Type")["Passed"].sort_values(ascending=False).index.tolist()
    )

    print("\nShare of runs (%):")
    print(shares.reindex(pd.MultiIndex.from_product([languages, TYPES])).round(1).to_string())

    # 3. Plot
    width = 0.38
    gap = 0.04
    x = np.arange(len(languages))
    fig, ax = plt.subplots(figsize=(11, 6))

    for i, t in enumerate(TYPES):
        xpos = x + (i - 0.5) * (width + gap)
        bottom = np.zeros(len(languages))
        for outcome, color in COLORS.items():
            vals = np.array([shares.loc[(lang, t), outcome] for lang in languages])
            ax.bar(xpos, vals, width, bottom=bottom, color=color,
                   edgecolor="white", linewidth=0.8,
                   label=outcome if i == 0 else None)
            if outcome == "Passed":
                for xp, v in zip(xpos, vals):
                    ax.text(xp, v / 2 if v >= 6 else v + 1, f"{v:.1f}%",
                            ha="center", va="center" if v >= 6 else "bottom",
                            fontsize=8.5, color="white" if v >= 6 else "black",
                            fontweight="bold")
            bottom += vals
        for xp, lang in zip(xpos, languages):
            ax.text(xp, 101.5, t.capitalize(), ha="center", va="bottom", fontsize=8.5, color="#444")

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{lang}" for lang in languages],fontsize=14
    )
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("Tests Passed (%)", fontsize=14, fontweight="bold")
    ax.set_title("Test Results by Programming Language", pad=14, fontsize=16, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3, frameon=False, fontsize=14)
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"\nSaved plot to {out}")


if __name__ == "__main__":
    main()
