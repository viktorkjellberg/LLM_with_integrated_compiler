import pandas as pd
import os
from pathlib import Path

import argparse

parser = argparse.ArgumentParser(description="Check number of tasks in CSV files")
parser.add_argument("--input_dir", "-f", default="./output_combined", help="Directory containing CSV files")
args = parser.parse_args()

# Your dictionary of CSV files





# Fixed language column order
language_order = ["ADA", "RUST", "HASKELL", "PYTHON", "JAVA", "C"]

all_dfs = []


input_dir = Path(args.input_dir)

for file_path in input_dir.glob("*.csv"):

    df = pd.read_csv(file_path)

    # Keep only needed columns
    df = df[["Model", "Language", "Task_Name"]].copy()

    # Normalize language names to match requested output
    df["Language"] = df["Language"].str.upper()

    all_dfs.append(df)

# Combine all files
combined_df = pd.concat(all_dfs, ignore_index=True)

# Count unique Task_Name per Model + Language
summary = (
    combined_df.groupby(["Model", "Language"])["Task_Name"]
    .nunique()
    .unstack(fill_value=0)
)

# Ensure all requested language columns exist, even if missing
summary = summary.reindex(columns=language_order, fill_value=0)

# Put Model back as a column
summary = summary.reset_index()

# Rename Model column to MODEL if you want exact style
summary = summary.rename(columns={"Model": "MODEL"})

# Save output
summary.to_csv("summary_output.csv", index=False)

# Print output
print(summary)