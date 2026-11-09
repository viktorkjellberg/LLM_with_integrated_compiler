#!/usr/bin/env bash
# Runs every step in RUN.md in order, from generating solutions to the final plots.
#
# Usage:
#   ./run_all.sh                    # run everything
#   ./run_all.sh --skip-generation  # skip the LLM runs (agents + baselines)
#   ./run_all.sh --skip-eval        # also skip compiling/testing the solutions
#
# Each step runs from the repo root in its own subshell, so the `cd`s in
# RUN.md don't stack up. The script stops at the first step that fails.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
ERR_DIR="categorize_errors/error_analysis_per_iteration"

SKIP_GENERATION=0
SKIP_EVAL=0
for arg in "$@"; do
    case "$arg" in
        --skip-generation) SKIP_GENERATION=1 ;;
        --skip-eval) SKIP_GENERATION=1; SKIP_EVAL=1 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

# run <dir relative to root> <python args...>
run() {
    local dir="$1"; shift
    echo
    echo ">>> [$dir] $PY $*"
    ( cd "$ROOT/$dir" && "$PY" "$@" )
}

# --- Run the LLMs for agents and baselines -------------------------------
if [[ $SKIP_GENERATION -eq 0 ]]; then
    run . main_agentc.py --settings_file settings/test.yaml
    run . main_agentc.py --settings_file settings/open_ai.yaml

    run . main_baseline.py --settings_file settings/test.yaml
    run . main_baseline.py --settings_file settings/open_ai.yaml
    run . run_eval_on_baseline_tasks.py --folder output_baseline/agentic_individual_tasks
    run . update_baseline_output.py output_baseline output_baseline
fi

# --- Evaluate output -----------------------------------------------------
if [[ $SKIP_EVAL -eq 0 ]]; then
    run . run_tests_eval_paralell.py
fi

run summarize_results combine_into_one_json.py ../eval_agent/ ../output_agent/agentic_individual_tasks/ -o combined_agent.json
run summarize_results combine_into_one_json.py ../eval_baseline/ ../output_baseline/agentic_individual_tasks/ -o combined_baseline.json

# --- Categorize errors ---------------------------------------------------
run categorize_errors categorize_errors.py

# --- Analysis of results -------------------------------------------------
run "$ERR_DIR" remove_iterations.py

#run "$ERR_DIR" count_error_per_iteration.py
run "$ERR_DIR" plot_all_errors_iteratively.py

run "$ERR_DIR" error_change_iterations.py
run "$ERR_DIR" calculate_survival_rate.py
run "$ERR_DIR" create_survival_table.py

run "$ERR_DIR" heatmaps.py
run "$ERR_DIR" create_heatmap.py

# --- Errors per language and model --------------------------------------
run summarize_results summarize_error.py ../categorize_errors/category_error/ ../plots/category_counts_iteration_4.xlsx
run plots plot_error_language_model.py category_counts_iteration_4.xlsx
run plots plot_error_language_model_hori.py category_counts_iteration_4.xlsx

# --- Test results --------------------------------------------------------
run summarize_results summary_of_test_and_comp_result_all.py
run summarize_results plot_test_results.py

echo
echo "All steps finished."
