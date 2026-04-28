#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

import pandas as pd
import matplotlib.pyplot as plt


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_output_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def normalize_iteration(value):
    try:
        return int(value)
    except Exception:
        return value


def extract_counts(data):
    """
    Count all compiler_error_types for each (Model, Iteration).

    Ignores items with no compiler errors.
    """
    counts = defaultdict(Counter)

    for item in data:
        if not isinstance(item, dict):
            continue

        model = item.get("Model")
        iteration = normalize_iteration(item.get("Iteration"))
        error_types = item.get("compiler_error_types", [])

        if model is None or iteration is None:
            continue

        if not isinstance(error_types, list) or not error_types:
            continue

        for err in error_types:
            if err and err != "no_error":
                counts[(model, iteration)][err] += 1

    return counts


def counts_to_dataframe(counts):
    rows = []

    for (model, iteration), counter in counts.items():
        for error_type, count in counter.items():
            rows.append(
                {
                    "Model": model,
                    "Iteration": iteration,
                    "compiler_error_type": error_type,
                    "count": count,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["Model", "Iteration", "compiler_error_type", "count"])

    df = pd.DataFrame(rows)
    return df.sort_values(["Model", "Iteration", "compiler_error_type"]).reset_index(drop=True)


def save_summary_csv(df, output_dir: Path):
    csv_path = output_dir / "compiler_error_counts_by_model_iteration.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    return csv_path


def plot_per_model(df, output_dir: Path):
    """
    Create one stacked bar chart per model.
    X-axis = iteration
    Y-axis = count
    Stacks = compiler_error_type
    """
    if df.empty:
        return []

    saved_paths = []

    for model in sorted(df["Model"].dropna().unique()):
        model_df = df[df["Model"] == model].copy()

        pivot = model_df.pivot_table(
            index="Iteration",
            columns="compiler_error_type",
            values="count",
            aggfunc="sum",
            fill_value=0,
        ).sort_index()

        if pivot.empty:
            continue

        fig, ax = plt.subplots(figsize=(12, 6))
        pivot.plot(kind="bar", stacked=True, ax=ax)

        ax.set_title(f"Compiler Error Types by Iteration for Model: {model}")
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Count")
        ax.legend(title="compiler_error_type", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.tight_layout()

        safe_model = (
            str(model)
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace(" ", "_")
        )
        out_path = output_dir / f"compiler_errors_{safe_model}.png"
        plt.savefig(out_path, dpi=200, bbox_inches="tight")
        plt.close(fig)

        saved_paths.append(out_path)

    return saved_paths


def plot_overall_by_model_and_iteration(df, output_dir: Path):
    """
    Summary plot:
    total number of compiler errors per model/iteration.
    """
    if df.empty:
        return None

    grouped = (
        df.groupby(["Model", "Iteration"], as_index=False)["count"]
        .sum()
        .sort_values(["Model", "Iteration"])
    )

    pivot = grouped.pivot_table(
        index="Iteration",
        columns="Model",
        values="count",
        aggfunc="sum",
        fill_value=0,
    ).sort_index()

    fig, ax = plt.subplots(figsize=(12, 6))
    pivot.plot(kind="bar", ax=ax)

    ax.set_title("Total Compiler Error Counts by Iteration and Model")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Total Error Count")
    ax.legend(title="Model", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()

    out_path = output_dir / "compiler_errors_total_by_model_iteration.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return out_path


def main():
    if len(sys.argv) != 2:
        print("Usage: python plot_compiler_errors_by_model_iteration.py <language>")
        sys.exit(1)

    input_path = Path(f'category_error/{sys.argv[1]}.json')
    output_dir = Path(f'category_error/{sys.argv[1]}/')

    if not input_path.exists() or not input_path.is_file():
        print(f"Error: invalid input file: {input_path}")
        sys.exit(1)

    ensure_output_dir(output_dir)

    data = load_json(input_path)
    counts = extract_counts(data)
    df = counts_to_dataframe(counts)

    csv_path = save_summary_csv(df, output_dir)
    model_plot_paths = plot_per_model(df, output_dir)
    overall_plot_path = plot_overall_by_model_and_iteration(df, output_dir)

    print(f"Saved summary CSV: {csv_path}")

    if overall_plot_path:
        print(f"Saved overall plot: {overall_plot_path}")

    if model_plot_paths:
        print("Saved per-model plots:")
        for path in model_plot_paths:
            print(path)
    else:
        print("No per-model plots were created.")


if __name__ == "__main__":
    main()