import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
from matplotlib.patches import Patch


ERROR_CATEGORIES = [
    "Syntax",
    "Semantic",
    "Dependency",
    "Type mismatch",
    "Language specific",
    "Other",
]


NEW_LABELS = {
    "codellama:34b": "Code Llama 34B",
    "codellama:7b": "Code Llama 7B",
    "deepseek-coder-v2:16b": "DeepSeek Coder V2 16B",
    "deepseek-r1:70b": "DeepSeek R1 70B",
    "deepseek-r1:7b": "DeepSeek R1 7B",
    "gemma3:12b": "Gemma 3 12B",
    "gemma3:27b": "Gemma 3 27B",
    "gpt-5.4": "GPT 5.4",
    "gpt-5.4-mini": "GPT 5.4 mini",
    "gpt-oss:120b": "GPT OSS 120B",
    "gpt-oss:20b": "GPT OSS 20B",
    "llama3.3:70b": "Llama 3.3 70B",
    "phi4": "Phi 4 14B",
    "qwen3-coder:30b": "Qwen3 Coder 30B",
    "qwen3:14b": "Qwen3 14B",
    "qwen3:32b": "Qwen3 32B",
    "qwen3:4b": "Qwen3 4B",
    "qwen3:8b": "Qwen3 8B",
}


def create_stacked_plot(
    df,
    group_column,
    output_file,
    title,
    xlabel,
    label_map=None,
):
    # Aggregate counts by group and Agent/Baseline
    grouped = (
        df.groupby([group_column, "Agent/Baseline"])[ERROR_CATEGORIES]
        .sum()
        .reset_index()
    )

    groups = sorted(grouped[group_column].dropna().unique())

    x = np.arange(len(groups))
    width = 0.38

    # Make figure wider if there are many groups
    fig_width = max(14, len(groups) * 1.8)

    fig, ax = plt.subplots(figsize=(fig_width, 9))

    # Use matplotlib default colors
    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for run_index, run_type in enumerate(["Agent", "Baseline"]):

        offset = -width / 2 if run_type == "Baseline" else width / 2

        bottoms = np.zeros(len(groups))

        for category_index, category in enumerate(ERROR_CATEGORIES):

            values = []

            for group in groups:
                match = grouped[
                    (grouped[group_column] == group)
                    & (grouped["Agent/Baseline"] == run_type)
                ]

                if match.empty:
                    values.append(0)
                else:
                    values.append(match[category].iloc[0])

            values = np.array(values)

            ax.bar(
                x + offset,
                values,
                width,
                bottom=bottoms,
                label=category if run_index == 0 else None,
                color=colors[
                    category_index % len(colors)
                ],
                edgecolor="black",
                linewidth=0.6,
                hatch="" if run_type == "Agent" else "//",
            )

            bottoms += values

    # Main title
    ax.set_title(
        title,
        fontsize=22,
        pad=18,
    )

    # Axis labels
    ax.set_xlabel(
        xlabel,
        fontsize=18,
        labelpad=12,
    )

    ax.set_ylabel(
        "Number of errors",
        fontsize=18,
        labelpad=12,
    )

    # X ticks
    ax.set_xticks(x)

    if label_map is not None:
        display_labels = [
            label_map.get(group, group)
            for group in groups
        ]
    else:
        display_labels = groups

    ax.set_xticklabels(
        display_labels,
        rotation=45,
        ha="right",
        fontsize=14,
    )

    # Y ticks
    ax.tick_params(
        axis="y",
        labelsize=14,
    )

    # Grid
    ax.grid(
        axis="y",
        alpha=0.25,
    )

    # Error-category legend
    category_legend = ax.legend(
        title="Error category",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=14,
        title_fontsize=15,
    )

    ax.add_artist(category_legend)

    # Separate legend for Agent/Baseline
    run_legend = [
        Patch(
            facecolor="white",
            edgecolor="black",
            hatch="//",
            label="Baseline",
        ),
        Patch(
            facecolor="white",
            edgecolor="black",
            label="Agent",
        ),

    ]

    ax.legend(
        handles=run_legend,
        title="Type",
        bbox_to_anchor=(1.02, 0.55),
        loc="upper left",
        fontsize=14,
        title_fontsize=15,
    )

    plt.tight_layout()

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Saved: {output_file}")


def main():

    if len(sys.argv) < 2:
        print(
            "Usage: python create_error_plots.py "
            "<category_counts_iteration_4.xlsx>"
        )
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"File not found: {input_file}")
        sys.exit(1)

    # Read Excel file
    df = pd.read_excel(input_file)

    required_columns = [
        "Language",
        "Model",
        "Agent/Baseline",
        *ERROR_CATEGORIES,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print("Missing required columns:")

        for column in missing_columns:
            print(f"  - {column}")

        sys.exit(1)

    # Ensure error columns are numeric
    for category in ERROR_CATEGORIES:
        df[category] = pd.to_numeric(
            df[category],
            errors="coerce",
        ).fillna(0)

    output_folder = input_file.parent

    # -----------------------------------
    # Plot 1: errors by language
    # -----------------------------------

    create_stacked_plot(
        df=df,
        group_column="Language",
        output_file=(
            output_folder
            / "errors_by_language.png"
        ),
        title=(
            "Error Categories by Language: "
            "Agent vs Baseline"
        ),
        xlabel="Language",
    )

    # -----------------------------------
    # Plot 2: errors by model
    # -----------------------------------

    create_stacked_plot(
        df=df,
        group_column="Model",
        output_file=(
            output_folder
            / "errors_by_model.png"
        ),
        title=(
            "Error Categories by Model"
        ),
        xlabel="Model",
        label_map=NEW_LABELS,
    )


if __name__ == "__main__":
    main()