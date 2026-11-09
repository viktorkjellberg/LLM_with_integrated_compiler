import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd


CATEGORY_ORDER = [
    "Syntax",
    "Semantic",
    "Dependency",
    "Type mismatch",
    "Language specific",
    "Other",
]


def get_run_type(filename):
    """
    Determine whether the file is Agent or Baseline
    from its filename.
    """
    name = filename.lower()

    if "_agent" in name:
        return "Agent"
    elif "_baseline" in name:
        return "Baseline"
    else:
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python count_categories.py <folder_path> [output.xlsx]")
        sys.exit(1)

    folder = Path(sys.argv[1])

    if not folder.is_dir():
        print(f"Error: {folder} is not a valid folder.")
        sys.exit(1)

    # Default output location
    output_file = (
        Path(sys.argv[2])
        if len(sys.argv) >= 3
        else "folder" / "category_counts_iteration_4.xlsx"
    )

    # Key:
    # (Language, Model, Agent/Baseline) -> Counter
    grouped_counts = defaultdict(Counter)

    json_files = sorted(folder.glob("*.json"))

    if not json_files:
        print("No JSON files found.")
        sys.exit(1)

    for json_file in json_files:

        run_type = get_run_type(json_file.name)

        # Ignore files that are neither _agent nor _baseline
        if run_type is None:
            print(f"Skipping: {json_file.name} (not agent/baseline)")
            continue

        print(f"Processing: {json_file.name}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            print(f"  Error reading file: {e}")
            continue

        for item in data:

            # Only Iteration 4
            if item.get("Iteration") != 4:
                continue

            language = item.get("Language", "Unknown")
            model = item.get("Model", "Unknown")

            categories = [item.get("primary_category")]

            # Protect against null categories
            if not categories:
                categories = []

            key = (language, model, run_type)

            grouped_counts[key].update(categories)

    # ---------------------------------------
    # Build output table
    # ---------------------------------------

    rows = []

    for (language, model, run_type), counts in sorted(grouped_counts.items()):

        row = {
            "Language": language,
            "Model": model,
            "Agent/Baseline": run_type,
        }

        for category in CATEGORY_ORDER:
            row[category] = counts[category]

        row["Total"] = sum(counts.values())

        rows.append(row)

    columns = [
        "Language",
        "Model",
        "Agent/Baseline",
        *CATEGORY_ORDER,
        "Total",
    ]

    df = pd.DataFrame(rows, columns=columns)

    # Save to Excel
    df.to_excel(output_file, index=False)

    print()
    print(f"Done. Results saved to:")
    print(output_file)

    print()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()