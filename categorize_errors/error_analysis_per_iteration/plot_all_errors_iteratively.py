import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

file_path = "category_counts_by_iteration.csv"
df = pd.read_csv(file_path)

# Error categories in stacking order
error_cols = [
    "Syntax",
    "Semantic",
    "Dependency",
    "Type mismatch",
    "Language specific",
    "Other"
]

# Directory for generated figures
output_dir = Path("stacked_area_plots")
output_dir.mkdir(exist_ok=True)


# --------------------------------------------------
# 2. Create one figure per language
# --------------------------------------------------

for language in df["Language"].unique():

    # Select rows belonging to the current language
    lang_data = df[df["Language"] == language].copy()

    # Calculate the largest total number of errors.
    # This ensures that Baseline and Agent use the same y-axis.
    totals = lang_data[error_cols].sum(axis=1)
    y_max = totals.max() * 1.08

    # Create two plots:
    # Baseline = left
    # Agent = right
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(16, 6),
        sharex=True,
        sharey=True
    )


    # --------------------------------------------------
    # 3. Plot Baseline and Agent
    # --------------------------------------------------

    for ax, run_type in zip(axes, ["baseline", "agent"]):

        # Select data
        data = lang_data[
            lang_data["Type"].str.lower() == run_type
        ].sort_values("Iteration")

        # X-axis
        x = data["Iteration"].to_numpy()

        # Values for each error category
        y_values = [
            data[column].to_numpy()
            for column in error_cols
        ]

        # Create stacked area chart
        ax.stackplot(
            x,
            *y_values,
            labels=error_cols,
            alpha=0.85
        )

        # Plot formatting
        ax.set_title(
            run_type.capitalize(),
            fontsize=16
        )

        ax.set_xlabel("Iteration",
                      fontsize=16)

        # Same y-axis for Agent and Baseline
        ax.set_ylim(0, y_max)

        # Ensure iterations appear as integers
        ticks = sorted(data["Iteration"].unique())

        ax.set_xticks(ticks)
        ax.set_xticklabels(
            [i + 1 for i in ticks],
            fontsize=16
)

        # Grid
        ax.grid(
            True,
            alpha=0.2
        )


    # --------------------------------------------------
    # 4. Y-axis
    # --------------------------------------------------

    axes[0].set_ylabel(
        "Total number of errors",
        fontsize=16
    )


    # --------------------------------------------------
    # 5. Main title
    # --------------------------------------------------

    fig.suptitle(
        f"{language}: Error Composition by Iteration",
        fontsize=20,
        #y=0.92
    )


    # --------------------------------------------------
    # 6. Horizontal legend underneath title
    # --------------------------------------------------

    handles, labels = axes[0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.93),
        ncol=6,
        fontsize=14,
        frameon=True
    )


    # --------------------------------------------------
    # 7. Layout
    # --------------------------------------------------

    # Leave space at the top for the title and legend
    fig.tight_layout(
        rect=[0, 0, 1, 0.92]
    )


    # --------------------------------------------------
    # 8. Save figure
    # --------------------------------------------------

    safe_language = (
        language
        .lower()
        .replace(" ", "_")
    )

    output_file = (
        output_dir /
        f"{safe_language}_baseline_agent_stacked_area.png"
    )

    fig.savefig(
        output_file,
        dpi=180,
        bbox_inches="tight"
    )


    # --------------------------------------------------
    # 9. Display figure
    # --------------------------------------------------

    #plt.show()

    # Free memory before creating the next figure
    #plt.close(fig)