import json
from pathlib import Path
from collections import defaultdict


def order_primary_errors(input_folder, output_file):
    """
    Reads all JSON files in a folder and combines their data.

    Groups by:
        Task_Name, Language, Model, Type

    Each group contains:
        iteration -> {
            "primary_category": ...,
            "primary_error_text": ...
        }

    Type is determined by filename:
        *agent.json    -> agents
        *baseline.json -> baseline
    """

    input_folder = Path(input_folder)
    output_file = Path(output_file)

    if not input_folder.is_dir():
        raise ValueError(f"Input folder does not exist: {input_folder}")

    grouped = defaultdict(dict)

    json_files = sorted(input_folder.glob("*.json"))

    # Prevent reading the output file
    json_files = [
        f for f in json_files
        if f.resolve() != output_file.resolve()
    ]

    for file in json_files:

        filename = file.name.lower()

        # Determine type from filename
        if filename.endswith("baseline.json"):
            experiment_type = "baseline"
        elif filename.endswith("agent.json"):
            experiment_type = "agent"
        else:
            print(f"Skipping file with unknown type: {file.name}")
            continue

        print(f"Processing: {file.name} ({experiment_type})")

        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for row in data:

            task_name = row.get("Task_Name")
            language = row.get("Language")
            model = row.get("Model")
            iteration = row.get("Iteration")

            if iteration is None:
                continue

            key = (
                task_name,
                language,
                model,
                experiment_type
            )

            grouped[key][int(iteration)] = {
                "primary_category": row.get("primary_category"),
                "Compile_Result": row.get("Compile_Result")
            }

    # Create final result
    result = []

    for (task_name, language, model, experiment_type), iterations in sorted(
        grouped.items()
    ):

        ordered_iterations = {
            str(iteration): iterations[iteration]
            for iteration in sorted(iterations)
        }

        result.append({
            "Task_Name": task_name,
            "Language": language,
            "Model": model,
            "Type": experiment_type,
            "iterations": ordered_iterations
        })

    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save combined JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\nProcessing completed!")
    print(f"Files found: {len(json_files)}")
    print(f"Unique task combinations: {len(result)}")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":

    order_primary_errors(
        input_folder="new_files",
        output_file="combined_ordered_errors.json"
    )