import argparse
from pathlib import Path

import pandas as pd


SUCCESS_VALUE = "Compilation successful"


def find_correlated_file(
    agentic_root: Path,
    language: str,
    model: str,
    task_name: str,
) -> Path | None:
    """
    Expected structure:

    agentic_individual_tasks/
        codellama:34b/
            Ada_codellama:34b_A+B.xlsx
    """

    model_folder = agentic_root / model
    expected_file = model_folder / f"{language}_{model}_{task_name}.xlsx"

    if expected_file.exists():
        return expected_file

    # Fallback:
    # Search the model folder in case characters in the task name or model
    # have been encoded/sanitized slightly differently.
    if model_folder.exists():
        expected_name = f"{language}_{model}_{task_name}".lower()

        for file in model_folder.glob("*.xlsx"):
            if file.stem.lower() == expected_name:
                return file

    return None


def get_replacement_content(agent_file: Path) -> tuple[str | None, int | None, str]:
    """
    Returns:
        (content, attempt, reason)

    Selection logic:
    1. Lowest attempt where compile_result == "Compilation successful"
    2. Otherwise attempt == 4
    """

    df = pd.read_excel(agent_file)

    required_columns = {
        "content",
        "attempt",
        "compile_result",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        return (
            None,
            None,
            f"Missing columns: {sorted(missing_columns)}",
        )

    attempts = df[df["attempt"].notna()].copy()

    if attempts.empty:
        return None, None, "No rows with an attempt value"

    attempts["attempt"] = pd.to_numeric(
        attempts["attempt"],
        errors="coerce",
    )

    attempts = attempts[attempts["attempt"].notna()].copy()

    # 1. Lowest successful attempt
    successful = attempts[
        attempts["compile_result"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq(SUCCESS_VALUE)
    ]

    if not successful.empty:
        selected = successful.sort_values("attempt").iloc[0]

        return (
            selected["content"],
            int(selected["attempt"]),
            f"successful attempt {int(selected['attempt'])}",
        )

    # 2. Fallback to attempt 4
    attempt_4 = attempts[attempts["attempt"] == 4]

    if not attempt_4.empty:
        selected = attempt_4.iloc[0]

        return (
            selected["content"],
            4,
            "attempt 4 fallback",
        )

    return None, None, "No successful attempt and no attempt 4"


def process_file(
    input_file: Path,
    output_file: Path,
    agentic_root: Path,
) -> None:

    print(f"\nProcessing: {input_file.name}")

    df = pd.read_csv(input_file)

    required_columns = {
        "Task_Name",
        "Language",
        "Model",
        "Generated_code",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        print(
            f"  SKIPPING: missing columns "
            f"{sorted(missing_columns)}"
        )
        return

    updated = 0
    missing_files = 0
    no_replacement = 0

    for index, row in df.iterrows():

        task_name = str(row["Task_Name"]).strip()
        language = str(row["Language"]).strip()
        model = str(row["Model"]).strip()

        agent_file = find_correlated_file(
            agentic_root=agentic_root,
            language=language,
            model=model,
            task_name=task_name,
        )

        if agent_file is None:
            print(
                f"  MISSING FILE: "
                f"{language} | {model} | {task_name}"
            )

            missing_files += 1
            continue

        replacement, attempt, reason = get_replacement_content(
            agent_file
        )

        if replacement is None:

            no_replacement += 1
            continue

        df.at[index, "Generated_code"] = replacement
        df.at[index, "Attempts"] = attempt

        updated += 1


    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_file,
        index=False,
    )

    print(f"\nSaved: {output_file}")
    print(f"  Updated rows: {updated}")
    print(f"  Missing correlated files: {missing_files}")
    print(f"  Rows without replacement: {no_replacement}")


def process_folder(
    input_folder: Path,
    output_folder: Path,
    agentic_root: Path,
) -> None:

    input_folder = input_folder.resolve()
    output_folder = output_folder.resolve()
    agentic_root = agentic_root.resolve()

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = sorted(input_folder.glob("*.csv"))

    if not files:
        print(
            f"No CSV files found in: {input_folder}"
        )
        return

    print(f"Found {len(files)} CSV files.")
    print(f"Agent files: {agentic_root}")
    print(f"Output: {output_folder}")

    for input_file in files:

        output_file = (
            output_folder
            / input_file.name
        )

        process_file(
            input_file=input_file,
            output_file=output_file,
            agentic_root=agentic_root,
        )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Replace Generated_code in baseline CSV files "
            "using corresponding agentic task XLSX files."
        )
    )

    parser.add_argument(
        "input_folder",
        type=Path,
        help="Folder containing baseline CSV files",
    )

    parser.add_argument(
        "output_folder",
        type=Path,
        help="Folder where updated CSV files are saved",
    )

    args = parser.parse_args()

    agentic_root = args.input_folder / Path("agentic_individual_tasks")

    process_folder(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        agentic_root=agentic_root,
    )


if __name__ == "__main__":
    main()