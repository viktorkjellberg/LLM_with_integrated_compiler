#!/usr/bin/env python3
"""
Recursively evaluate generated code stored in spreadsheets/CSVs.

For every .xlsx/.xls/.csv file under --folder:
  * reads every row
  * selects rows where an attempts/attempt column has a value
  * extracts code from the clean_code column
  * detects the language unless --language is supplied
  * compiles the code using the same compile_code flow as the original evaluator
  * optionally runs tests when Tests/test_cases are present or --tests-file is supplied
  * writes results back into the same file in a column named compile_result

Examples:
  python run_folder_tests_eval.py --folder output_files
  python run_folder_tests_eval.py --folder output_files --language Ada
  python run_folder_tests_eval.py --folder output_files --tests-file data/all_tasks.xlsx
"""

from __future__ import annotations

import argparse
import ast
import json
import os
from random import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import random

import pandas as pd


SUPPORTED_LANGUAGES = {"Ada", "Java", "Python", "C", "Haskell", "Rust"}
LANGUAGE_TOKENS = {
    "ada": "Ada",
    "adb": "Ada",
    "ads": "Ada",
    "java": "Java",
    "python": "Python",
    "py": "Python",
    "c": "C",
    "haskell": "Haskell",
    "hs": "Haskell",
    "lhs": "Haskell",
    "rust": "Rust",
    "rs": "Rust",
}


