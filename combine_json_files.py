import json
import re
from pathlib import Path
from collections import defaultdict


INPUT_DIR = Path("eval_json")
OUTPUT_DIR = Path("eval_json_model")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """
    Replace special characters so the filename is safe on most systems.
    Example:
        gemma3:12b -> gemma3_12b
        deepseek-r1:7b -> deepseek-r1_7b
    """
    name = re.sub(r"[^\w.-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("._")


def extract_model_from_filename(filename: str) -> str | None:
    """
    Expected pattern:
        <Language>_<Model>_agents_evaluation.json

    Examples:
        Haskell_gemma3:12b_agents_evaluation.json
        Java_deepseek-r1:7b_agents_evaluation.json
    """
    suffix = "_agents_evaluation.json"
    if not filename.endswith(suffix):
        return None

    base = filename[:-len(suffix)]

    if "_" not in base:
        return None

    # Split only on the first underscore:
    # Haskell_gemma3:12b -> language=Haskell, model=gemma3:12b
    _, model = base.split("_", 1)
    return model


def load_json_file(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def combine_by_model(input_dir: Path, output_dir: Path):
    grouped = defaultdict(list)

    json_files = list(input_dir.glob("*_agents_evaluation.json"))

    if not json_files:
        print(f"No matching files found in {input_dir}")
        return

    for json_file in json_files:
        model = extract_model_from_filename(json_file.name)
        if model is None:
            print(f"Skipping unrecognized filename: {json_file.name}")
            continue

        try:
            data = load_json_file(json_file)
        except Exception as e:
            print(f"Failed to read {json_file.name}: {e}")
            continue

        # If the file contains a list, extend it.
        # If it contains a single dict/object, append it.
        if isinstance(data, list):
            grouped[model].extend(data)
        else:
            grouped[model].append(data)

        print(f"Loaded {json_file.name} -> model={model}")

    for model, records in grouped.items():
        safe_model = sanitize_filename(model)
        output_file = output_dir / f"{safe_model}_agents_evaluation.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        print(f"Wrote {len(records)} records -> {output_file}")


if __name__ == "__main__":
    combine_by_model(INPUT_DIR, OUTPUT_DIR)