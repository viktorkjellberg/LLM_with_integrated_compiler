import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


HASKELL_ERROR_PATTERNS = [
    (r"parse error", "parse_error"),
    (r"parse error on input", "parse_error_on_input"),
    (r"lexical error", "lexical_error"),
    (r"not in scope", "not_in_scope"),
    (r"variable not in scope", "variable_not_in_scope"),
    (r"data constructor not in scope", "constructor_not_in_scope"),
    (r"type constructor or class not in scope", "type_constructor_not_in_scope"),
    (r"could not find module", "module_not_found"),
    (r"could not load module", "module_load_error"),
    (r"ambiguous occurrence", "ambiguous_occurrence"),
    (r"duplicate type signatures for", "duplicate_type_signatures"),
    (r"multiple declarations of", "multiple_declarations"),
    (r"conflicting definitions for", "conflicting_definitions"),
    (r"couldn't match expected type", "type_mismatch"),
    (r"could not deduce", "typeclass_deduction_failed"),
    (r"no instance for", "missing_typeclass_instance"),
    (r"occurs check", "infinite_type"),
    (r"equations for .* have different numbers of arguments", "arity_mismatch"),
    (r"the function .* is applied to too few arguments", "too_few_arguments"),
    (r"the function .* is applied to too many arguments", "too_many_arguments"),
    (r"non-exhaustive patterns", "non_exhaustive_patterns"),
    (r"pattern match(es)? are non-exhaustive", "non_exhaustive_patterns"),
    (r"illegal type signature", "illegal_type_signature"),
    (r"illegal instance declaration", "illegal_instance_declaration"),
    (r"illegal declaration of", "illegal_declaration"),
    (r"kind mismatch", "kind_mismatch"),
    (r"main is not defined", "main_not_defined"),
]


ERROR_TYPE_TO_CATEGORY = {
    "parse_error": "syntax_error",
    "parse_error_on_input": "syntax_error",
    "lexical_error": "syntax_error",
    "not_in_scope": "name_resolution",
    "variable_not_in_scope": "name_resolution",
    "constructor_not_in_scope": "name_resolution",
    "type_constructor_not_in_scope": "name_resolution",
    "module_not_found": "module_error",
    "module_load_error": "module_error",
    "ambiguous_occurrence": "name_resolution",
    "duplicate_type_signatures": "declaration_error",
    "multiple_declarations": "declaration_error",
    "conflicting_definitions": "declaration_error",
    "type_mismatch": "type_error",
    "typeclass_deduction_failed": "typeclass_error",
    "missing_typeclass_instance": "typeclass_error",
    "infinite_type": "type_error",
    "arity_mismatch": "function_definition_error",
    "too_few_arguments": "function_call_error",
    "too_many_arguments": "function_call_error",
    "non_exhaustive_patterns": "pattern_match_error",
    "illegal_type_signature": "declaration_error",
    "illegal_instance_declaration": "declaration_error",
    "illegal_declaration": "declaration_error",
    "kind_mismatch": "kind_error",
    "main_not_defined": "program_structure",
    "unknown_haskell_error": "other",
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

    # Haskell/GHC often includes “error:” lines
    match = re.search(r"error:\s*(.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    # Fallback for compilation wrapper text
    match = re.search(r"compilation error:\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_whitespace(match.group(1))

    # Fallback: first meaningful line
    first_line = text.splitlines()[0] if text.splitlines() else text
    return normalize_whitespace(first_line)


def classify_haskell_error(error_text: Optional[str]) -> Optional[str]:
    if not error_text:
        return None

    text = error_text.lower()

    for pattern, label in HASKELL_ERROR_PATTERNS:
        if re.search(pattern, text):
            return label

    return "unknown_haskell_error"


def get_category(error_type: Optional[str], compile_result: str) -> str:
    if error_type is None:
        if "compilation successful" in str(compile_result).lower():
            return "no_error"
        return "unknown"

    return ERROR_TYPE_TO_CATEGORY.get(error_type, "other")


def extract_haskell_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "haskell":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_text = extract_error_text(compile_result)
        error_type = classify_haskell_error(error_text)
        category = get_category(error_type, compile_result)

        enriched = dict(item)
        enriched["source_file"] = source_file
        enriched["compiler_error_text"] = error_text
        enriched["compiler_error_type"] = error_type
        enriched["category"] = category
        enriched["has_compilation_error"] = error_type is not None

        results.append(enriched)

    return results


def combine_haskell_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            haskell_records = extract_haskell_records(data, file_path.name)

            if haskell_records:
                combined.extend(haskell_records)
                print(f"Processed {file_path.name}: {len(haskell_records)} Haskell records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total Haskell records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_haskell_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_haskell_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()