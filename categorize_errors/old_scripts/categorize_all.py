#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

LANGUAGE_KEYS = ("Language", "language")
COMPILE_RESULT_KEYS = ("Compile_Result", "Compile_result", "compile_result", "compileResult")

CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    (
        "missing_symbol_or_import",
        [
            r"cannot find symbol",
            r"package .* does not exist",
            r"symbol:\s+class ",
            r"symbol:\s+variable ",
            r"symbol:\s+method ",
            r"not in scope",
            r"undefined reference to",
            r"undeclared",
            r"cannot find value .* in this scope",
            r"cannot find function .* in this scope",
            r"cannot find type .* in this scope",
            r"no such file or directory",
            r"can't find crate",
            r"unbound variable",
            r"unbound module",
            r"unresolved import",
            r"use of undeclared (identifier|label|crate|type)",
        ],
    ),
    (
        "syntax_error",
        [
            r"';' expected",
            r"'\)' expected",
            r"'\]' expected",
            r"'\}' expected",
            r"not a statement",
            r"illegal start of (expression|type)",
            r"class, interface, enum, or record expected",
            r"reached end of file while parsing",
            r"unclosed (string literal|character literal)",
            r"identifier expected",
            r"parse error",
            r"syntax error",
            r"expected one of",
            r'missing "then"',
            r'missing "is"',
            r'missing "return"',
            r"declaration expected",
            r"statement expected",
            r"unexpected token",
            r"unexpected .*, expected",
            r"encountered diff marker",
            r"version control conflict marker in file",
            r'reserved word .* cannot be used as identifier',
            r'missing "begin"',
            r"end .* expected",
            r"binary operator expected",
        ],
    ),
    (
        "type_mismatch",
        [
            r"incompatible types",
            r"bad operand types for binary operator",
            r"no suitable method found",
            r"no suitable constructor found",
            r"actual and formal argument lists differ in length",
            r"cannot be converted to",
            r"mismatched types",
            r"type mismatch",
            r"expected .* found",
            r"couldn't match expected type",
            r"doesn't implement",
            r"cannot infer type",
            r"anonymous array definition not allowed here",
            r"the trait bound .* is not satisfied",
            r"ambiguous type variable",
        ],
    ),
    (
        "missing_method_or_wrong_api_usage",
        [
            r"cannot find symbol\s+.*symbol:\s+method",
            r"method .* cannot be applied to given types",
            r"no suitable method found",
            r"no function or associated item named",
            r"not a function",
            r"no instance for",
            r"has no field",
            r"is not a member of",
            r"has no attribute",
            r"unrecognized attribute",
        ],
    ),
    (
        "class_name_file_name_mismatch",
        [
            r"is public, should be declared in a file named",
            r'keyword "body" expected here \[see file name\]',
        ],
    ),
    (
        "control_flow_error",
        [
            r"break outside switch or loop",
            r"continue outside of loop",
            r"return outside method",
            r"main function not found",
        ],
    ),
    (
        "illegal_character_or_encoding",
        [
            r"illegal character",
            r"unmappable character",
            r"illegal unicode escape",
            r"invalid character",
        ],
    ),
    (
        "assignment_or_mutability_error",
        [
            r"cannot assign a value to final variable",
            r"cannot assign a value to static final variable",
            r"auto-closeable resource .* may not be assigned",
            r"cannot borrow .* as mutable",
            r"cannot assign twice to immutable variable",
        ],
    ),
    (
        "preview_or_language_feature_issue",
        [
            r"preview feature",
            r"use --enable-preview",
            r"feature .* is incomplete",
            r"requires .* edition",
        ],
    ),
    (
        "other_compile_error",
        [],
    ),
]

