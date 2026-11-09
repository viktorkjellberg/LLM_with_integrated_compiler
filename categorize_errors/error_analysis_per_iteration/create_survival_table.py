import argparse
import csv
from pathlib import Path

ITERATIONS = ['0->1', '1->2', '2->3', '3->4']
LANGUAGE_ORDER = ['Python', 'Java', 'C', 'Rust', 'Haskell', 'Ada']
METRICS = [
    ('Category_Survival_Rate', 'category_survival_table.tex', 'Primary error category survival rates across consecutive iterations.', 'tab:category_survival'),
    ('Compile_Result_Survival_Rate', 'compile_result_survival_table.tex', 'Exact compiler-result survival rates across consecutive iterations.', 'tab:compile_result_survival'),
]

def latex_escape(value):
    return str(value).replace('\\', r'\textbackslash{}').replace('&', r'\&').replace('%', r'\%').replace('_', r'\_').replace('#', r'\#')

def read_data(csv_path):
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        required = {'Language', 'Type', 'Iteration_Pair', 'Category_Survival_Rate', 'Compile_Result_Survival_Rate'}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing columns: {sorted(missing)}')
        rows = list(reader)
    result = {}
    for row in rows:
        key = (row['Language'].strip(), row['Type'].strip().lower(), row['Iteration_Pair'].strip())
        if key in result:
            raise ValueError(f'Duplicate row: {key}')
        result[key] = row
    return result

def create_table(data, metric, caption, label):
    languages = sorted({key[0] for key in data}, key=lambda x: (LANGUAGE_ORDER.index(x) if x in LANGUAGE_ORDER else len(LANGUAGE_ORDER), x))
    lines = [
        r'\begin{table*}[t]',
        r'\centering',
        r'\caption{' + caption + r' Values are percentages (\%).}',
        r'\label{' + label + '}',
        r'\small',
        r'\setlength{\tabcolsep}{4pt}',
        r'\begin{tabular}{l' + 'rr' * len(ITERATIONS) + '}',
        r'\toprule',
        'Language & ' + ' & '.join(r'\multicolumn{2}{c}{' + f'Iteration {pair.replace("->", r"$\rightarrow$")}' + '}' for pair in ITERATIONS) + r' \\',
        r'\cmidrule(lr){2-3} \cmidrule(lr){4-5} \cmidrule(lr){6-7} \cmidrule(lr){8-9}',
        ' & ' + ' & '.join(['Base & Agent'] * len(ITERATIONS)) + r' \\',
        r'\midrule',
    ]
    for language in languages:
        values = []
        for pair in ITERATIONS:
            for type_ in ('baseline', 'agent'):
                row = data.get((language, type_, pair))
                value = (row or {}).get(metric, '')
                try:
                    values.append(f'{float(value):.2f}' if str(value).strip() else '--')
                except (ValueError, TypeError):
                    values.append('--')
        lines.append(latex_escape(language) + ' & ' + ' & '.join(values) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', r'\end{table*}']
    return '\n'.join(lines) + '\n'

def main():

    output_folder = "overleaf_tables"
    input_csv = "error_survival_summary.csv"

    output = Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)
    data = read_data(input_csv)
    tables = []
    for metric, filename, caption, label in METRICS:
        table = create_table(data, metric, caption, label)
        path = output / filename
        path.write_text(table, encoding='utf-8')
        print(f'Saved: {path}')
        tables.append(table)
    combined_path = output / 'survival_tables.tex'
    combined_path.write_text('\n'.join(tables), encoding='utf-8')
    print(f'Saved: {combined_path}')
    print('Add \\usepackage{booktabs} to your Overleaf preamble.')

if __name__ == '__main__':
    main()
