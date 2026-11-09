import json
from pathlib import Path


def remove_iterations_after_success(input_json, output_folder):
    input_path = Path(input_json)
    output_folder = Path(output_folder)

    # Create output folder if it does not exist
    output_folder.mkdir(parents=True, exist_ok=True)

    # Read JSON
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Keep track of Task_Name + Model combinations
    # that have already compiled successfully
    successful = set()

    filtered_data = []

    for item in data:
        key = (
            item.get("Task_Name"),
            item.get("Model")
        )

        # Skip everything after the first successful compilation
        if key in successful:
            continue

        # Keep current item
        filtered_data.append(item)

        # Mark this task/model as finished after success
        if item.get("Compile_Result") == "Compilation successful":
            successful.add(key)

    # Save using the same filename
    output_path = output_folder / input_path.name

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            filtered_data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Original items: {len(data)}")
    print(f"Filtered items: {len(filtered_data)}")
    print(f"Removed items: {len(data) - len(filtered_data)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":

    for input_json in ["ada_baseline.json", "ada_agent.json", 
                       "rust_baseline.json", "rust_agent.json",
                       "haskell_baseline.json", "haskell_agent.json",
                       "java_baseline.json", "java_agent.json",
                       "c_baseline.json", "c_agent.json"]:
        
        remove_iterations_after_success(
            input_json=f"../category_error/{input_json}",
            output_folder="new_files"
        )
