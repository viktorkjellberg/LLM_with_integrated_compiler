import json
import pandas as pd
import argparse
from pathlib import Path


ITERATION_PAIRS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
]

LANGUAGE_ORDER = [
    "Python",
    "Java",
    "C",
    "Rust",
    "Haskell",
    "Ada",
]


def calculate_error_survival(input_json):
    """
    Calculate error survival between consecutive iterations.

    Survival:
        1 = value remains the same
        0 = value changes

    Compares:
        - primary_category
        - Compile_Result (exact text)

    Outputs:
        1. error_survival_detailed.csv
        2. error_survival_summary.csv
    """

    input_json = Path(input_json)


    # Read JSON
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    # Process each task/model/language/type combination
    for item in data:

        language = item.get("Language")
        task = item.get("Task_Name")
        model = item.get("Model")
        type_ = item.get("Type")

        iterations = item.get("iterations", {})

        for current_iter, next_iter in ITERATION_PAIRS:

            current_key = str(current_iter)
            next_key = str(next_iter)

            # Skip if either iteration does not exist
            if (
                current_key not in iterations
                or next_key not in iterations
            ):
                continue

            current = iterations[current_key]
            next_ = iterations[next_key]

            current_category = current.get("primary_category")
            next_category = next_.get("primary_category")

            current_compile = current.get("Compile_Result")
            next_compile = next_.get("Compile_Result")

            # Compare primary category
            category_survived = int(
                current_category == next_category
            )

            # Compare exact compiler result
            compile_survived = int(
                current_compile == next_compile
            )

            rows.append({
                "Language": language,
                "Task_Name": task,
                "Model": model,
                "Type": type_,
                "Iteration_Pair": f"{current_iter}->{next_iter}",

                "Category_From": current_category,
                "Category_To": next_category,
                "Category_Survived": category_survived,

                "Compile_Result_From": current_compile,
                "Compile_Result_To": next_compile,
                "Compile_Result_Survived": compile_survived,
            })

    # Create detailed dataframe
    detailed_df = pd.DataFrame(rows)

    if detailed_df.empty:
        print("No valid iteration pairs found.")
        return

    # Sort detailed results
    detailed_df["Language"] = pd.Categorical(
        detailed_df["Language"],
        categories=LANGUAGE_ORDER,
        ordered=True
    )

    detailed_df = detailed_df.sort_values(
        by=[
            "Language",
            "Type",
            "Model",
            "Task_Name",
            "Iteration_Pair",
        ]
    )

    # Save detailed results
    detailed_path = "error_survival_detailed.csv"

    detailed_df.to_csv(
        detailed_path,
        index=False
    )

    print(f"Saved detailed results: {detailed_path}")

    # ---------------------------------------
    # Calculate summary survival rates
    # ---------------------------------------

    summary_df = (
        detailed_df.groupby(
            [
                "Language",
                "Type",
                "Iteration_Pair",
            ],
            observed=True
        )
        .agg(
            Category_Survival_Rate=(
                "Category_Survived",
                "mean"
            ),
            Compile_Result_Survival_Rate=(
                "Compile_Result_Survived",
                "mean"
            ),
            N=(
                "Category_Survived",
                "size"
            ),
        )
        .reset_index()
    )

    # Convert rates to percentages
    summary_df["Category_Survival_Rate"] *= 100
    summary_df["Compile_Result_Survival_Rate"] *= 100

    # Round percentages
    summary_df[
        [
            "Category_Survival_Rate",
            "Compile_Result_Survival_Rate",
        ]
    ] = summary_df[
        [
            "Category_Survival_Rate",
            "Compile_Result_Survival_Rate",
        ]
    ].round(2)

    # Sort summary
    summary_df = summary_df.sort_values(
        by=[
            "Language",
            "Type",
            "Iteration_Pair",
        ]
    )

    # Save summary
    summary_path = "error_survival_summary.csv"

    summary_df.to_csv(
        summary_path,
        index=False
    )

    print(f"Saved summary results: {summary_path}")

    # Display summary
    print("\nError Survival Summary:")
    print(summary_df.to_string(index=False))

    return detailed_df, summary_df


if __name__ == "__main__":

    input_json = "combined_ordered_errors.json"

    calculate_error_survival(
        input_json
    )