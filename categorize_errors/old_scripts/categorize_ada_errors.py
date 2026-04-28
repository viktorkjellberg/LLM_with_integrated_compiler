import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


ADA_ERROR_PATTERNS = [
    (r'".*" is undefined', "undefined_symbol"),
    (r'undefined', "undefined_symbol"),
    (r'file ".*" not found', "file_not_found"),
    (r'cannot find', "file_not_found"),
    (r'expected .* found .*', "unexpected_token"),
    (r'missing ";"', "missing_semicolon"),
    (r'missing "end"', "missing_end"),
    (r'missing "\)"', "missing_right_parenthesis"),
    (r'missing "\("', "missing_left_parenthesis"),
    (r'missing "then"', "missing_then"),
    (r'missing "loop"', "missing_loop"),
    (r'missing "begin"', "missing_begin"),
    (r'identifier expected', "identifier_expected"),
    (r'statement expected', "statement_expected"),
    (r'declarations must come before "begin"', "declaration_order_error"),
    (r'compilation unit expected', "compilation_unit_expected"),
    (r'type mismatch', "type_mismatch"),
    (r'expected type .* found type .*', "type_mismatch"),
    (r'invalid operand types', "invalid_operand_types"),
    (r'incorrect constraint for this kind of type', "invalid_constraint"),
    (r'too many arguments', "too_many_arguments"),
    (r'too few arguments', "too_few_arguments"),
    (r'no candidate interpretations match the actuals', "no_matching_overload"),
    (r'actual for .* must be a variable', "actual_must_be_variable"),
    (r'left hand of assignment must be a variable', "assignment_target_not_variable"),
    (r'subprogram .* is not visible', "not_visible"),
    (r'operator .* is not defined', "operator_not_defined"),
    (r'package .* does not allow a body', "invalid_package_body"),
    (r'end .* expected', "wrong_end_name"),
    (r'pragma .* is not recognized', "unknown_pragma"),
    (r'warning: .* will raise constraint_error', "constraint_error_warning"),
]


ERROR_TYPE_TO_CATEGORY = {
    "undefined_symbol": "name_resolution",
    "not_visible": "visibility_error",
    "file_not_found": "build_or_include",
    "unexpected_token": "syntax_error",
    "missing_semicolon": "syntax_error",
    "missing_end": "syntax_error",
    "missing_right_parenthesis": "syntax_error",
    "missing_left_parenthesis": "syntax_error",
    "missing_then": "syntax_error",
    "missing_loop": "syntax_error",
    "missing_begin": "syntax_error",
    "identifier_expected": "syntax_error",
    "statement_expected": "syntax_error",
    "declaration_order_error": "declaration_error",
    "compilation_unit_expected": "declaration_error",
    "wrong_end_name": "declaration_error",
    "invalid_package_body": "declaration_error",
    "type_mismatch": "type_error",
    "invalid_operand_types": "type_error",
    "invalid_constraint": "type_error",
    "operator_not_defined": "type_error",
    "too_many_arguments": "function_call_error",
    "too_few_arguments": "function_call_error",
    "no_matching_overload": "function_call_error",
    "actual_must_be_variable": "parameter_mode_error",
    "assignment_target_not_variable": "assignment_error",
    "unknown_pragma": "pragma_error",
    "constraint_error_warning": "runtime_warning",
    "unknown_ada_error": "other",
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

    # Common Ada/GNAT style: error: ...
    match = re.search(r"error:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    # Fallback for warning:
    match = re.search(r"warning:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace("warning: " + match.group(1))

    # Generic compilation wrapper
    match = re.search(r"compilation error:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    first_line = text
    #text.splitlines()[0] if text.splitlines() else text
    return normalize_whitespace(first_line)


def classify_ada_error(error_text: Optional[str]) -> Optional[str]:
    if not error_text:
        return None

    text = error_text.lower()

    for pattern, label in ADA_ERROR_PATTERNS:
        if re.search(pattern, text):
            return label

    return "unknown_ada_error"


def get_category(error_type: Optional[str], compile_result: str) -> str:
    if error_type is None:
        if "compilation successful" in str(compile_result).lower():
            return "no_error"
        return "unknown"

    return ERROR_TYPE_TO_CATEGORY.get(error_type, "other")


def extract_ada_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "ada":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_text = extract_error_text(compile_result)
        error_type = classify_ada_error(error_text)
        category = get_category(error_type, compile_result)

        enriched = dict(item)
        enriched["source_file"] = source_file
        enriched["compiler_error_text"] = error_text
        enriched["compiler_error_type"] = error_type
        enriched["category"] = category
        enriched["has_compilation_error"] = error_type is not None

        results.append(enriched)

    return results


def combine_ada_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            ada_records = extract_ada_records(data, file_path.name)

            if ada_records:
                combined.extend(ada_records)
                print(f"Processed {file_path.name}: {len(ada_records)} Ada records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total Ada records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_ada_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_ada_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()