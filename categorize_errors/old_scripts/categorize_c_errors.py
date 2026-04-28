import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


C_ERROR_PATTERNS = [
    (r"undeclared\b", "undeclared_identifier"),
    (r"implicit declaration of function", "implicit_function_declaration"),
    (r"conflicting types for", "conflicting_types"),
    (r"incompatible types", "incompatible_types"),
    (r"incompatible pointer type", "incompatible_pointer_type"),
    (r"assignment to .* from incompatible pointer type", "incompatible_pointer_assignment"),
    (r"too few arguments to function", "too_few_arguments"),
    (r"too many arguments to function", "too_many_arguments"),
    (r"expected ['\"].*['\"] before", "expected_token"),
    (r"expected declaration specifiers", "expected_declaration_specifiers"),
    (r"expected expression", "expected_expression"),
    (r"expected ';'", "missing_semicolon"),
    (r"expected ','", "missing_comma"),
    (r"expected '\)'", "missing_right_parenthesis"),
    (r"expected '\('", "missing_left_parenthesis"),
    (r"expected '\}'", "missing_right_brace"),
    (r"stray '\\\\[0-9]+' in program", "stray_character"),
    (r"stray .+ in program", "stray_character"),
    (r"missing terminating ['\"] character", "unterminated_literal"),
    (r"missing terminating ['\"] string", "unterminated_literal"),
    (r"invalid use of void expression", "invalid_void_use"),
    (r"called object is not a function", "called_non_function"),
    (r"subscripted value is neither array nor pointer", "invalid_subscript"),
    (r"lvalue required", "lvalue_required"),
    (r"redefinition of", "redefinition"),
    (r"multiple definition of", "multiple_definition"),
    (r"no such file or directory", "missing_include_or_file"),
    (r"fatal error:", "fatal_error"),
    (r"warning: control reaches end of non-void function", "missing_return_statement"),
    (r"segmentation fault", "segmentation_fault"),
]


ERROR_TYPE_TO_CATEGORY = {
    "undeclared_identifier": "name_resolution",
    "implicit_function_declaration": "name_resolution",
    "missing_include_or_file": "build_or_include",
    "fatal_error": "build_or_include",
    "conflicting_types": "type_error",
    "incompatible_types": "type_error",
    "incompatible_pointer_type": "pointer_type_error",
    "incompatible_pointer_assignment": "pointer_type_error",
    "too_few_arguments": "function_call_error",
    "too_many_arguments": "function_call_error",
    "expected_token": "syntax_error",
    "expected_declaration_specifiers": "syntax_error",
    "expected_expression": "syntax_error",
    "missing_semicolon": "syntax_error",
    "missing_comma": "syntax_error",
    "missing_right_parenthesis": "syntax_error",
    "missing_left_parenthesis": "syntax_error",
    "missing_right_brace": "syntax_error",
    "stray_character": "syntax_error",
    "unterminated_literal": "syntax_error",
    "invalid_void_use": "type_error",
    "called_non_function": "type_error",
    "invalid_subscript": "type_error",
    "lvalue_required": "assignment_error",
    "redefinition": "declaration_error",
    "multiple_definition": "linker_error",
    "missing_return_statement": "function_structure",
    "segmentation_fault": "runtime_error",
    "unknown_compiler_error": "other",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_all_error_texts(compile_result: str) -> List[str]:
    """
    Extract every c 'error: ...' message from the full compile output.

    Example input:
        main.c:3: error: cannot find symbol
        main.c:4: error: ';' expected
    Output:
        ['cannot find symbol', "';' expected"]
    """
    if not compile_result:
        return []

    lower = compile_result.lower()
    if 'compilation successful' in lower:
        return []

    matches = re.findall(r'error:\s*(.*?)(?:\n|$)', compile_result, re.IGNORECASE)
    # Normalize and filter out noise-only lines (e.g. a single caret '^' or other
    # punctuation-only markers) which are sometimes present in javac output.
    error_texts_raw = [normalize_whitespace(m) for m in matches if normalize_whitespace(m)]
    # Keep only messages that contain at least one alphanumeric character. This
    # preserves legitimate short messages like "';' expected" (which include
    # the word "expected") while removing marker lines like '^'.
    error_texts = [e for e in error_texts_raw if re.search(r'[A-Za-z0-9]', e)]

    if error_texts:
        return error_texts

    # Fallback: if compilation failed but no explicit "error:" lines were found
    match = re.search(r'compilation error:\s*(.*)', compile_result, re.IGNORECASE | re.DOTALL)
    if match:
        text = normalize_whitespace(match.group(1))
        if text and re.search(r'[A-Za-z0-9]', text):
            return [text]
        return []

    text = normalize_whitespace(compile_result)
    if text and re.search(r'[A-Za-z0-9]', text):
        return [text]
    return []


def classify_c_error(error_text: str) -> str:
    text = error_text.lower()

    for pattern, label in C_ERROR_PATTERNS:
        if re.search(pattern, text):
            return label

    return 'unknown_compiler_error'


def get_category(error_type: str) -> str:
    return ERROR_TYPE_TO_CATEGORY.get(error_type, 'other')


def unique_preserve_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_c_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "c":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_texts = extract_all_error_texts(compile_result)

        if not error_texts:
            error_types: List[str] = []
            categories: List[str] = []
            primary_error_type: Optional[str] = None
            primary_category = "no_error" if "compilation successful" in compile_result.lower() else "unknown"
        else:
            error_types = [classify_c_error(text) for text in error_texts]
            error_types = unique_preserve_order(error_types)
            categories = unique_preserve_order([get_category(error_type) for error_type in error_types])
            primary_error_type = error_types[0]
            primary_category = categories[0] if categories else "other"

        enriched = dict(item)
        enriched["source_file"] = source_file
        enriched["compiler_error_texts"] = error_texts
        enriched["compiler_error_types"] = error_types
        enriched["categories"] = categories
        enriched["primary_compiler_error_type"] = primary_error_type
        enriched["primary_category"] = primary_category
        enriched["has_compilation_error"] = len(error_texts) > 0

        results.append(enriched)

    return results


def combine_c_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            c_records = extract_c_records(data, file_path.name)

            if c_records:
                combined.extend(c_records)
                print(f"Processed {file_path.name}: {len(c_records)} C records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total C records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_c_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_c_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()