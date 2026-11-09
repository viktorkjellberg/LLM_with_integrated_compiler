This file explation how to recreate the experiment. It generates solutions in the chosen languages with the specified LLMs. If you run all files then you will get the generated solutions, all data for the tables and plots used in the paper.

### Run the LLMs for agents and baselines

Generate the solution for each task in all tasks with the settings in ollama_server.yaml, where the programming languages, models and servers are specified.
In these the LLMs have access to iteartive compiler feedback for the chosen language and generates candidate solutions unitl either the number of iterations hit the max value of 5 or the solution candidate compiles.

```bash
python3 main_agentc.py --settings_file settings/ollama_server.yaml
python3 main_agentc.py --settings_file settings/open_ai.yaml
```

Generate baseline solutions

```bash
python3 main_baseline.py --settings_file settings/ollama_server.yaml
python3 main_baseline.py --settings_file settings/open_ai.yaml
python3 run_eval_on_baseline_tasks.py --folder output_baseline/agentic_individual_tasks
python3 update_baseline_output.py output_baseline output_baseline
```

The baseline does not run the compiler while generating and just iterate 5 times but to allow a fair comparision run_eval_on_baseline_tasks.py adds compiler results to each result files and update_baseline_output updates the result so that it only include the iterations until a compiled solution was generated.

### Evaluate output

Evaluate all generated solutions by compiling the solutions and running the test cases. The script runs multiple evaluations paralell.

```bash
python3 run_tests_eval_paralell.py
```

After which you will have csv and xlsx files with the compile result, test result, number of iterations needed and the markdown code.

The following code combines all agent and baseline data into two files for analysis.

```bash
cd summarize_results
python3 combine_into_one_json.py ../eval_agent/ ../output_agent/agentic_individual_tasks/ -o combined_agent.json
python3 combine_into_one_json.py ../eval_baseline/ ../output_baseline/agentic_individual_tasks/ -o combined_baseline.json
```

### Categorize Errors

Categorize all errors from all iterations for baseline and agents based on each languages based on the categorization from settings_error_types. The results are saved in category_error in a file each for agents and baselines.

```bash
cd categorize_errors
python3 categorize_errors.py
```

### Analysis of results

Cleanup script that creates new files over errors in new_files

```bash
cd categorize_errors/error_analysis_per_iteration
python3 remove_iterations.py
```

Count errors per iteration

```bash
cd categorize_errors/error_analysis_per_iteration
python3 count_error_per_iteration.py
python3 plot_all_errors_iteratively.py
```

Generate plots in the stacked_area_plots over the number of errors in each iteration for all languages.

Calculate error survivla rate

```bash
cd categorize_errors/error_analysis_per_iteration
python3 error_change_iterations.py
python3 calculate_survival_rate.py
python3 create_survival_table.py
```

This saves the survivla rate as overleaf tables

Next we create the heatmap over error transitions per langauge but in the paper we will only use the _all_languages_agent_percent.png

```bash
cd categorize_errors/error_analysis_per_iteration
python3 heatmaps.py
python3 create_heatmap.py
```

This creates the plots for errors per language and models.

```bash
cd summarize_results
python3 summarize_error.py ../categorize_errors/category_error/ ../plots/category_counts_iteration_4.xlsx
cd ../plots
python3 plot_error_language_model.py category_counts_iteration_4.xlsx
python3 plot_error_language_model_hori.py category_counts_iteration_4.xlsx
```

Plot test results

```bash
cd summarize_results
python3 summary_of_test_and_comp_result_all.py
python3 plot_test_results.py
```

This creates a summary csv over compile and test results and the plot for test results in summary
