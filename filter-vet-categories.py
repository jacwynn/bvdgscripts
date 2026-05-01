import pandas as pd
import re
import sys
from datetime import datetime

def run(input_path):
    """
    Filter raw vendor feed to only animal-related products.

    Args:
        input_path: path to raw vet-med CSV

    Returns:
        path to filtered CSV with only animal products
    """
    try:
        df = pd.read_csv(input_path, encoding='latin1')
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Error reading input file: {e}")

    if 'Categories' not in df.columns:
        raise ValueError("Input CSV must have a 'Categories' column")

    print(f"Filtering {len(df)} rows for animal-related products...")

    # Animal keywords to match
    animal_names = [
        'animal', 'sea life', 'amphibians', 'reptiles', 'insects', 'arachnids',
        'seashore', 'dog', 'dogs', 'cat', 'cats', 'bird', 'dolphin', 'butterfly',
        'snake', 'ladybug', 'dragonfly', 'lizard', 'turtle', 'bear', 'salmon',
        'horse', 'frog', 'fish'
    ]

    animal_pattern = '|'.join(r'\b{}\b'.format(re.escape(animal)) for animal in animal_names)

    def has_animal_category(categories):
        if pd.isna(categories):
            return False
        return bool(re.search(animal_pattern, categories, re.IGNORECASE))

    df_filtered = df[df['Categories'].apply(has_animal_category)]

    def process_categories(categories):
        if pd.isna(categories):
            return ''
        animal_categories = [
            cat.strip() for cat in re.split(r'[\\|;,]', categories)
            if re.search(animal_pattern, cat, re.IGNORECASE)
        ]
        return ', '.join(sorted(set(animal_categories)))

    df_filtered = df_filtered.copy()
    df_filtered['Tags'] = df_filtered['Categories'].apply(process_categories)

    # Write output with date stamp
    current_datetime = datetime.now()
    output_path = './BVDG-VET/filtered-vet-categories-{}.csv'.format(
        current_datetime.strftime('%Y%m%d')
    )

    df_filtered.to_csv(output_path, index=False, encoding='utf-8')

    print(f"✓ Filtered {len(df_filtered)} rows out of {len(df)} original")
    print(f"✓ Output: {output_path}")

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python filter-vet-categories.py <input_csv>")
        sys.exit(1)

    output = run(sys.argv[1])
    print(f"Done: {output}")
