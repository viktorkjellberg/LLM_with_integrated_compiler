import json
import csv
from pathlib import Path
from collections import defaultdict, Counter


def count_categories_by_iteration(input_folder, output_csv):
    input_folder = Path(input_folder)
    output_csv = Path(output_csv)

    if not input_folder.exists():
        raise FileNotFoundError(
            f"Input folder does not exist: {input_folder.resolve()}"
        )

    json_files = list(input_folder.rglob("*.json"))

    print(f"Input folder: {input_folder.resolve()}")
    print(f"Found {len(json_files)} JSON files")

    if not json_files:
        raise ValueError(
            f"No JSON files found in: {input_folder.resolve()}"
        )

    # counts[(language, type, iteration)] = Counter(...)
    counts = defaultdict(Counter)
    all_categories = set()

    total_items = 0
    total_category_entries = 0

    for json_file in json_files:
        filename = json_file.name.lower()

        if "agent" in filename:
            file_type = "agent"
        elif "baseline" in filename:
            file_type = "baseline"
        else:
            print(f"Skipping file with unknown type: {json_file.name}")
            continue

        print(f"Reading: {json_file.name} -> {file_type}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ERROR reading file: {e}")
            continue

        if not isinstance(data, list):
            print("  Skipping: JSON root is not a list")
            continue

        for item in data:
            total_items += 1

            language = item.get("Language")
            iteration = item.get("Iteration")
            categories = [item.get("primary_category")]

            if language is None or iteration is None:
                continue

            key = (language, file_type, iteration)

            # Ensure row exists even when categories is empty
            counts[key]

            if not isinstance(categories, list):
                continue

            for category in categories:
                if not category:
                    continue

                category = str(category).strip()

                counts[key][category] += 1
                all_categories.add(category)
                total_category_entries += 1

    print(f"\nTotal items read: {total_items}")
    print(f"Total category entries: {total_category_entries}")
    print(f"Rows to output: {len(counts)}")
    print(f"Categories found: {sorted(all_categories)}")

    if not counts:
        raise ValueError(
            "No valid agent/baseline data was found."
        )

    preferred_order = [
        "Syntax",
        "Semantic",
        "Dependency",
        "Type mismatch",
        "Language specific",
        "Language mismatch",
        "Other",
    ]

    ordered_categories = [
        category
        for category in preferred_order
        if category in all_categories
    ]

    remaining_categories = sorted(
        all_categories - set(ordered_categories)
    )

    ordered_categories += remaining_categories

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_csv,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            ["Language", "Type", "Iteration"]
            + ordered_categories
        )

        for language, file_type, iteration in sorted(
            counts.keys(),
            key=lambda x: (x[0], x[1], x[2])
        ):
            writer.writerow(
                [
                    language,
                    file_type,
                    iteration,
                    *[
                        counts[
                            (language, file_type, iteration)
                        ][category]
                        for category in ordered_categories
                    ]
                ]
            )

    print(f"\nSaved to: {output_csv.resolve()}")


if __name__ == "__main__":
    count_categories_by_iteration(
        input_folder="new_files",
        output_csv="category_counts_by_iteration.csv"
    )