#!/usr/bin/env python3
"""
BVDG-VET Shopify Import Pipeline

Orchestrates the full product feed transformation:
  Stage 1 (optional): Filter to animal products only
  Stage 2: Transform raw feed to Shopify root format
  Stage 3: Split root by category
  Stage 4: Customize each category
  Stage 5: Batch output for Matrixify (5K rows per file)

Usage:
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --animals-only
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --vet-medicine
"""

import argparse
import os
import sys
import importlib.util
from datetime import datetime

from script import run as transform_feed
from split import run as split_by_category

# Import modules with hyphens using importlib
spec = importlib.util.spec_from_file_location("product_customization_script", "./product-customization-script.py")
product_customization_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(product_customization_script)
customize_category = product_customization_script.run

spec = importlib.util.spec_from_file_location("filter_vet_categories", "./filter-vet-categories.py")
filter_vet_categories = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filter_vet_categories)
filter_animals = filter_vet_categories.run


def batch_for_matrixify(output_files, batch_size=5000):
    """
    Combine and batch all category CSVs for Matrixify (5K rows per file).

    Args:
        output_files: list of category CSV paths
        batch_size: rows per batch (default 5000 for Matrixify Basic)

    Returns:
        list of batch file paths
    """
    import pandas as pd

    print("\n=== Stage 5: Batch for Matrixify ===")

    if not output_files:
        print("No files to batch")
        return []

    # Read and combine all category files
    dfs = []
    for path in output_files:
        if os.path.exists(path):
            try:
                dfs.append(pd.read_csv(path))
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}")

    if not dfs:
        raise ValueError("No valid output files to batch")

    combined_df = pd.concat(dfs, ignore_index=True)
    total_rows = len(combined_df)

    print(f"Combined {len(dfs)} files: {total_rows} total rows")

    # Split into batches
    current_datetime = datetime.now()
    batch_dir = f'./BVDG-VET/ready-to-import/{current_datetime.strftime("%Y%m%d")}'
    os.makedirs(batch_dir, exist_ok=True)

    batch_files = []
    batch_num = 1
    start_row = 0

    while start_row < total_rows:
        end_row = min(start_row + batch_size, total_rows)
        batch_df = combined_df.iloc[start_row:end_row]

        batch_path = os.path.join(batch_dir, f'batch_{batch_num}.csv')
        batch_df.to_csv(batch_path, index=False)
        batch_files.append(batch_path)

        print(f"  ✓ Batch {batch_num}: rows {start_row+1}–{end_row} ({len(batch_df)} rows)")
        batch_num += 1
        start_row = end_row

    print(f"✓ Created {len(batch_files)} batch files\n")
    return batch_files


def main():
    parser = argparse.ArgumentParser(
        description='BVDG-VET Shopify Import Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --animals-only
  python pipeline.py --input ./BVDG-VET/vet-med-data-feed.csv --vet-medicine
        '''
    )
    parser.add_argument('--input', required=True, help='Path to raw vendor feed CSV')
    parser.add_argument('--animals-only', action='store_true',
                       help='Filter to animal-related products only')
    parser.add_argument('--vet-medicine', action='store_true',
                       help='Add " - Vet Medicine" vendor suffix')

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    try:
        print("=" * 70)
        print("BVDG-VET SHOPIFY IMPORT PIPELINE")
        print("=" * 70)

        input_feed = args.input

        # Stage 1: Optional animal filter
        if args.animals_only:
            print("\n=== Stage 1: Filter to Animal Products ===")
            input_feed = filter_animals(args.input)

        # Stage 2: Transform
        print("\n=== Stage 2: Transform Raw Feed ===")
        root_csv = transform_feed(input_feed)

        # Stage 3: Split by category
        print("\n=== Stage 3: Split by Category ===")
        category_dict = split_by_category(root_csv)

        if not category_dict:
            print("Error: No category files created")
            sys.exit(1)

        # Get file paths from the dict
        category_files = list(category_dict.values())

        # Stage 4: Customize each category
        print("\n=== Stage 4: Customize Categories ===")
        output_files = []

        # Auto-enable vet_medicine if animals_only is used
        vet_medicine_flag = args.vet_medicine or args.animals_only

        for category_path in sorted(category_files):
            try:
                output = customize_category(category_path, vet_medicine=vet_medicine_flag)
                output_files.append(output)
            except Exception as e:
                print(f"Error processing {category_path}: {e}")
                raise

        if not output_files:
            print("Error: No category files processed")
            sys.exit(1)

        # Stage 5: Batch for Matrixify
        batch_files = batch_for_matrixify(output_files)

        # Summary
        print("=" * 70)
        print("PIPELINE COMPLETE ✓")
        print("=" * 70)
        print(f"Input: {args.input}")
        if args.animals_only:
            print(f"Mode: Animals only")
        if args.vet_medicine:
            print(f"Vendor: Quality Gold - Vet Medicine")
        else:
            print(f"Vendor: Quality Gold")
        print(f"Categories processed: {len(category_files)}")
        print(f"Matrixify batches: {len(batch_files)}")
        print(f"\nBatch files ready in: {os.path.dirname(batch_files[0]) if batch_files else 'N/A'}")
        print("=" * 70 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
