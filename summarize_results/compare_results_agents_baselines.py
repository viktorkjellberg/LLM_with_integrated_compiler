#!/usr/bin/env python3
"""Compare evaluation workbooks from two folders and export an Excel summary.

Expected input files contain columns like:
Task_Name, Language, Model, ..., Compile_Result, Test_Result, ...

The script counts, per MODEL + LANGUAGE:
- baseline_compiler_result: rows where Compile_Result contains
  "Compilation successful" in the baseline folder
- agent_compiler_result: rows where Compile_Result contains
  "Compilation successful" in the agent folder
- baseline_test_result: rows where Test_Result contains "PASSED"
  in the baseline folder
- agent_test_result: rows where Test_Result contains "PASSED"
  in the agent folder
- total_tasks: task count shared by both sides when equal; otherwise the
  larger of the two counts is used and a warning is written

Output columns:
MODEL | LANGUAGE | baseline_compiler_result | agent_compiler_result |
baseline_test_result | agent_test_result | total_tasks

Usage:
    python compare_evaluations.py /path/to/baseline_folder /path/to/agent_folder \
        -o comparison.xlsx
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}
COMPILE_SUCCESS_PATTERN = re.compile(r"compilation\s+successful", re.IGNORECASE)
TEST_PASS_PATTERN = re.compile(r"\bpassed\b", re.IGNORECASE)
Key = Tuple[str, str]


class WorkbookFormatError(Exception):
    """Raised when an input workbook does not contain required columns."""


def normalize_header(value: object) -> str:
    return str(value).strip().lower() if value is not None else ""


def iter_workbook_rows(path: Path) -> Iterable[Tuple[str, str, str, str]]:
    """Yield (model, language, compile_result, test_result) rows from all sheets."""
    wb = load_workbook(path, data_only=True, read_only=True)

    found_any_valid_sheet = False
    for ws in wb.worksheets:
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            continue

        header_map = {normalize_header(v): idx for idx, v in enumerate(header_row)}
        required = {"model", "language", "compile_result", "test_result"}
        if not required.issubset(header_map.keys()):
            continue

        found_any_valid_sheet = True
        model_idx = header_map["model"]
        language_idx = header_map["language"]
        compile_idx = header_map["compile_result"]
        test_idx = header_map["test_result"]

        for row in ws.iter_rows(min_row=2, values_only=True):
            if row is None:
                continue
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue

            model = str(row[model_idx]).strip() if model_idx < len(row) and row[model_idx] is not None else "UNKNOWN"
            language = str(row[language_idx]).strip() if language_idx < len(row) and row[language_idx] is not None else "UNKNOWN"
            compile_result = str(row[compile_idx]) if compile_idx < len(row) and row[compile_idx] is not None else ""
            test_result = str(row[test_idx]) if test_idx < len(row) and row[test_idx] is not None else ""
            yield model, language, compile_result, test_result

    if not found_any_valid_sheet:
        raise WorkbookFormatError(
            f"{path.name} does not contain the required columns: Model, Language, Compile_Result, Test_Result"
        )


def summarize_folder(folder: Path) -> Tuple[Dict[Key, Dict[str, int]], List[Dict[str, object]], List[str]]:
    """Return aggregated stats by (model, language), per-file details, and warnings."""
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")

    stats: Dict[Key, Dict[str, int]] = defaultdict(lambda: {
        "compiler_result": 0,
        "test_result": 0,
        "total_tasks": 0,
        "file_count": 0,
    })
    file_details: List[Dict[str, object]] = []
    warnings: List[str] = []

    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        warnings.append(f"No Excel files found in {folder}")
        return stats, file_details, warnings

    for path in files:
        per_file: Dict[Key, Dict[str, int]] = defaultdict(lambda: {
            "compiler_result": 0,
            "test_result": 0,
            "total_tasks": 0,
        })
        try:
            for model, language, compile_result, test_result in iter_workbook_rows(path):
                key = (model, language)
                per_file[key]["total_tasks"] += 1
                if COMPILE_SUCCESS_PATTERN.search(compile_result):
                    per_file[key]["compiler_result"] += 1
                if TEST_PASS_PATTERN.search(test_result):
                    per_file[key]["test_result"] += 1
        except Exception as exc:
            warnings.append(f"Skipped {path.name}: {exc}")
            continue

        for (model, language), values in per_file.items():
            stats[(model, language)]["compiler_result"] += values["compiler_result"]
            stats[(model, language)]["test_result"] += values["test_result"]
            stats[(model, language)]["total_tasks"] += values["total_tasks"]
            stats[(model, language)]["file_count"] += 1
            file_details.append({
                "file_name": path.name,
                "model": model,
                "language": language,
                **values,
            })

    return stats, file_details, warnings


def choose_total_tasks(model: str, language: str, base_total: int, agent_total: int, warnings: List[str]) -> int:
    if base_total == agent_total:
        return base_total
    if base_total == 0:
        return agent_total
    if agent_total == 0:
        return base_total
    warnings.append(
        f"Task count mismatch for model={model}, language={language}: baseline={base_total}, agent={agent_total}. Using max value."
    )
    return max(base_total, agent_total)


def build_comparison_rows(
    baseline_stats: Dict[Key, Dict[str, int]],
    agent_stats: Dict[Key, Dict[str, int]],
    warnings: List[str],
) -> List[List[object]]:
    keys = sorted(set(baseline_stats) | set(agent_stats), key=lambda item: (item[0].lower(), item[1].lower()))
    rows: List[List[object]] = []
    for model, language in keys:
        base = baseline_stats.get((model, language), {})
        agent = agent_stats.get((model, language), {})
        base_total = base.get("total_tasks", 0)
        agent_total = agent.get("total_tasks", 0)
        total_tasks = choose_total_tasks(model, language, base_total, agent_total, warnings)
        rows.append([
            model,
            language,
            base.get("compiler_result", 0),
            agent.get("compiler_result", 0),
            base.get("test_result", 0),
            agent.get("test_result", 0),
            base.get("total_tasks", 0),
            agent.get("total_tasks", 0),
        ])
    return rows


def autosize_columns(ws) -> None:
    for col_cells in ws.columns:
        max_length = 0
        col_idx = col_cells[0].column
        for cell in col_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_length + 2, 40)


def write_output(
    output_path: Path,
    comparison_rows: List[List[object]],
    baseline_details: List[Dict[str, object]],
    agent_details: List[Dict[str, object]],
    warnings: List[str],
) -> None:
    wb = Workbook()

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)

    ws = wb.active
    ws.title = "Summary"
    headers = [
        "MODEL",
        "LANGUAGE",
        "baseline_compiler_result",
        "agent_compiler_result",
        "baseline_test_result",
        "agent_test_result",
        "baseline_total_tasks",
        "agent_total_tasks",
    ]
    ws.append(headers)
    for row in comparison_rows:
        ws.append(row)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    ws.freeze_panes = "A2"
    autosize_columns(ws)

    details_ws = wb.create_sheet("File_Details")
    details_headers = [
        "side", "file_name", "model", "language", "compiler_result", "test_result", "total_tasks"
    ]
    details_ws.append(details_headers)
    for item in baseline_details:
        details_ws.append([
            "baseline",
            item["file_name"],
            item["model"],
            item["language"],
            item["compiler_result"],
            item["test_result"],
            item["total_tasks"],
        ])
    for item in agent_details:
        details_ws.append([
            "agent",
            item["file_name"],
            item["model"],
            item["language"],
            item["compiler_result"],
            item["test_result"],
            item["total_tasks"],
        ])
    for cell in details_ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    details_ws.freeze_panes = "A2"
    autosize_columns(details_ws)

    warn_ws = wb.create_sheet("Warnings")
    warn_ws.append(["message"])
    for message in warnings or ["No warnings"]:
        warn_ws.append([message])
    for cell in warn_ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    autosize_columns(warn_ws)

    wb.save(output_path)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare baseline and agent evaluation workbooks.")
    parser.add_argument("-b", "--baseline", type=Path, help="Folder containing baseline Excel files")
    parser.add_argument("-a", "--agent", type=Path, help="Folder containing agent Excel files")
    parser.add_argument("-o", "--output", type=Path, default=Path("evaluation_comparison.xlsx"), help="Output Excel file path")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    try:
        baseline_stats, baseline_details, warnings = summarize_folder(args.baseline)
        agent_stats, agent_details, agent_warnings = summarize_folder(args.agent)
        warnings.extend(agent_warnings)
        comparison_rows = build_comparison_rows(baseline_stats, agent_stats, warnings)
        write_output(args.output, comparison_rows, baseline_details, agent_details, warnings)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote comparison workbook to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
