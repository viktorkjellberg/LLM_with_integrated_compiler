import json
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt


INPUT_FILE = "categorized_java_compile_errors.json"
OUTPUT_FILE = "errors_by_model.png"


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_error_categories(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()] if str(value).strip() else []


def build_long_dataframe(records):
    rows = []

    for record in records:
        model = record.get("Model", "Unknown")
        error_categories = normalize_error_categories(record.get("error_categories", []))

        for error in error_categories:
            rows.append({
                "Model": model,
                "error_category": error
            })

    return pd.DataFrame(rows)


def plot_grouped_bar(df, output_file, top_n=None):
    if df.empty:
        print("No error categories found in the file.")
        return

    counts = (
        df.groupby(["error_category", "Model"])
        .size()
        .reset_index(name="count")
    )

    if top_n is not None:
        top_errors = (
            counts.groupby("error_category")["count"]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .index
        )
        counts = counts[counts["error_category"].isin(top_errors)]

    pivot = counts.pivot(
        index="error_category",
        columns="Model",
        values="count"
    ).fillna(0)

    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

    ax = pivot.plot(kind="bar", figsize=(14, 7))
    ax.set_xlabel("Error category")
    ax.set_ylabel("Count")
    ax.set_title("Error Categories Made by Each Model")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.show()


def main():
    records = load_data(INPUT_FILE)
    df = build_long_dataframe(records)
    plot_grouped_bar(df, OUTPUT_FILE, top_n=None)  # set to None to show all categories


if __name__ == "__main__":
    main()