class FolderCodeEvaluator:
    def __init__(self, temp_root: Path, timeout: int = 5) -> None:
        self.temp_root = temp_root
        self.timeout = timeout
        self.temp_root
        self.temp_dir = ""
        self.compiled_result: dict[str, dict[str, int]] = {}
        os.makedirs(self.temp_root, exist_ok=True)

    def get_code(self, code: Any) -> str:
        """Same extraction flow as the original script: extract fenced code, then remove a leading language token."""
        if pd.isna(code):
            return ""
        code = self.extract_code(str(code))
        code = self.remove_leading_language_token(code)
        if code != "":
            code = code.split("\n")
            code = "\n".join(code)
        return code

    def remove_leading_language_token(self, text: str) -> str:
        languages = {
            "c", "C", "python", "Python", "py", "PYTHON", "java", "Java", "JAVA",
            "Haskell", "haskell", "HASKELL", "hs", "lhs", "Ada", "ADA", "ada", "adb", "ads",
            "Rust", "rust", "rs"
        }
        m = re.match(r"^(\s*)([A-Za-z]+)([ \t]*\r?\n?)", text)
        if not m:
            return text
        leading_ws, first_word, _ = m.groups()
        if first_word.casefold() in {x.casefold() for x in languages}:
            return leading_ws + text[m.end():]
        return text

    def extract_code(self, markdown: str) -> str:
        try:
            pattern1 = r"```(|c|C|python|Python|py|PYTHON|java|Java|JAVA|Haskell|haskell|HASKELL|hs|lhs|Ada|ADA|ada|adb|ads|Rust|rust|rs|)(.*?)```"
            pattern2 = r"```(.*?)```"
            pattern3 = r"```(.*?)$"
            match1 = re.search(pattern1, markdown, re.DOTALL)
            match2 = re.search(pattern2, markdown, re.DOTALL)
            match3 = re.search(pattern3, markdown, re.DOTALL)
            if match1:
                return match1.group(2).strip()
            if match2:
                return match2.group(1).strip()
            if match3:
                return match3.group(1).strip()
            return markdown
        except Exception:
            pass
        return ""

    def suggest_java_filename(self, source: str, include_package_path: bool = False, sep: str = "/") -> str:
        PACKAGE_RE = re.compile(r"(?m)^\s*package\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*;")
        PUBLIC_TOP_RE = re.compile(
            r"(?m)^\s*public\s+(?:\w+\s+)*(class|interface|enum|record|@interface)\s+([A-Za-z_]\w*)\b"
        )
        ANY_TOP_RE = re.compile(
            r"(?m)^\s*(?:\w+\s+)*(class|interface|enum|record|@interface)\s+([A-Za-z_]\w*)\b"
        )
        cleaned = self._strip_comments_and_strings(source)

        def _is_top_level(idx: int) -> bool:
            pre = cleaned[:idx]
            return pre.count("{") - pre.count("}") == 0

        pkg_match = PACKAGE_RE.search(cleaned)
        pkg = pkg_match.group(1) if pkg_match else None
        name = None
        for m in PUBLIC_TOP_RE.finditer(cleaned):
            if _is_top_level(m.start()):
                name = m.group(2)
                break
        if not name:
            for m in ANY_TOP_RE.finditer(cleaned):
                if _is_top_level(m.start()):
                    name = m.group(2)
                    break
        if not name:
            name = "code_temp"
        if include_package_path and pkg:
            return f"{pkg.replace('.', sep)}{sep}{name}"
        return name

    def _strip_comments_and_strings(self, s: str) -> str:
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
        s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
        s = re.sub(r'"(?:\\.|[^"\\])*"', '""', s)
        s = re.sub(r"'(?:\\.|[^'\\])'", "''", s)
        return s

    def compile_code(self, code, language):

        code = self.get_code(code)

        temp_file_name = "code_temp"

        #temp_cod_file_path = f'temp/code_temp'
        temp_file = f'task_file.exe'

        random_string = ''.join(str(random.randint(0, 9)) for _ in range(5))

        temp_folder = f"{self.temp_dir}/{language}_{random_string}"

        os.makedirs(temp_folder, exist_ok=True)

        if code != "":
            if language == "C":
                with open(f'{temp_folder}/{temp_file_name}.c', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['gcc', '-w', f'{temp_file_name}.c', '-o', temp_file, '-lm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                exe_file_name = f"./{temp_file}"
            elif language == "C++":
                with open(f'{temp_folder}/{temp_file_name}.cpp', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['g++', '-w', f'{temp_file_name}.cpp', '-o', temp_file, '-lm'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                exe_file_name = f"./{temp_file}"
            elif language == "Java":
                suggested_file_name_java = self.suggest_java_filename(code)
                with open(f'{temp_folder}/{suggested_file_name_java}.java', 'w+') as f:
                    f.write(code)   
                result = subprocess.run(['javac', f'{suggested_file_name_java}.java'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                exe_file_name = suggested_file_name_java
                #os.remove(f'{temp_folder}/{suggested_file_name_java}.java')
            elif language == "Python":
                with open(f'{temp_folder}/{temp_file_name}.py', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['python3', '-m', 'py_compile', f'{temp_file_name}.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                exe_file_name = f'{temp_file_name}.py'
            elif language == "Ada":
                with open(f'{temp_folder}/{temp_file_name}.adb', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['gnatmake', f'{temp_file_name}.adb'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,cwd=temp_folder) 
                #print("RESULT: ", result)
                exe_file_name = f"./{temp_file_name}"
            elif language == "Rust":
                with open(f'{temp_folder}/{temp_file_name}.rs', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['rustc', f'{temp_file_name}.rs', '-o', temp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder) 
                exe_file_name = f"./{temp_file}"
            elif language == "Haskell":
                with open(f'{temp_folder}/{temp_file_name}.hs', 'w+') as f:
                    f.write(code)
                result = subprocess.run(['ghc', f'{temp_file_name}.hs', '-o', temp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=temp_folder)
                exe_file_name = f"./{temp_file}"
 
            else:
                return "Unsupported language", False, None, None


            # check if the output of the compilation contains the word "error"
            if b'error' in result.stderr:
                compile_result_msg = f"Compilation error: {result.stderr.decode()}"
                compile_result = False

            else:
                compile_result_msg = "Compilation successful"
                compile_result = True
        else:
            compile_result_msg = "No code found"
            compile_result = False   
            exe_file_name = None

        return compile_result_msg, compile_result, code, exe_file_name, temp_folder

    def compile_and_test(
        self,
        code_value: Any,
        language: str,
        task_name: Optional[str],
        tests_by_task: dict[str, Any],
        row: pd.Series,
    ) -> str:
        if language not in SUPPORTED_LANGUAGES:
            return f"Unsupported language: {language}"

        with tempfile.TemporaryDirectory(prefix="code_eval_", dir=self.temp_root) as tmp:
            self.temp_dir = tmp
            compile_result_msg, compile_result, _found_code, exe_file, temp_folder = self.compile_code(code_value, language)
            parts = [compile_result_msg]
            tests = self.get_inline_tests(row)
            if tests is None and task_name is not None:
                tests = tests_by_task.get(str(task_name))
            if tests is not None:
                test_result, test_data = self.run_tests(tests, task_name or "", exe_file, language, compile_result, temp_folder)
                parts.append(f"Test result: {test_result}")
                if test_data:
                    parts.append(f"Test data: {json.dumps(test_data, ensure_ascii=False)}")
            self.reset_dir(self.temp_dir)
            return "\n".join(parts)

    def run_tests(
        self,
        test_cases: Any,
        task_name: str,
        exe_file: Optional[str],
        language: str,
        compile_result: bool,
        temp_folder: str
    ) -> tuple[str, dict[str, str]]:
        try:
            test_cases = ast.literal_eval(test_cases) if isinstance(test_cases, str) else test_cases
        except Exception as e:
            print(f"Error parsing test cases for task {task_name}: {e}")
            return "ERROR: Invalid test cases format", {}

        if not isinstance(test_cases, dict):
            return "ERROR: Invalid test cases format", {}

        test_result = "PASSED"
        test_data: dict[str, str] = {}

        if exe_file and compile_result:
            for test in test_cases.keys():
                single_test = test_cases[test]
                assert_equal = str(single_test.get("Assert", "True"))
                test_input = single_test.get("Input", "None")
                test_output = single_test.get("Output", "")

                if assert_equal == "Manual":
                    test_data[test] = "MANUAL CHECK REQUIRED"
                    test_result = "MANUAL CHECK REQUIRED"
                    continue

                cmd: list[str]
                if test_input != "None" and test_input is not None and str(test_input).strip() != "":
                    input_cmd = [x for x in str(test_input).split(" ")]
                else:
                    input_cmd = []

                if language == "Python":
                    cmd = ["python3", exe_file]
                elif language == "Java":
                    cmd = ["java", exe_file]
                else:
                    cmd = [exe_file]

                cmd.extend(input_cmd)

                try:
                    p_out = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        cwd=temp_folder,
                        timeout=self.timeout,
                    )
                    output = self.clean_text(p_out.stdout).upper()
                    expected = self.clean_text(test_output).upper()

                    if p_out.returncode != 0:
                        test_data[test] = f"ERROR: non-zero exit {p_out.returncode}: {p_out.stderr.strip()}"
                        test_result = "FAILED"
                    elif assert_equal == "True":
                        if output == expected:
                            test_data[test] = "PASSED"
                        else:
                            test_data[test] = f"ERROR: {output}, NOT EQUAL TO EXPECTED OUTPUT, {expected}"
                            test_result = "FAILED"
                    elif assert_equal == "False":
                        if output != expected:
                            test_data[test] = "PASSED"
                        else:
                            test_data[test] = f"ERROR: {output}, EQUAL TO FAULTY OUTPUT, {expected}"
                            test_result = "FAILED"
                    else:
                        test_data[test] = f"ERROR: unsupported Assert value {assert_equal}"
                        test_result = "ERROR"
                except subprocess.TimeoutExpired:
                    test_result = "FAILED"
                    test_data[test] = "ERROR: TIMEOUT"
                except Exception as e:
                    test_result = "ERROR"
                    test_data[test] = f"ERROR: {str(e)}"
        else:
            test_result = "ERROR: No program found."
        
        return test_result, test_data


    def clean_text(self, text: Any) -> str:
        if isinstance(text, str):
            text = text.strip()
            text = text.replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "").replace("\\n", "")
            return text
        return "" if text is None else str(text)

    def get_inline_tests(self, row: pd.Series) -> Optional[Any]:
        for col in row.index:
            if str(col).strip().lower() in {"tests", "test_cases", "testcases"}:
                value = row[col]
                if not pd.isna(value) and str(value).strip():
                    return value
        return None

    def reset_dir(self, dir_path: str | Path) -> None:
        p = Path(dir_path)
        p.mkdir(parents=True, exist_ok=True)
        for child in p.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def normalize_columns(df: pd.DataFrame) -> dict[str, str]:
    return {str(col).strip().lower(): col for col in df.columns}


def find_attempt_col(df: pd.DataFrame) -> Optional[str]:
    cols = normalize_columns(df)
    return cols.get("attempts") or cols.get("attempt")


def find_clean_code_col(df: pd.DataFrame) -> Optional[str]:
    cols = normalize_columns(df)
    return cols.get("clean_code")


def find_task_name(row: pd.Series, file_path: Path) -> str:
    normalized = {str(col).strip().lower(): col for col in row.index}
    for key in ("task_name", "task"):
        col = normalized.get(key)
        if col is not None and not pd.isna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    stem = file_path.stem
    return stem.split("_")[-1] if "_" in stem else stem


def language_from_value(value: Any) -> Optional[str]:
    if pd.isna(value):
        return None
    token = str(value).strip()
    if token in SUPPORTED_LANGUAGES:
        return token
    return LANGUAGE_TOKENS.get(token.casefold())


def language_from_filename(path: Path) -> Optional[str]:

    return path.stem.split("_", 1)[0]

def detect_language(file_path: Path, df: pd.DataFrame, row: pd.Series, clean_code_col: str, forced_language: Optional[str]) -> str:
    if forced_language:
        return forced_language
    cols = normalize_columns(df)
    lang_col = cols.get("language") or cols.get("lang")
    if lang_col:
        lang = language_from_value(row.get(lang_col))
        if lang:
            return lang
    lang = language_from_filename(file_path)
    if lang:
        return lang
    return "Unsupported"


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def write_table(path: Path, df: pd.DataFrame) -> None:
    if path.suffix.lower() == ".csv":
        df.to_csv(path, index=False)
    else:
        df.to_excel(path, index=False)


def load_tests(path: Optional[Path]) -> dict[str, Any]:
    if not path:
        return {}
    df = read_table(path)
    cols = normalize_columns(df)
    task_col = cols.get("task_name") or cols.get("task")
    tests_col = cols.get("tests") or cols.get("test_cases") or cols.get("testcases")
    if not task_col or not tests_col:
        raise ValueError("The tests file must contain Task_Name/Task and Tests/test_cases columns.")
    out: dict[str, Any] = {}
    for _, row in df.iterrows():
        if not pd.isna(row[task_col]):
            out[str(row[task_col]).strip()] = row[tests_col]
    return out


def iter_files(folder: Path, patterns: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(folder.rglob(pattern) if recursive else folder.glob(pattern))
    return sorted({p for p in files if p.is_file() and not p.name.startswith("~$")})


def evaluate_file(path: Path, tests_by_task: dict[str, Any], temp_root: Path, forced_language: Optional[str]) -> tuple[int, int]:
    df = read_table(path)
    attempt_col = find_attempt_col(df)
    clean_code_col = find_clean_code_col(df)
    evaluator =FolderCodeEvaluator(temp_root)
    if not attempt_col or not clean_code_col:
        print(f"SKIP {path}: missing attempts/attempt or clean_code column")
        return 0, 0

    if "compile_result" not in df.columns:
        df["compile_result"] = ""

    mask = df[attempt_col].notna() & df[attempt_col].astype(str).str.strip().ne("")
    total = int(mask.sum())
    done = 0
    language_counts: dict[str, int] = {}

    for idx, row in df.loc[mask].iterrows():
        language = detect_language(path, df, row, clean_code_col, forced_language)
        language_counts[language] = language_counts.get(language, 0) + 1
        task_name = find_task_name(row, path)
        df.at[idx, "compile_result"] = evaluator.compile_and_test(
            code_value=row[clean_code_col],
            language=language,
            task_name=task_name,
            tests_by_task=tests_by_task,
            row=row,
        )
        done += 1

    write_table(path, df)
    languages_used = ", ".join(f"{k}={v}" for k, v in sorted(language_counts.items())) or "none"
    #print(f"UPDATED {path}: evaluated {done}/{len(df)} rows; languages used: {languages_used}")
    return done, total


def evaluate_file_task(payload: dict[str, Any]) -> tuple[str, int, int, dict[str, int], Optional[str]]:
    return evaluate_file(
        path=Path(payload["path"]),
        tests_by_task=payload["tests_by_task"],
        temp_root=Path(payload["temp_root"]),
        forced_language=payload.get("forced_language")
    )


def positive_int(value: str) -> int:
    out = int(value)
    if out < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Recursively compile/test clean_code rows and save compile_result in each source file.")
    parser.add_argument("--folder", required=True, type=Path, help="Folder containing the spreadsheets/CSVs to update.")
    parser.add_argument("--language", type=str, help="Force a specific language for all files (overrides detection).")
    parser.add_argument("--no-recursive", action="store_true", help="Only process files directly inside --folder.")
    args = parser.parse_args()

    temp_dir = "temp/folder_eval"
    timeout = 5
    #tests_file = Path("data/all_tasks.xlsx")
    tests_file = None

    patterns = ["*.xlsx", "*.xls", "*.csv"]
    tests_by_task = load_tests(tests_file)

    files = iter_files(args.folder, patterns, recursive=not args.no_recursive)


    total_done = 0
    total_target = 0
    total_files = len(files)
    completed_files = 0
    failures: list[tuple[str, str]] = []

    max_workers = os.cpu_count() or 4

    if total_files == 0:
        print("Finished. No matching files found.")
        return

    payloads = [{
        "path": str(path),
        "tests_by_task": tests_by_task,
        "forced_language": args.language,
        "temp_root": temp_dir,
        "timeout": timeout,
    } for path in files]


    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(evaluate_file, path, tests_by_task, temp_dir, args.language): path
            for path in files
        }
        for future in as_completed(futures):
            path = futures[future]
            completed_files += 1
            left = total_files - completed_files
            try:
                results = future.result()
                total_done += 1
                total_target += 1
                print(f"Files done: {completed_files}/{total_files}; left: {left}.")
            except Exception as exc:
                print(f"Files done: {completed_files}/{total_files}; left: {left}. FAILED {path}: {exc}")

    try:
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            shutil.rmtree(temp_dir)
    except Exception:
        pass

    print(f"Finished. Evaluated {total_done}/{total_target} selected rows across {len(files)} files.")
    if failures:
        print(f"Failures/skips: {len(failures)}")
        for path, error in failures:
            print(f"  {path}: {error}")


if __name__ == "__main__":
    main()

