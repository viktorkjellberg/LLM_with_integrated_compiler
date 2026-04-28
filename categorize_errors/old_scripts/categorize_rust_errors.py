import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


RUST_ERROR_PATTERNS = [
    (r"cannot find (?:value|function|type|struct|enum|trait|module) .* in this scope", "not_found_in_scope"),
    (r"use of undeclared crate or module", "undeclared_crate_or_module"),
    (r"failed to resolve", "failed_to_resolve"),
    (r"mismatched types", "mismatched_types"),
    (r"expected .* found .*", "type_mismatch"),
    (r"borrow of moved value", "borrow_of_moved_value"),
    (r"cannot move out of", "move_out_of_borrowed"),
    (r"cannot borrow .* as mutable", "mutable_borrow_error"),
    (r"cannot borrow .* as immutable because it is also borrowed as mutable", "borrow_conflict"),
    (r"cannot assign to .* because it is borrowed", "assign_while_borrowed"),
    (r"borrowed value does not live long enough", "lifetime_too_short"),
    (r"missing lifetime specifier", "missing_lifetime_specifier"),
    (r"doesn't implement", "missing_trait_impl"),
    (r"the trait bound .* is not satisfied", "trait_bound_not_satisfied"),
    (r"no method named .* found for", "method_not_found"),
    (r"this function takes \d+ argument[s]? but \d+ argument[s]? were supplied", "wrong_argument_count"),
    (r"unexpected closing delimiter", "unexpected_closing_delimiter"),
    (r"unclosed delimiter", "unclosed_delimiter"),
    (r"expected one of .* found .*", "expected_token"),
    (r"expected identifier", "expected_identifier"),
    (r"match arms have incompatible types", "match_arm_type_mismatch"),
    (r"cannot return value referencing", "returning_reference_to_local"),
    (r"temporary value dropped while borrowed", "temporary_dropped_while_borrowed"),
    (r"recursion limit reached", "recursion_limit_reached"),
    (r"main function not found", "main_not_found"),
    (r"multiple applicable items in scope", "ambiguous_method_resolution"),
    (r"aborting due to .* previous error", "compile_aborted"),
]


ERROR_TYPE_TO_CATEGORY = {
    "not_found_in_scope": "name_resolution",
    "undeclared_crate_or_module": "name_resolution",
    "failed_to_resolve": "name_resolution",
    "mismatched_types": "type_error",
    "type_mismatch": "type_error",
    "match_arm_type_mismatch": "type_error",
    "missing_trait_impl": "trait_error",
    "trait_bound_not_satisfied": "trait_error",
    "method_not_found": "trait_error",
    "ambiguous_method_resolution": "trait_error",
    "borrow_of_moved_value": "ownership_error",
    "move_out_of_borrowed": "ownership_error",
    "mutable_borrow_error": "borrow_checker_error",
    "borrow_conflict": "borrow_checker_error",
    "assign_while_borrowed": "borrow_checker_error",
    "lifetime_too_short": "lifetime_error",
    "missing_lifetime_specifier": "lifetime_error",
    "returning_reference_to_local": "lifetime_error",
    "temporary_dropped_while_borrowed": "lifetime_error",
    "wrong_argument_count": "function_call_error",
    "expected_token": "syntax_error",
    "expected_identifier": "syntax_error",
    "unexpected_closing_delimiter": "syntax_error",
    "unclosed_delimiter": "syntax_error",
    "recursion_limit_reached": "compile_limit_error",
    "main_not_found": "program_structure",
    "compile_aborted": "other",
    "unknown_rust_error": "other",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_error_text(compile_result: str) -> Optional[str]:
    if not compile_result:
        return None

    text = compile_result.strip()
    lower = text.lower()

    if "compilation successful" in lower:
        return None

    # Try standard Rust "error:" line first
    match = re.search(r"error(?:\[[A-Z0-9]+\])?:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    # Fallback for general compilation error wrapper
    match = re.search(r"compilation error:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    return normalize_whitespace(text)


def classify_rust_error(error_text: Optional[str]) -> Optional[str]:
    if not error_text:
        return None

    text = error_text.lower()

    for pattern, label in RUST_ERROR_PATTERNS:
        if re.search(pattern, text):
            return label

    return "unknown_rust_error"


def get_category(error_type: Optional[str], compile_result: str) -> str:
    if error_type is None:
        if "compilation successful" in str(compile_result).lower():
            return "no_error"
        return "unknown"

    return ERROR_TYPE_TO_CATEGORY.get(error_type, "other")


def extract_rust_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "rust":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_text = extract_error_text(compile_result)
        error_type = classify_rust_error(error_text)
        category = get_category(error_type, compile_result)

        enriched = dict(item)
        enriched["source_file"] = source_file
        enriched["compiler_error_text"] = error_text
        enriched["compiler_error_type"] = error_type
        enriched["category"] = category
        enriched["has_compilation_error"] = error_type is not None

        results.append(enriched)

    return results


def combine_rust_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            rust_records = extract_rust_records(data, file_path.name)

            if rust_records:
                combined.extend(rust_records)
                print(f"Processed {file_path.name}: {len(rust_records)} Rust records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total Rust records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_rust_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_rust_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()