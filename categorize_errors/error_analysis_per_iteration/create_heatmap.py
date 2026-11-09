#!/usr/bin/env python3
"""Create one heatmap per transition CSV in the transition_matrices folder.

CSV filenames containing 'percent' are plotted as percentages; filenames
containing 'count' are plotted as raw counts. Each figure is saved as PNG
and PDF in the transition_heatmaps folder.

The 'no_error' category is excluded from rows but retained in columns.
"""

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CATEGORY_ORDER = [
    'Syntax', 'Semantic', 'Dependency', 'Type mismatch',
    'Language specific', 'Other', 'no_error',
]

FONTSIZE = 14
TITLE_FONTSIZE = 18

def make_heatmap(csv_path: Path, output_dir: Path) -> None:
    filename = csv_path.stem.lower()
    if 'percent' in filename:
        metric = 'percent'
    elif 'count' in filename:
        metric = 'counts'
    else:
        print(f'SKIP (no count/percent in name): {csv_path.name}')
        return

    df = pd.read_csv(csv_path, index_col=0)
    if df.empty or len(df.columns) == 0:
        print(f'SKIP (empty matrix): {csv_path.name}')
        return

    df.index = df.index.map(lambda v: str(v).strip())
    df.columns = df.columns.map(lambda v: str(v).strip())
    df = df.apply(pd.to_numeric, errors='raise')

    categories = [c for c in CATEGORY_ORDER if c in df.index or c in df.columns]
    categories += sorted((set(df.index) | set(df.columns)) - set(categories))

    row_categories = [c for c in categories if c != 'no_error']
    col_categories = categories
    if not row_categories or not col_categories:
        print(f'SKIP (no plottable categories): {csv_path.name}')
        return

    matrix = df.reindex(index=row_categories, columns=col_categories, fill_value=0).fillna(0)
    data = matrix.to_numpy(dtype=float)

    n_rows, n_cols = data.shape
    fig, ax = plt.subplots(
        figsize=(max(9, n_cols * 1.25 + 2), max(7, n_rows * 0.9 + 2))
    )
    maximum = 100.0 if metric == 'percent' else max(float(data.max()), 1.0)
    im = ax.imshow(data, cmap='viridis', vmin=0, vmax=maximum, aspect='equal')

    display_col_categories = ['No Error' if c == 'no_error' else c for c in col_categories]
    ax.set_xticks(range(n_cols), labels=display_col_categories, rotation=40, ha='right')
    ax.set_yticks(range(n_rows), labels=row_categories)
    ax.set_xlabel('Error Category at Iteration i+1', fontsize=FONTSIZE)
    ax.set_ylabel('Error Category at Iteration i', fontsize=FONTSIZE)
    #title = csv_path.stem.removeprefix('category_transitions_').replace('_', ' ')
    title = " Error Category Transition For Agents"
    ax.set_title(title, pad=15, fontsize=TITLE_FONTSIZE)

    for i in range(n_rows):
        for j in range(n_cols):
            value = data[i, j]
            label = f'{value:.1f}%' if metric == 'percent' else f'{value:,.0f}'
            ax.text(j, i, label, ha='center', va='center', fontsize=FONTSIZE,
                    color='black' if value > maximum * 0.55 else 'white')

    bar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.03)
    bar.set_label('Transition percentage (%)' if metric == 'percent' else 'Number of transitions', fontsize=FONTSIZE)
    ax.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=1)
    ax.tick_params(which='minor', bottom=False, left=False)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ('png', 'pdf'):
        fig.savefig(output_dir / f'{csv_path.stem}.{extension}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Created: {csv_path.stem}.png / .pdf ({metric})')


def main() -> None:
    input_folder = Path('transition_matrices')
    output_folder = Path('transition_heatmaps')

    if not input_folder.is_dir():
        print(f'Input folder does not exist: {input_folder}')
        return

    csv_files = sorted(input_folder.glob('*.csv'))
    output_folder.mkdir(parents=True, exist_ok=True)
    if not csv_files:
        print('No CSV files found.')
        return

    processed = 0
    for csv_file in csv_files:
        if 'percent' not in csv_file.stem.lower() and 'count' not in csv_file.stem.lower():
            print(f'SKIP (not a transition matrix): {csv_file.name}')
            continue
        try:
            make_heatmap(csv_file, output_folder)
            processed += 1
        except (ValueError, KeyError, pd.errors.ParserError) as error:
            print(f'ERROR in {csv_file.name}: {error}')
    print(f'Finished: {processed} heatmaps from {len(csv_files)} CSV files.')


if __name__ == '__main__':
    main()
