import os
import pandas as pd



def get_generated_code(df_task_data):
      
   generated_solution = df_task_data[df_task_data["attempt"] == 0.0]["content"].values[0]
   return generated_solution


def get_baseline():

    for file in os.listdir("output_alvis_new"):
        if file.endswith(".csv"):
            print("Processing file:", file)
            df = pd.read_csv(os.path.join("output_alvis_new", file))

            if df.empty:
                print(f"Warning: {file} is empty. Skipping.")
                continue

            df_baseline = pd.DataFrame()

            for index, row in df.iterrows():
                model = row["Model"]
                attempts = int(row["Attempts"])
                task = row["Task_Name"]
                lang = row["Language"]

                new_row = {
                        "Task_Name": task,
                        "Language": lang,
                        "Model": model,
                        "Task_Description": row["Task_Description"],
                        "Solution": row["Solution"]
                }

                if attempts == 0:
                    new_row["Generated_code"] = row["Generated_code"]
                    new_row["Attempts"] = attempts
                    
                else: 
                    
                    task_file = f"output_alvis_new/agentic_individual_tasks/{model}/{lang}_{model}_{task}.xlsx"
                    if not os.path.exists(task_file):
                        task_file = f"output_combined/agentic_individual_tasks/{model}/{lang}_{model}_{task}.xlsx"
                        
                    df_task_data = pd.read_excel(task_file)
                    gen_code = get_generated_code(df_task_data)

                    new_row["Generated_code"] = gen_code
                    new_row["Attempts"] = 0

                df_baseline = pd.concat([df_baseline, pd.DataFrame([new_row])], ignore_index=True)

            print("Baseline for", lang, model)
            print(f"Number of rows in agent: {len(df)}")
            print(f"Number of rows in baseline: {len(df_baseline)}")

            baseline_file =f"output_baseline/{lang}_{model}_baseline.csv"
            df_baseline.to_csv(baseline_file, index=False)


if __name__ == "__main__":
    get_baseline()