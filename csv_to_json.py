
import csv
import json
import sys
from pathlib import Path


def increase_csv_field_limit():
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = max_int // 10


def clean_value(value):
    if value in ("", "NaN", "nan", None):
        return None
    return value


def csv_to_json(input_path: Path, output_path: Path):
    rows = []

    with input_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: clean_value(v) for k, v in row.items()})

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def convert_directory(input_dir, output_dir=None, recursive=False):
    increase_csv_field_limit()

    input_dir = Path(input_dir)

    if output_dir is None:
        output_dir = input_dir
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    pattern = "**/*.csv" if recursive else "*.csv"
    csv_files = list(input_dir.glob(pattern))

    if not csv_files:
        print(f"No CSV files found in: {input_dir}")
        return

    for csv_file in csv_files:
        if output_dir == input_dir:
            json_file = csv_file.with_suffix(".json")
        else:
            relative_path = csv_file.relative_to(input_dir).with_suffix(".json")
            json_file = output_dir / relative_path
            json_file.parent.mkdir(parents=True, exist_ok=True)

        csv_to_json(csv_file, json_file)
        print(f"Converted: {csv_file} -> {json_file}")



if __name__ == "__main__":
    convert_directory(
        input_dir="eval",
        output_dir="eval_json",   # or None to save next to CSVs
        recursive=False                       # True to include subfolders
    )