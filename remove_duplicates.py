
import os
import pandas as pd
from collections import Counter
import argparse

parser = argparse.ArgumentParser(description="Check number of tasks in CSV files")
parser.add_argument("--input_dir", "-f", default="./output_combined", help="Directory containing CSV files")
args = parser.parse_args()



def remove_duplicates_from_file(file_path):

    data = pd.read_csv(file_path)
    #print(c)
    print(len(data))

    data_wo_dup = data.drop_duplicates(subset=["Task_Name"], keep="first")

    data_wo_dup = data_wo_dup[data_wo_dup["Generated_code"].notna()]

    #print(c2)
    print(len(data_wo_dup))
    data_wo_dup.to_csv(file_path, index=False)   


if __name__ == "__main__":
    for file in os.listdir(args.input_dir):
        if file.endswith(".csv"):
            print(f"Processing file: {file}")
            remove_duplicates_from_file(os.path.join(args.input_dir, file))