COMPILED_OK_PATTERNS = [
    re.compile(r"^\s*Compilation successful\s*$", re.I),
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_records(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return [x for x in data["data"] if isinstance(x, dict)]
        return [data]
    raise ValueError("Unsupported JSON structure. Expected a JSON object or array.")


def get_language(record: Dict[str, Any]) -> str:
    for key in LANGUAGE_KEYS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def get_compile_result(record: Dict[str, Any]) -> str:
    for key in COMPILE_RESULT_KEYS:
        value = record.get(key)
        if isinstance(value, str):
            return value
    return ""


def is_compile_success(text: str) -> bool:
    return any(p.match(text) for p in COMPILED_OK_PATTERNS)


def extract_error_lines(text: str) -> List[str]:
    return [line.rstrip() for line in text.splitlines() if "error" in line.lower()]


def extract_error_messages(text: str) -> List[str]:
    messages: List[str] = []
    for line in text.splitlines():
        if "error" not in line.lower():
            continue
        if re.search(r"\berror:\s*", line, flags=re.I):
            parts = re.split(r"\berror:\s*", line, maxsplit=1, flags=re.I)
            messages.append(parts[1].strip())
        elif re.search(r"\berror\[[A-Z]\d+\]:", line, flags=re.I):
            messages.append(line.strip())
        elif re.search(r"\berror\b", line, flags=re.I):
            messages.append(line.strip())
    return messages


def categorize_error(text: str) -> List[str]:
    lowered = text.lower()
    categories: List[str] = []
    for category, patterns in CATEGORY_RULES:
        if not patterns:
            continue
        for pattern in patterns:
            if re.search(pattern, lowered, flags=re.I | re.S):
                categories.append(category)
                break
    return categories or ["other_compile_error"]


def summarize_primary_error(text: str) -> str:
    messages = extract_error_messages(text)
    if messages:
        return messages[0]
    lines = extract_error_lines(text)
    if lines:
        return lines[0].strip()
    return text.strip().splitlines()[0].strip() if text.strip() else ""


def analyze_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    record_list = list(records) if not isinstance(records, list) else records
    details: List[Dict[str, Any]] = []
    category_counts: Counter = Counter()
    diagnostic_category_counts: Counter = Counter()
    task_counts: Counter = Counter()

    for idx, record in enumerate(record_list):
        compile_result = get_compile_result(record)
        if not compile_result or is_compile_success(compile_result):
            continue

        task_name = record.get("Task_Name", f"record_{idx}")
        language = get_language(record)
        task_counts[task_name] += 1

        error_messages = extract_error_messages(compile_result)
        categorized_errors: List[Dict[str, Any]] = []
        aggregated_categories: List[str] = []

        if error_messages:
            for message in error_messages:
                cats = categorize_error(message)
                categorized_errors.append({"message": message, "categories": cats})
                for cat in cats:
                    diagnostic_category_counts[cat] += 1
                    aggregated_categories.append(cat)
        else:
            cats = categorize_error(compile_result)
            categorized_errors.append({"message": summarize_primary_error(compile_result), "categories": cats})
            for cat in cats:
                diagnostic_category_counts[cat] += 1
                aggregated_categories.append(cat)

        unique_categories = sorted(set(aggregated_categories))
        for cat in unique_categories:
            category_counts[cat] += 1

        details.append(
            {
                "task_name": task_name,
                "language": language,
                "model": record.get("Model"),
                "categories": unique_categories,
                "primary_error": summarize_primary_error(compile_result),
                "error_lines": extract_error_lines(compile_result),
                "categorized_errors": categorized_errors,
                "compile_result": compile_result,
            }
        )

    return {
        "total_records": len(record_list),
        "compile_error_records": len(details),
        "category_counts": dict(category_counts.most_common()),
        "diagnostic_category_counts": dict(diagnostic_category_counts.most_common()),
        "details": details,
        "task_counts": dict(task_counts.most_common()),
    }


def merge_counts(left: Dict[str, int], right: Dict[str, int]) -> Dict[str, int]:
    counter = Counter(left)
    counter.update(right)
    return dict(counter.most_common())


def analyze_file(path: Path) -> Dict[str, Any]:
    data = load_json(path)
    records = normalize_records(data)
    result = analyze_records(records)
    language = get_language(records[0]) if records else "unknown"
    result["language"] = language
    result["file"] = str(path)
    return result


def analyze_directory(input_dir: Path) -> Dict[str, Any]:
    files = sorted(p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() == ".json")
    aggregated: Dict[str, Dict[str, Any]] = {}

    for path in files:
        result = analyze_file(path)
        language = result["language"]
        bucket = aggregated.setdefault(
            language,
            {
                "language": language,
                "files": [],
                "total_records": 0,
                "compile_error_records": 0,
                "category_counts": {},
                "diagnostic_category_counts": {},
                "task_counts": {},
                "details": [],
            },
        )
        bucket["files"].append(result["file"])
        bucket["total_records"] += result["total_records"]
        bucket["compile_error_records"] += result["compile_error_records"]
        bucket["category_counts"] = merge_counts(bucket["category_counts"], result["category_counts"])
        bucket["diagnostic_category_counts"] = merge_counts(
            bucket["diagnostic_category_counts"], result["diagnostic_category_counts"]
        )
        bucket["task_counts"] = merge_counts(bucket["task_counts"], result["task_counts"])
        bucket["details"].extend(result["details"])

    return {
        "input_dir": str(input_dir),
        "file_count": len(files),
        "languages": dict(sorted(aggregated.items(), key=lambda item: item[0].lower())),
    }


def print_summary(result: Dict[str, Any], top_n: int = 10) -> None:
    print(f"Input dir: {result['input_dir']}")
    print(f"Files scanned: {result['file_count']}")
    print("\nBy language:")
    for language, info in result["languages"].items():
        print(f"- {language}: {info['compile_error_records']} compile-error records across {len(info['files'])} file(s)")
        for category, count in list(info["diagnostic_category_counts"].items())[:top_n]:
            print(f"    {category}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract and categorize compiler errors from all JSON files in a directory."
    )
    parser.add_argument("input", help="Path to input directory")
    parser.add_argument("-o", "--output", required=True, help="Path to write aggregated analysis as JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_dir():
        raise ValueError(f"Expected a directory, got: {input_path}")

    result = analyze_directory(input_path)
    print_summary(result)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote analysis to: {output_path}")


if __name__ == "__main__":
    main()
