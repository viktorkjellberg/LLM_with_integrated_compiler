#!/usr/bin/env python3

import re
import json
import math
import argparse
from pathlib import Path

import pandas as pd


def normalize_text(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace(":", "_")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def clean_value(value):
    if pd.isna(value):
        return None
    return value


def build_xlsx_index(xlsx_dir):
    """
    Index all xlsx files under xlsx_dir recursively.

    Expected structure:
      xlsx_dir/
        <model_name>/
          ...xlsx
    """
    index = []
    for path in Path(xlsx_dir).rglob("*.xlsx"):
        parent_model = path.parent.name
        index.append(
            {
                "path": path,
                "filename_norm": normalize_text(path.stem),
                "model_dir_norm": normalize_text(parent_model),
            }
        )
    return index


def find_matching_xlsx(task_name, language, model, xlsx_index):
    """
    Find the best XLSX for a task.

    Strategy:
    1. Only consider xlsx files inside the folder matching the model name.
    2. Prefer filename containing language + model + task_name.
    3. Then prefer filename containing task_name.
    """
    norm_task = normalize_text(task_name)
    norm_lang = normalize_text(language)
    norm_model = normalize_text(model)

    filtered = [x for x in xlsx_index if x["model_dir_norm"] == norm_model]

    if not filtered:
        return None

    strong_key = "-".join(part for part in [norm_lang, norm_model, norm_task] if part)

    for item in filtered:
        if strong_key and strong_key in item["filename_norm"]:
            return item["path"]

    task_matches = [x["path"] for x in filtered if norm_task and norm_task in x["filename_norm"]]
    if len(task_matches) == 1:
        return task_matches[0]

    if len(task_matches) > 1:
        # Prefer one that also contains language
        lang_matches = [
            x["path"] for x in filtered
            if norm_task in x["filename_norm"] and norm_lang in x["filename_norm"]
        ]
        if len(lang_matches) == 1:
            return lang_matches[0]

        return task_matches[0]

    return None


def parse_iterations_from_xlsx(xlsx_path):
    """
    Parse iteration xlsx into:

    [
      {
        "0": {
          "Generated_code": ...,
          "Markdown_Code": ...,
          "Compile_Result": ...
        },
        "1": {...}
      }
    ]

    Expected XLSX columns:
      - attempt
      - content
      - clean_code
      - compile_result
    """
    if xlsx_path is None or not xlsx_path.exists():
        return []

    try:
        df = pd.read_excel(xlsx_path)
    except Exception as e:
        print(f"Warning: failed to read {xlsx_path}: {e}")
        return []

    required = {"attempt", "content", "clean_code", "compile_result"}
    missing = required - set(df.columns)
    if missing:
        print(f"Warning: {xlsx_path} missing columns: {sorted(missing)}")
        return []

    attempts_map = {}

    for _, row in df.iterrows():
        attempt = row.get("attempt")
        if pd.isna(attempt):
            continue

        try:
            attempt_key = str(int(attempt))
        except Exception:
            attempt_key = str(attempt)

        attempts_map[attempt_key] = {
            "Generated_code": clean_value(row.get("content")),
            "Markdown_Code": clean_value(row.get("clean_code")),
            "Compile_Result": clean_value(row.get("compile_result")),
        }

    if not attempts_map:
        return []

    return [attempts_map]


def process_csv_file(csv_path, xlsx_index):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Warning: failed to read {csv_path}: {e}")
        return []

    results = []

    for _, row in df.iterrows():
        item = {
            "Task_Name": clean_value(row.get("Task_Name")),
            "Language": clean_value(row.get("Language")),
            "Model": clean_value(row.get("Model")),
            "Task_Description": clean_value(row.get("Task_Description")),
            "Generated_code": clean_value(row.get("Generated_code")),
            "Markdown_Code": clean_value(row.get("Markdown_Code")),
            "Compile_Result": clean_value(row.get("Compile_Result")),
            "Test_Result": clean_value(row.get("Test_Result")),
            "Test_Data": clean_value(row.get("Test_Data")),
        }

        try:
            iteration_count = int(row.get("Iteration", 0)) if not pd.isna(row.get("Iteration", 0)) else 0
        except Exception:
            iteration_count = 0

        if iteration_count > 0:
            xlsx_path = find_matching_xlsx(
                task_name=row.get("Task_Name"),
                language=row.get("Language"),
                model=row.get("Model"),
                xlsx_index=xlsx_index,
            )

            item["Iterations_Data"] = parse_iterations_from_xlsx(xlsx_path)

            if xlsx_path is None:
                print(
                    f"Warning: no XLSX found for "
                    f"Task_Name='{row.get('Task_Name')}', "
                    f"Language='{row.get('Language')}', "
                    f"Model='{row.get('Model')}'"
                )

        results.append(item)

    return results


def combine_to_json(csv_dir, xlsx_dir, output_json):
    csv_dir = Path(csv_dir)
    xlsx_dir = Path(xlsx_dir)
    output_json = Path(output_json)

    if not csv_dir.is_dir():
        raise ValueError(f"CSV directory does not exist: {csv_dir}")

    if not xlsx_dir.is_dir():
        raise ValueError(f"XLSX directory does not exist: {xlsx_dir}")

    csv_files = sorted(csv_dir.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in {csv_dir}")

    xlsx_index = build_xlsx_index(xlsx_dir)

    all_results = []
    for csv_file in csv_files:
        print(f"Processing {csv_file.name}")
        all_results.extend(process_csv_file(csv_file, xlsx_index))

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(all_results)} records to {output_json}")


def main():
    parser = argparse.ArgumentParser(
        description="Combine CSV files and nested XLSX iteration files into one JSON file."
    )
    parser.add_argument("csv_dir", help="Directory containing CSV files")
    parser.add_argument("xlsx_dir", help="Root directory containing model subdirectories with XLSX files")
    parser.add_argument("-o", "--output", default="combined.json", help="Output JSON path")

    args = parser.parse_args()
    combine_to_json(args.csv_dir, args.xlsx_dir, args.output)


if __name__ == "__main__":
    main()