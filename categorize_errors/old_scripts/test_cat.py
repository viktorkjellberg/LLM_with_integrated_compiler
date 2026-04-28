import json
import csv
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any


CATEGORY_RULES = [
    ("compilation_successful", [
        r"\bCompilation successful\b",
    ]),

    ("cannot_find_symbol", [
        r"error:\s*cannot find symbol",
        r"\bsymbol:\s+class\b",
        r"\bsymbol:\s+method\b",
        r"\bsymbol:\s+variable\b",
    ]),

    ("missing_import", [
        r"location:\s*package\s+java\.[\w.]+",
        r"error:\s*cannot find symbol.*\bMap\b",
        r"error:\s*cannot find symbol.*\bHashMap\b",
        r"error:\s*cannot find symbol.*\bArrays\b",
        r"error:\s*cannot find symbol.*\bIOException\b",
        r"error:\s*cannot find symbol.*\bInputStream\b",
        r"error:\s*cannot find symbol.*\bFunction\b",
    ]),

    ("syntax_error", [
        r"error:\s*';'\s*expected",
        r"error:\s*'\)'\s*expected",
        r"error:\s*'\('\s*expected",
        r"error:\s*not a statement",
        r"error:\s*illegal start of expression",
        r"error:\s*reached end of file while parsing",
        r"error:\s*class,\s*interface,\s*enum,\s*or\s*record\s*expected",
        r"error:\s*unclosed character literal",
        r"error:\s*unclosed string literal",
    ]),

    ("type_mismatch", [
        r"error:\s*incompatible types",
        r"error:\s*bad operand types for binary operator",
        r"cannot be converted to",
    ]),

    ("method_not_found", [
        r"symbol:\s+method\s+\w+",
    ]),

    ("variable_not_found", [
        r"symbol:\s+variable\s+\w+",
    ]),

    ("class_not_found", [
        r"symbol:\s+class\s+\w+",
    ]),

    ("public_class_filename_mismatch", [
        r"error:\s*class\s+\w+\s+is public,\s+should be declared in a file named",
    ]),

    ("illegal_character", [
        r"error:\s*illegal character",
    ]),

    ("preview_feature_required", [
        r"preview feature",
        r"use --enable-preview to enable",
    ]),

    ("package_or_import_error", [
        r"error:\s*package\s+.+\s+does not exist",
        r"location:\s*package\s+",
    ]),
]


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    return str(text).replace("\r\n", "\n").strip()


def categorize_compile_result(compile_result: str) -> List[str]:
    text = normalize_text(compile_result)
    categories = set()

    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL):
                categories.add(category)
                break

    if "Compilation successful" not in text:
        categories.add("has_compilation_error")

    if re.search(r"\b\d+\s+errors?\b", text, flags=re.IGNORECASE):
        categories.add("multiple_compiler_messages")

    if "error:" in text.lower() and len(categories) == 1 and "has_compilation_error" in categories:
        categories.add("uncategorized_compiler_error")

    if "compilation_successful" in categories:
        categories.discard("has_compilation_error")
        categories.discard("multiple_compiler_messages")
        categories.discard("uncategorized_compiler_error")

    return sorted(categories)


def load_json_array(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{path} does not contain a top-level JSON array")

    return [row for row in data if isinstance(row, dict)]


def is_java_row(row: Dict[str, Any]) -> bool:
    return str(row.get("Language", "")).strip() == "Java"


def enrich_row(row: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    result = dict(row)
    result["Source_File"] = source_file
    result["Compile_Error_Categories"] = categorize_compile_result(row.get("Compile_Result", ""))
    return result


def write_json(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "Source_File",
        "Task_Name",
        "Language",
        "Model",
        "Compile_Result",
        "Compile_Error_Categories",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "Source_File": row.get("Source_File", ""),
                "Task_Name": row.get("Task_Name", ""),
                "Language": row.get("Language", ""),
                "Model": row.get("Model", ""),
                "Compile_Result": row.get("Compile_Result", ""),
                "Compile_Error_Categories": "|".join(row.get("Compile_Error_Categories", [])),
            })


def main():
    parser = argparse.ArgumentParser(
        description="Combine JSON files, keep only Java rows, and categorize compile results."
    )
    parser.add_argument("input_dir", help="Directory containing JSON files")
    parser.add_argument(
        "--json-out",
        default="all_java_compile_results_categorized.json",
        help="Output JSON file name"
    )
    parser.add_argument(
        "--csv-out",
        default="all_java_compile_results_categorized.csv",
        help="Output CSV file name"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f"Input directory does not exist or is not a directory: {input_dir}")

    json_files = sorted(input_dir.glob("*.json"))
    if not json_files:
        raise SystemExit(f"No JSON files found in {input_dir}")

    all_java_rows: List[Dict[str, Any]] = []
    total_rows = 0

    for json_file in json_files:
        try:
            rows = load_json_array(json_file)
            total_rows += len(rows)

            java_rows = [enrich_row(row, json_file.name) for row in rows if is_java_row(row)]
            all_java_rows.extend(java_rows)

            print(f"[OK] {json_file.name}: total={len(rows)} java={len(java_rows)}")
        except Exception as e:
            print(f"[ERROR] {json_file.name}: {e}")

    json_out_path = input_dir / args.json_out
    csv_out_path = input_dir / args.csv_out

    write_json(json_out_path, all_java_rows)
    write_csv(csv_out_path, all_java_rows)

    print(f"\nDone.")
    print(f"Total rows seen: {total_rows}")
    print(f"Total Java rows kept: {len(all_java_rows)}")
    print(f"JSON output: {json_out_path}")
    print(f"CSV output:  {csv_out_path}")


if __name__ == "__main__":
    main()