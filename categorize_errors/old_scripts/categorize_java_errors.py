import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


JAVA_ERROR_PATTERNS = [
    (r'cannot find symbol', 'cannot_find_symbol'),
    (r'incompatible types', 'incompatible_types'),
    (r'class, interface, enum, or record expected', 'declaration_expected'),
    (r'interface expected here', 'interface_expected_here'),
    (r'illegal start of expression', 'illegal_start_of_expression'),
    (r'illegal start of type', 'illegal_start_of_type'),
    (r'not a statement', 'not_a_statement'),
    (r'invalid method declaration; return type required', 'missing_return_type'),
    (r'missing return statement', 'missing_return_statement'),
    (r'return outside method', 'return_outside_method'),
    (r'unclosed string literal', 'unclosed_string_literal'),
    (r'unclosed character literal', 'unclosed_character_literal'),
    (r'reached end of file while parsing', 'unexpected_eof_while_parsing'),
    (r';\s*expected', 'missing_semicolon'),
    (r'\)\s*expected', 'missing_right_parenthesis'),
    (r'\(\s*expected', 'missing_left_parenthesis'),
    (r'}\s*expected', 'missing_right_brace'),
    (r"'\{'\s*expected", 'missing_left_brace'),
    (r"'\]'\s*expected|\]\s*expected", 'missing_right_bracket'),
    (r"'\)'\s*expected", 'missing_right_parenthesis'),
    (r'duplicate class', 'duplicate_class'),
    (r'already defined', 'duplicate_definition'),
    (r'package .* does not exist', 'package_does_not_exist'),
    (r'cannot access ', 'cannot_access_symbol'),
    (r'non-static variable .* cannot be referenced from a static context',
     'non_static_reference_from_static_context'),
    (r'method .* cannot be applied to given types', 'method_argument_mismatch'),
    (r'constructor .* cannot be applied to given types', 'constructor_argument_mismatch'),
    (r'possible lossy conversion from .* to .*', 'possible_lossy_conversion'),
    (r'variable .* might not have been initialized', 'variable_might_not_have_been_initialized'),
    (r'unreported exception .* must be caught or declared to be thrown',
     'unreported_exception'),
    (r'exception .* is never thrown in body of corresponding try statement',
     'exception_never_thrown'),
    (r'error: no suitable method found for', 'no_suitable_method_found'),
    (r'error: file not found', 'file_not_found'),
    (r'error: error reading', 'cannot_read_file'),
    (r'no code found', 'no_code_found'),
    (r'illegal character:', 'illegal_character'),
    (r"'\;'\s*expected", 'missing_semicolon'),
    (r'unnamed classes are a preview feature and are disabled by default.', 'using_unnamed_class'),
    (r'.* error: <identifier> expected', 'missing_identifier'),
    (r'<identifier> expected', 'missing_identifier'),
    (r'.* error: cannot infer type arguments for', 'cannot_infer_type_arguments'),
    (r'.* error: \) expected', 'missing_right_parenthesis'),
    (r'error: class .* is public, should be declared in a file named .*\.java', 'public_class_file_mismatch'),
    (r'.* error: bad operand types for binary operator', 'bad_operand_types'),
    (r'bad operand types for binary operator', 'bad_operand_types'),    
    (r'.* error: bad operand type .* for unary operator', 'bad_operand_types'),
    (r'.* error: bad initializer for for-loop', 'bad_initializer_for_for_loop'),
    (r'bad initializer for for-loop', 'bad_initializer_for_for_loop'),
    (r'method does not override or implement a method from a supertype', 'method_not_found'),
    (r"'catch' without 'try'", 'catch_without_try'),
    (r'no suitable constructor found for', 'no_suitable_constructor_found'),
    (r'.*= expected', 'missing_equals_in_annotation'),
    (r'.* error: \'\.class\' expected', 'missing_class_literal'),
    (r'.* error: \) or \, expected', 'missing_right_parenthesis'),
    (r".* error: '\)'' expected", 'missing_right_parenthesis'),
    (r'.*cannot find symbol', 'cannot_find_symbol'),
    (r'break outside switch or loop', 'break_outside_switch_or_loop'),
    (r".* error: '\)' or '\,' expected", 'missing_right_parenthesis'),
    (r'no suitable method found for', 'no_suitable_method_found'),
    (r'.* error: illegal escape characters', 'illegal_character'),
    (r'non-static method .* cannot be referenced from a static context', 'non_static_reference_from_static_context'),
    (r'illegal escape character', 'illegal_character'),
    (r"'\[\' expected", 'missing_left_bracket'),
    (r"'\]'\s*expected|\]\s*expected", 'missing_right_bracket'),
    (r".* error: '\.class' expected", 'missing_class_literal')
    
]


