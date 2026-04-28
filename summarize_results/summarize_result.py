from pathlib import Path
import pandas as pd


def summarize_csv_file(csv_path: Path, result_type: str) -> dict:
    df = pd.read_csv(csv_path)

    compile_col = df.get("Compile_Result", pd.Series(dtype="object")).fillna("").astype(str).str.strip()
    test_col = df.get("Test_Result", pd.Series(dtype="object")).fillna("").astype(str).str.strip()
    task_col = df.get("Task_Name", pd.Series(dtype="object")).fillna("").astype(str).str.strip()

    if "Model" in df.columns:
        models = [m for m in df["Model"].dropna().astype(str).str.strip().unique() if m]
        model_name = models[0] if models else csv_path.stem
    else:
        model_name = csv_path.stem

    if "Language" in df.columns:
        languages = [l for l in df["Language"].dropna().astype(str).str.strip().unique() if l]
        language = languages[0] if languages else ""
    else:
        language = csv_path.stem

    return {
        "model": model_name,
        "type": result_type,
        "language": language,
        "Compile_result": (compile_col == "Compilation successful").sum(),
        "Test_result": (test_col == "PASSED").sum(),
        "Nr_tasks": (task_col != "").sum(),
    }


def summarize_folders_to_excel(baseline_folder: str, agent_folder: str, output_excel: str):
    baseline_folder = Path(baseline_folder)
    agent_folder = Path(agent_folder)

    rows = []


    for csv_file in sorted(agent_folder.glob("*.csv")):
        try:
            rows.append(summarize_csv_file(csv_file, "agent"))
            print(f"Processed agent: {csv_file.name}")
        except Exception as e:
            print(f"Failed to process {csv_file}: {e}")

    for csv_file in sorted(baseline_folder.glob("*.csv")):


        try:
            result = summarize_csv_file(csv_file, "baseline")
            if result["model"] in [row["model"] for row in rows if row["type"] == "agent"] and result["language"] in [row["language"] for row in rows if row["type"] == "agent"]:
                rows.append(result)
            print(f"Processed baseline: {csv_file.name}")
        except Exception as e:
            print(f"Failed to process {csv_file}: {e}")



    if not rows:
        print("No CSV files found.")
        return

    summary_df = pd.DataFrame(
        rows,
        columns=["model", "type", "language", "Compile_result", "Test_result", "Nr_tasks"]
    )
    summary_df.to_excel(output_excel, index=False)
    print(f"Summary written to: {output_excel}")

if __name__ == "__main__":
    baseline_folder = "../eval_baseline_5_iterations"
    new_results_folder = "../eval_alvis_new"
    output_excel = "summary.xlsx"

    summarize_folders_to_excel(baseline_folder, new_results_folder, output_excel)