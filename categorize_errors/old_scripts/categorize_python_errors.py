import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


PYTHON_ERROR_PATTERNS = [
    (r"syntaxerror", "syntax_error"),
    (r"indentationerror", "indentation_error"),
    (r"taberror", "tab_error"),
    (r"nameerror", "name_error"),
    (r"typeerror", "type_error"),
    (r"valueerror", "value_error"),
    (r"attributeerror", "attribute_error"),
    (r"importerror", "import_error"),
    (r"modulenotfounderror", "module_not_found"),
    (r"indexerror", "index_error"),
    (r"keyerror", "key_error"),
    (r"zerodivisionerror", "zero_division"),
    (r"overflowerror", "overflow_error"),
    (r"recursionerror", "recursion_error"),
    (r"unboundlocalerror", "unbound_local"),
    (r"filenotfounderror", "file_not_found"),
    (r"assertionerror", "assertion_error"),
    (r"memoryerror", "memory_error"),
    (r"eoferror", "eof_error"),
    (r"runtimeerror", "runtime_error"),
    (r"permissionerror", "permission_error"),
    (r"oserror", "os_error"),
]


ERROR_TYPE_TO_CATEGORY = {
    "syntax_error": "syntax_error",
    "indentation_error": "syntax_error",
    "tab_error": "syntax_error",
    "name_error": "name_resolution",
    "unbound_local": "name_resolution",
    "import_error": "import_resolution",
    "module_not_found": "import_resolution",
    "type_error": "type_error",
    "value_error": "value_error",
    "attribute_error": "attribute_error",
    "index_error": "container_error",
    "key_error": "container_error",
    "zero_division": "math_error",
    "overflow_error": "math_error",
    "recursion_error": "runtime_error",
    "runtime_error": "runtime_error",
    "memory_error": "runtime_error",
    "eof_error": "input_error",
    "file_not_found": "file_or_io_error",
    "permission_error": "file_or_io_error",
    "os_error": "file_or_io_error",
    "assertion_error": "assertion_failure",
    "unknown_python_error": "other",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_error_text(compile_result: str) -> Optional[str]:
    """
    Extract the main error text from a Python compile/runtime message.
    """
    if not compile_result:
        return None

    text = compile_result.strip()
    lower = text.lower()

    if "compilation successful" in lower:
        return None

    # Try to find a standard Python exception/error name and its message
    match = re.search(
        r"([A-Za-z_][A-Za-z0-9_]*Error)\s*:\s*(.*?)(?:\n|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return normalize_whitespace(f"{match.group(1)}: {match.group(2)}")

    # Fallback: extract first line containing "error"
    match = re.search(r"^.*error.*$", text, re.IGNORECASE | re.MULTILINE)
    if match:
        return normalize_whitespace(match.group(0))

    return normalize_whitespace(text)


def classify_python_error(error_text: Optional[str]) -> Optional[str]:
    if not error_text:
        return None

    text = error_text.lower()

    for pattern, label in PYTHON_ERROR_PATTERNS:
        if re.search(pattern, text):
            return label

    return "unknown_python_error"


def get_category(error_type: Optional[str], compile_result: str) -> str:
    if error_type is None:
        if "compilation successful" in str(compile_result).lower():
            return "no_error"
        return "unknown"

    return ERROR_TYPE_TO_CATEGORY.get(error_type, "other")


def extract_python_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "python":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_text = extract_error_text(compile_result)
        error_type = classify_python_error(error_text)
        category = get_category(error_type, compile_result)

        enriched = dict(item)
        enriched["source_file"] = source_file
        enriched["compiler_error_text"] = error_text
        enriched["compiler_error_type"] = error_type
        enriched["category"] = category
        enriched["has_compilation_error"] = error_type is not None

        results.append(enriched)

    return results


def combine_python_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            python_records = extract_python_records(data, file_path.name)

            if python_records:
                combined.extend(python_records)
                print(f"Processed {file_path.name}: {len(python_records)} Python records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total Python records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_python_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_python_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()