ERROR_TYPE_TO_CATEGORY = {
    'cannot_find_symbol': 'name_resolution',
    'package_does_not_exist': 'name_resolution',
    'cannot_access_symbol': 'name_resolution',
    'duplicate_class': 'declaration',
    'duplicate_definition': 'declaration',
    'declaration_expected': 'declaration',
    'interface_expected_here': 'declaration',
    'incompatible_types': 'type_error',
    'possible_lossy_conversion': 'type_error',
    'method_argument_mismatch': 'type_error',
    'constructor_argument_mismatch': 'type_error',
    'no_suitable_method_found': 'type_error',
    'missing_semicolon': 'syntax_error',
    'missing_right_parenthesis': 'syntax_error',
    'missing_left_parenthesis': 'syntax_error',
    'missing_right_brace': 'syntax_error',
    'missing_right_bracket': 'syntax_error',
    'illegal_start_of_expression': 'syntax_error',
    'illegal_start_of_type': 'syntax_error',
    'not_a_statement': 'syntax_error',
    'unclosed_string_literal': 'syntax_error',
    'unclosed_character_literal': 'syntax_error',
    'unexpected_eof_while_parsing': 'syntax_error',
    'missing_return_type': 'method_structure',
    'missing_return_statement': 'method_structure',
    'return_outside_method': 'method_structure',
    'non_static_reference_from_static_context': 'static_context',
    'variable_might_not_have_been_initialized': 'initialization',
    'unreported_exception': 'exception_handling',
    'exception_never_thrown': 'exception_handling',
    'file_not_found': 'build_or_input',
    'cannot_read_file': 'build_or_input',
    'no_code_found': 'build_or_input',
    'illegal_character': 'syntax_error',
    'unknown_compiler_error': 'other',
    'missing_semicolon': 'syntax_error',
    'using_unnamed_class': 'language_feature',
    'missing_identifier': 'syntax_error',
    'cannot_infer_type_arguments': 'type_error',
    'public_class_file_mismatch': 'declaration',
    'bad_operand_types': 'type_error',
    'method_not_found': 'type_error',
    'bad_initializer_for_for_loop': 'type_error',
    'catch_without_try': 'exception_handling',
    'no_suitable_constructor_found': 'type_error',
    'missing_equals_in_annotation': 'syntax_error',
    'missing_left_brace': 'syntax_error',
    'missing_class_literal': 'syntax_error',
    'missing_right_parenthesis': 'syntax_error',
    'break_outside_switch_or_loop': 'syntax_error'
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_all_error_texts(compile_result: str) -> List[str]:
    """
    Extract every javac 'error: ...' message from the full compile output.

    Example input:
        Main.java:3: error: cannot find symbol
        Main.java:4: error: ';' expected

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


def classify_java_error(error_text: str) -> str:
    text = error_text.lower()

    for pattern, label in JAVA_ERROR_PATTERNS:
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


def extract_java_records(data: Any, source_file: str) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if str(item.get("Language", "")).strip().lower() != "java":
            continue

        compile_result = str(item.get("Compile_Result", ""))
        error_texts = extract_all_error_texts(compile_result)

        if not error_texts:
            error_types: List[str] = []
            categories: List[str] = []
            primary_error_type: Optional[str] = None
            primary_category = "no_error" if "compilation successful" in compile_result.lower() else "unknown"
        else:
            error_types = [classify_java_error(text) for text in error_texts]
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


def combine_java_json_files(input_dir: Path, output_file: Path) -> None:
    combined: List[Dict[str, Any]] = []

    for file_path in sorted(input_dir.rglob("*.json")):
        if not file_path.is_file():
            continue

        try:
            data = load_json_file(file_path)
            java_records = extract_java_records(data, file_path.name)

            if java_records:
                combined.extend(java_records)
                print(f"Processed {file_path.name}: {len(java_records)} Java records")
        except Exception as e:
            print(f"Skipping {file_path.name}: {e}")

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(combined)} total Java records to {output_file}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python combine_java_with_categories.py <input_directory> <output_file>")
        sys.exit(1)

    input_dir = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)

    combine_java_json_files(input_dir, output_file)


if __name__ == "__main__":
    main()