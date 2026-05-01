import pandas as pd
import sys

def run(input_path):
    """
    Split root feed by Type column into category-specific files.
    Only processes: pendant-and-charms, bracelets, earrings, necklaces, chains, anklets, rings

    Args:
        input_path: path to root-vet-med-data-feed-*.csv

    Returns:
        dict mapping category name to file path
    """
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Error reading input file: {e}")

    if 'Type' not in df.columns:
        raise ValueError("Input CSV must have a 'Type' column")

    # Only include these categories
    allowed_categories = ['pendants-&-charms', 'bracelets', 'earrings', 'necklaces', 'chains', 'anklets', 'rings']

    print(f"Splitting {len(df)} rows by Type column...")
    print(f"Processing categories: {', '.join(allowed_categories)}\n")

    # Get unique types that match allowed categories (case-insensitive)
    categories = []
    for cat in df['Type'].dropna().unique():
        cat_slug = str(cat).lower().replace(' ', '-').replace('/', '-')
        if cat_slug in allowed_categories:
            categories.append(cat)

    categories = sorted(categories)

    output_files = {}

    print(f"\nFound {len(categories)} categories:")
    for category in categories:
        df_category = df[df['Type'] == category]

        # Slugify category name: lowercase, replace spaces with hyphens
        category_slug = str(category).lower().replace(' ', '-').replace('/', '-')
        output_path = f'./BVDG-VET/{category_slug}-product-feed.csv'

        df_category.to_csv(output_path, index=False)
        output_files[category] = output_path

        print(f"  ✓ {category_slug}: {len(df_category)} rows → {output_path}")

    print(f"\n✓ Created {len(output_files)} category files\n")
    return output_files


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python split.py <root_feed.csv>")
        sys.exit(1)

    output = run(sys.argv[1])
    print("Done!")
    for cat, path in output.items():
        print(f"  {cat}: {path}")
