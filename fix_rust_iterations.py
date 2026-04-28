import os
import pandas as pd



def fix_rust_iterations():

    for file in os.listdir("output/combined/"):
        if file.endswith(".json"):
            file_path = os.path.join("output/combined/", file)
            df = pd.read_csv(file_path)
            