#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import get_error_lib

def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def load_json_file(file_path: Path) -> Any:
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(file_path: Path, data: Any) -> None:
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


"""
def extract_all_error_texts(compile_result: str) -> List[str]:
    if not compile_result:
        return []

    lower = compile_result.lower()
    if 'compilation successful' in lower:
        return []

    matches = re.findall(r'error:\s*(.*?)(?:\n|$)', compile_result, re.IGNORECASE)
    error_texts_raw = [normalize_whitespace(m) for m in matches if normalize_whitespace(m)]
    error_texts = [e for e in error_texts_raw if re.search(r'[A-Za-z0-9]', e)]

    if error_texts:
        return error_texts

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
"""


def classify_error(error_text: str, error_patterns) -> str:
    text = error_text.lower()

    for e_p in error_patterns:
        pattern = e_p["pattern"].lower()
        label = e_p["label"].lower()

        if re.search(rf'{pattern}', text):
            return label

    return 'unknown_compiler_error'


def get_category(error_type: str, error_types_of_categoires) -> str:
    return error_types_of_categoires.get(error_type, 'Other')


def unique_preserve_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def is_item(item: Dict[str, Any], language: str) -> bool:
    return str(item.get("Language", "")).strip().lower() == language


def create_category_list(error_types: List[str], error_types_of_categoires) -> List[str]:
    categories = []

    for error_type in error_types:
        category = get_category(error_type, error_types_of_categoires)

        if category != "" and category != None:
            categories.append(category)

    return categories

def enrich_with_error_categories(item: Dict[str, Any], error_patterns, error_types_of_categoires) -> Dict[str, Any]:
    compile_result = str(item.get("Compile_Result", ""))

    error_texts = get_error_lib.extract_all_error_texts(compile_result)

    if not error_texts:
        error_types: List[str] = []
        categories: List[str] = []
        primary_error_type: Optional[str] = None
        primary_category = "no_error" if "compilation successful" in compile_result.lower() else "unknown"
        primary_error_text: Optional[str] = None
    else:
        error_types = [classify_error(text, error_patterns) for text in error_texts]
        #error_types = unique_preserve_order(error_types)
        error_types = error_types  # Keep the order of error types as they appear
        categories_list = create_category_list(error_types, error_types_of_categoires)
        categories = categories_list
        #categories = unique_preserve_order(categories_list)
        #categories = unique_preserve_order([get_category(error_type, error_types_of_categoires) for error_type in error_types])
        primary_error_type = error_types[0]
        primary_category = categories[0] if categories else "Other"
        primary_error_text = get_error_lib.extract_first_error(compile_result)

    enriched = dict(item)
    enriched["compiler_error_texts"] = error_texts
    enriched["compiler_error_types"] = error_types
    enriched["categories"] = categories
    enriched["primary_compiler_error_type"] = primary_error_type
    enriched["primary_category"] = primary_category
    enriched["primary_error_text"] = primary_error_text
    enriched["has_compilation_error"] = len(error_texts) > 0

    return enriched


def flatten_iterations(data: Any, source_file_name: str, language: str, error_patterns, error_types_of_categoires) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list")

    flattened: List[Dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        if not is_item(item, language):
            continue

        iterations_data = item.get("Iterations_Data")
        if not isinstance(iterations_data, list):
            continue

        for iteration_group in iterations_data:
            if not isinstance(iteration_group, dict):
                continue

            for iteration_index, iteration_content in iteration_group.items():
                if not isinstance(iteration_content, dict):
                    continue

                output_item = dict(item)
                output_item.pop("Iterations_Data", None)

                output_item["Generated_code"] = iteration_content.get("Generated_code")
                output_item["Markdown_Code"] = iteration_content.get("Markdown_Code")
                output_item["Compile_Result"] = iteration_content.get("Compile_Result")

                try:
                    output_item["Iteration"] = int(iteration_index)
                except Exception:
                    output_item["Iteration"] = iteration_index

                if "source_file" not in output_item:
                    output_item["source_file"] = source_file_name

                output_item = enrich_with_error_categories(output_item, error_patterns, error_types_of_categoires)
                flattened.append(output_item)

    return flattened


def load_error_classification_config(language: str):
    error_category = Path(f"settings_errors_types/{language}/error_categories.json")
    error_patterns = Path(f"settings_errors_types/{language}/error_patterns.json")
    with error_category.open("r", encoding="utf-8") as f:
        category_data = json.load(f)
    with error_patterns.open("r", encoding="utf-8") as f:
        patterns_data = json.load(f)
    
    return patterns_data, category_data


def count_unknown_compiler_errors_in_types(output_file: str) -> int:
    from pathlib import Path
    import json

    file_path = Path(output_file)

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Output JSON must be a list")

    count = 0

    for item in data:
        if not isinstance(item, dict):
            continue

        compiler_error_types = item.get("compiler_error_types", [])
        if not isinstance(compiler_error_types, list):
            continue

        count += sum(
            1
            for error_type in compiler_error_types
            if error_type == "unknown_compiler_error"
        )

    return count


def main() -> None:


    base_dir ="category_error"

    if len(sys.argv) != 3:
        types = ["a", "b"]
        language = ["ada", "c", "java", "haskell", "rust"]

        #print("Usage: python3 flatten_and_categorize_iterations.py <language> <agent/baseline (a/b)>")
        #ys.exit(1)

        for t in types:
            if t == "a":
                a_or_b = "agent"
            else:
                a_or_b = "baseline"
            for lang in language:
                run_flatten_and_categorize(lang, a_or_b, base_dir)        

    else:
        if sys.argv[2] not in ("a", "b"):
            print("Error: second argument must be 'a' or 'b'")
            sys.exit(1)

        if sys.argv[2] == "a":
            a_or_b = "agent"
        else:
            a_or_b = "baseline"

        run_flatten_and_categorize(sys.argv[1], a_or_b, base_dir)

    
def run_flatten_and_categorize(language: str, a_or_b: str, base_dir: str) -> None:

    input_file = Path(f"../summarize_results/combined_{a_or_b}.json")

    output_file = Path(f"{base_dir}/{language}_{a_or_b}.json")

    error_patterns, error_types_of_categoires = load_error_classification_config(language)

    if not input_file.exists() or not input_file.is_file():
        print(f"Error: {input_file} is not a valid file")
        sys.exit(1)

    data = load_json_file(input_file)
    flattened = flatten_iterations(data, input_file.name, language, error_patterns, error_types_of_categoires)
    save_json_file(output_file, flattened)
    print(f"Saved {len(flattened)} flattened iteration items to {output_file}")
    unknown_errors = count_unknown_compiler_errors_in_types(output_file)
    print(f"Count of unknown compiler errors: {unknown_errors}")


if __name__ == "__main__":
    main()