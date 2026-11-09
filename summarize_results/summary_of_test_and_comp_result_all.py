import pandas as pd
from pathlib import Path

# Folder containing your CSV files

input_folders = [
    (Path("../eval_baseline"), "baseline"),
    (Path("../eval_agent"), "agent")]

# Columns to keep
columns_to_keep = [
    "Task_Name",
    "Language",
    "Model",
    "Compile_Result",
    "Test_Result"
]

all_data = []

# Go through all CSV files in the folder
for input_folder, type_run in input_folders:
    for csv_file in input_folder.glob("*.csv"):

        # Don't accidentally include a previously generated combined file
        if csv_file.name == "combined_results.csv":
            continue

        print(f"Reading: {csv_file.name}")

        df = pd.read_csv(csv_file)

        if df.empty:
            print(f"Skipping {csv_file.name}: empty file")
            continue

        # Check that required columns exist
        missing_columns = [
            col for col in columns_to_keep
            if col not in df.columns
        ]

        if missing_columns:
            print(
                f"Skipping {csv_file.name}: "
                f"missing columns {missing_columns}"
            )
            continue

        # Keep only the required columns
        df = df[columns_to_keep].copy()

        df["Type"] = type_run

        # Convert Test_Result:
        # PASSED -> 1
        # Anything else -> 0
        df["Test_Result"] = (
            df["Test_Result"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("PASSED")
            .astype(int)
        )

        # Convert Compile_result:
        # "Compilation successful" -> 1
        # Anything else -> 0
        df["Compile_Result"] = (
            df["Compile_Result"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("compilation successful")
            .astype(int)
        )

        all_data.append(df)

# Combine all CSV files
if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)

    combined_df=combined_df.drop_duplicates(subset=['Task_Name', 'Language', 'Model', 'Type'], keep='first')

    # Save result
    output_file = "summary/combined_results_all.csv"
    combined_df.to_csv(output_file, index=False)

    print()
    print(f"Combined {len(all_data)} CSV files.")
    print(f"Total rows: {len(combined_df)}")
    print(f"Saved to: {output_file}")

    # Show summary
    print()
    print("Test results:")
    print(combined_df["Test_Result"].value_counts())

    print()
    print("Compilation results:")
    print(combined_df["Compile_Result"].value_counts())

else:
    print("No valid CSV files found.")