import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import textwrap
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


def wrap_label(label, width=16):
    return "\n".join(
        textwrap.wrap(
            str(label),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def create_stacked_plot(
    df,
    group_column,
    output_file,
    title,
    ylabel,
    label_map=None,
):
    # Aggregate counts
    grouped = (
        df.groupby(
            [group_column, "Agent/Baseline"]
        )[ERROR_CATEGORIES]
        .sum()
        .reset_index()
    )

    groups = sorted(
        grouped[group_column]
        .dropna()
        .unique()
    )

    y = np.arange(len(groups))
    height = 0.38

    # Taller when there are many models
    fig_height = max(
        10,
        len(groups) * 1.05,
    )

    # Make the figure much wider so there is
    # dedicated space for the legends
    fig, ax = plt.subplots(
        figsize=(25, fig_height)
    )

    colors = plt.rcParams[
        "axes.prop_cycle"
    ].by_key()["color"]

    category_handles = []

    # ===================================
    # Draw bars
    # ===================================

    for run_index, run_type in enumerate(
        ["Agent", "Baseline"]
    ):

        offset = (
            -height / 2
            if run_type == "Agent"
            else height / 2
        )

        lefts = np.zeros(len(groups))

        for category_index, category in enumerate(
            ERROR_CATEGORIES
        ):

            values = []

            for group in groups:

                match = grouped[
                    (
                        grouped[group_column]
                        == group
                    )
                    & (
                        grouped["Agent/Baseline"]
                        == run_type
                    )
                ]

                if match.empty:
                    values.append(0)
                else:
                    values.append(
                        match[category].iloc[0]
                    )

            values = np.array(values)

            ax.barh(
                y + offset,
                values,
                height,
                left=lefts,
                color=colors[
                    category_index
                    % len(colors)
                ],
                edgecolor="black",
                linewidth=0.8,
                hatch=(
                    ""
                    if run_type == "Agent"
                    else "//"
                ),
            )

            # One legend handle per category
            if run_index == 0:
                category_handles.append(
                    Patch(
                        facecolor=colors[
                            category_index
                            % len(colors)
                        ],
                        edgecolor="black",
                        label=category,
                    )
                )

            lefts += values

    # ===================================
    # Title
    # ===================================

    ax.set_title(
        title,
        fontsize=34,
        pad=22,
    )

    # ===================================
    # Axis labels
    # ===================================

    ax.set_xlabel(
        "Number of errors",
        fontsize=30,
        labelpad=15,
    )

    ax.set_ylabel(
        ylabel,
        fontsize=30,
        labelpad=15,
    )

    # ===================================
    # Y labels
    # ===================================

    ax.set_yticks(y)

    if label_map is not None:
        display_labels = [
            wrap_label(
                label_map.get(group, group),
                width=16,
            )
            for group in groups
        ]
    else:
        display_labels = [
            wrap_label(group, width=16)
            for group in groups
        ]

    ax.set_yticklabels(
        display_labels,
        fontsize=24,
    )

    # ===================================
    # X axis
    # ===================================

    ax.tick_params(
        axis="x",
        labelsize=24,
    )

    # ===================================
    # Grid
    # ===================================

    ax.grid(
        axis="x",
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    # First model/language at top
    ax.invert_yaxis()

    # ===================================
    # TYPE LEGEND
    # ===================================

    run_handles = [
        Patch(
            facecolor="white",
            edgecolor="black",
            linewidth=1.2,
            label="Agent",
        ),
        Patch(
            facecolor="white",
            edgecolor="black",
            linewidth=1.2,
            hatch="//",
            label="Baseline",
        ),
    ]

    # ===================================
    # ERROR CATEGORY LEGEND
    # ===================================

    category_legend = fig.legend(
        handles=category_handles,
        title="Error category",
        loc="upper left",
        bbox_to_anchor=(0.7, 0.88),
        fontsize=20,
        title_fontsize=22,
        frameon=True,
        labelspacing=1.0,
        handlelength=2.2,
        handletextpad=0.8,
        borderpad=1.0,
    )

    # ===================================
    # TYPE LEGEND
    # ===================================

    type_legend = fig.legend(
        handles=run_handles,
        title="Type",
        loc="upper left",
        bbox_to_anchor=(0.7, 0.64),
        fontsize=20,
        title_fontsize=22,
        frameon=True,
        labelspacing=1.0,
        handlelength=2.2,
        handletextpad=0.8,
        borderpad=1.0,
    )

    # ===================================
    # Figure spacing
    # ===================================

    # Only use about 70% of the figure for
    # the plot. The remaining 30% is reserved
    # for the legends.
    fig.subplots_adjust(
        left=0.20,
        right=0.70,
        top=0.92,
        bottom=0.10,
    )

    # ===================================
    # Save
    # ===================================

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.4,
    )

    plt.close()

    print(f"Saved: {output_file}")


def main():

    if len(sys.argv) < 2:
        print(
            "Usage: "
            "python create_error_plots_horizontal.py "
            "<category_counts_iteration_4.xlsx>"
        )
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(
            f"File not found: {input_file}"
        )
        sys.exit(1)

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

    # Ensure numeric error counts
    for category in ERROR_CATEGORIES:

        df[category] = pd.to_numeric(
            df[category],
            errors="coerce",
        ).fillna(0)

    output_folder = input_file.parent

    # ===================================
    # Plot 1: Language
    # ===================================

    create_stacked_plot(
        df=df,
        group_column="Language",
        output_file=(
            output_folder
            / "errors_by_language_horizontal.png"
        ),
        title=(
            "Error Categories by Language: "
            "Agent vs Baseline"
        ),
        ylabel="Language",
    )

    # ===================================
    # Plot 2: Model
    # ===================================

    create_stacked_plot(
        df=df,
        group_column="Model",
        output_file=(
            output_folder
            / "errors_by_model_horizontal.png"
        ),
        title=(
            "Error Categories by Model"
        ),
        ylabel="Model",
        label_map=NEW_LABELS,
    )


if __name__ == "__main__":
    main()