import argparse
from pathlib import Path
import pandas as pd

CATEGORY_ORDER = [
    'Syntax', 'Semantic', 'Dependency', 'Type mismatch',
    'Language specific', 'Other', 'no_error'
]
LANGUAGE_ORDER = ['Python', 'Java', 'C', 'Rust', 'Haskell', 'Ada']


def create_transition_csvs(input_csv, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(
        input_csv,
        usecols=['Language', 'Type', 'Category_From', 'Category_To'],
        dtype='string'
    ).dropna(subset=['Language', 'Type', 'Category_From', 'Category_To'])
    df['Type'] = df['Type'].str.strip().str.lower().replace({'agents': 'agent', 'base': 'baseline'})
    df = df[df['Type'].isin(['agent', 'baseline'])]

    found_categories = set(df['Category_From']) | set(df['Category_To'])
    categories = [x for x in CATEGORY_ORDER if x in found_categories]
    categories += sorted(found_categories - set(categories))
    languages = [x for x in LANGUAGE_ORDER if x in set(df['Language'])]
    languages += sorted(set(df['Language']) - set(languages))

    index_rows = []
    for language in ['All_Languages'] + languages:
        subset = df if language == 'All_Languages' else df[df['Language'] == language]
        for kind in ['baseline', 'agent', 'all']:
            selected = subset if kind == 'all' else subset[subset['Type'] == kind]
            counts = pd.crosstab(selected['Category_From'], selected['Category_To'])
            counts = counts.reindex(index=categories, columns=categories, fill_value=0)
            counts.index.name = 'Category_From'
            counts.columns.name = 'Category_To'
            percentages = counts.div(counts.sum(axis=1).replace(0, float('nan')), axis=0).fillna(0).mul(100).round(2)
            percentages.index.name = 'Category_From'
            percentages.columns.name = 'Category_To'
            stem = f'category_transitions_{language.lower()}_{kind}'
            counts.to_csv(output_dir / f'{stem}_counts.csv')
            percentages.to_csv(output_dir / f'{stem}_percent.csv')
            index_rows.append({'Language': language, 'Type': kind, 'Transitions': int(counts.to_numpy().sum()),
                               'Counts_File': stem + '_counts.csv', 'Percent_File': stem + '_percent.csv'})
    pd.DataFrame(index_rows).to_csv(output_dir / 'transition_index.csv', index=False)
    print(f'Saved {len(index_rows) * 2} matrices plus transition_index.csv in {output_dir}')
    print(pd.DataFrame(index_rows)[['Language', 'Type', 'Transitions']].to_string(index=False))


if __name__ == '__main__':

    input_csv = "error_survival_detailed.csv"
    output_folder = "transition_matrices"
    create_transition_csvs(input_csv, output_folder)
