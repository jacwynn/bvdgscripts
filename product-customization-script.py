import pandas as pd
import shutil
import os
import re
import numpy as np
import json
import sys
from datetime import datetime

def description_to_html(description, sku, size_weight_info):
    if pd.isna(description):
        description = ''

    items = description.split('|')
    key_value_pairs = [item.split(':', 1) for item in items if ':' in item]

    measurement_pattern = re.compile(r'\b(length|width|height|size|mm|cm|in)\b', re.IGNORECASE)

    html = '<div class="product-information" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;" data-size-weight-info=\'{}\'>'.format(
        size_weight_info.replace("'", "\\'")
    )

    html += '<div class="sku">SKU: {}</div>'.format(sku)

    for key, value in key_value_pairs:
        if not measurement_pattern.search(key) and not measurement_pattern.search(value):
            combined = '{}: {}'.format(key.strip().replace("_", " "), value.strip())
            if 'average weight' not in key.lower():
                html += '<div>{}</div>'.format(combined)

    html += '<div class="average-weight"></div>'
    html += '</div>'
    return html

def create_custom_metafields(df):
    """Creates custom metafield columns based on the Description field."""
    def parse_description(description):
        if pd.isna(description):
            return {}
        items = description.split('|')
        specs = {}

        material_patterns = {
            'material_primary': r'(?:material|metal|primary)\s*:\s*primary\s*:\s*([^,]+)',
            'material_primary_color': r'(?:color|colour)\s*:\s*([^,]+)',
            'material_primary_purity': r'(?:purity|karat|kt|k)\s*:\s*([^,]+)'
        }

        for item in items:
            if ':' in item:
                key, value = item.split(':', 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if 'material' in key or 'metal' in key:
                    for field, pattern in material_patterns.items():
                        if re.search(pattern, item, re.IGNORECASE):
                            specs[field] = re.search(pattern, item, re.IGNORECASE).group(1).strip()

                specs[key] = value

        return specs

    specs_list = df['Description'].apply(parse_description)

    required_metafields = [
        'stone_type', 'chain_type', 'material_primary_color', 'material_primary_purity',
        'material_primary', 'clasp_connector', 'stone_color', 'stone_weight',
        'stone_shape', 'earring_type', 'earring_closure', 'plating',
        'plating_color', 'stone_clarity', 'stone_creation_method',
        'head_type', 'finish', 'gender', 'coating', 'feature',
        'stone_treatment', 'average_weight', 'weight'
    ]

    for key in required_metafields:
        metafield_col = 'Metafield: custom.' + key + ' [single_line_text_field]'
        df[metafield_col] = specs_list.apply(lambda x: x.get(key, ''))

    df['Metafield: custom.weight [single_line_text_field]'] = df['Metafield: custom.average_weight [single_line_text_field]']

    return df

def create_size_weight_dict(group):
    size_weight_dict = {}
    for _, row in group.iterrows():
        size = row['Option1 Value']
        weight = row['temp_weight']
        if pd.notna(size) and pd.notna(weight):
            size_weight_dict[size] = weight

    return dict(
        sorted(
            ((k, v) for k, v in size_weight_dict.items() if k and k.replace('in', '').strip()),
            key=lambda x: float(x[0].replace('in', ''))
        )
    )

def run(input_path, vet_medicine=False):
    """
    Customize products for a specific category and generate Shopify import CSV.

    Args:
        input_path: path to category-specific product feed CSV
        vet_medicine: if True, append ' - Vet Medicine' to vendor

    Returns:
        path to generated updated-shopify_import-product-feed-{category}-{YYYYMMDD}.csv
    """
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Error reading input file: {e}")

    # Extract category from filename
    filename = os.path.basename(input_path)
    if not filename.endswith('-product-feed.csv'):
        raise ValueError(f"Input filename must end with '-product-feed.csv', got: {filename}")

    product_category = filename.replace('-product-feed.csv', '')
    print(f"Customizing category: {product_category}")
    print(f"Processing {len(df)} rows...")

    # Regex patterns - fix: removed |\.+ which was stripping all dots
    remove_inch_and_mm_pattern = re.compile(r"\d+\.?\d*-?in-|\d*-?inch-|\d+\.?\d*mm-")
    remove_measurements_from_title_pattern = re.compile(r'\d*\.?\d+\s*(inch|in|mm)')

    last_part = df['Handle'].str.split('-').str[-1]
    last_part_number = pd.to_numeric(last_part, errors='coerce')
    mm_size = df['Handle'].str.extract(r'(\d*\.?\d+mm)')[0]

    df['Handle'] = df['Handle'].apply(lambda x: '-'.join(x.split('-')[:-1]))
    df['Handle'] = df['Handle'].replace(remove_inch_and_mm_pattern, "", regex=True)

    df['Title'] = df['Title'].replace(remove_measurements_from_title_pattern, "", regex=True)
    df['Title'] = df['Title'].replace(r'\s+', ' ', regex=True).str.strip()

    # Update vendor based on vet_medicine flag
    if vet_medicine:
        df['Vendor'] = 'Quality Gold - Vet Medicine'
    else:
        df['Vendor'] = 'Quality Gold'

    df['last_part_number'] = last_part_number
    df['Option1 Name'] = df.apply(lambda row: '' if pd.isna(row['last_part_number']) else 'Size (Length)', axis=1)
    df['Option1 Value'] = last_part_number.apply(lambda x: str(int(x)) + 'in' if np.isfinite(x) else '')

    df['mm_size'] = mm_size
    df['Option2 Name'] = df.apply(lambda row: '' if pd.isna(row['mm_size']) else 'Size (Width)', axis=1)
    df['Option2 Value'] = mm_size

    df['Variant Inventory Tracker'] = 'shopify'

    df['Variant Compare At Price'] = pd.to_numeric(df['Variant Compare At Price'], errors='coerce')
    df['Variant Price'] = df['Variant Compare At Price'] * 0.7
    df['Variant Price'] = df['Variant Price'].round(2)
    df['Variant Compare At Price'] = df['Variant Compare At Price'].round(2)

    df = create_custom_metafields(df)

    metafield_columns = [col for col in df.columns if col.startswith('Metafield:')]
    shopify_columns = [
        'Handle', 'Title', 'Body HTML', 'Vendor', 'Type', 'Tags', 'Published', 'Variant SKU',
        'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Compare At Price', 'Variant Price',
        'Variant Grams', 'Image Src', 'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value'
    ]
    shopify_columns.extend(metafield_columns)

    df['temp_weight'] = df['Metafield: custom.average_weight [single_line_text_field]'].str.replace('GM', '').str.strip()
    # Extract base SKU (everything before the last hyphen)
    df['base_sku'] = df['Variant SKU'].apply(lambda x: '-'.join(x.split('-')[:-1]) if pd.notna(x) else x)

    weight_by_sku = df.groupby('base_sku', group_keys=False).apply(create_size_weight_dict, include_groups=False).reset_index()
    weight_by_sku.columns = ['base_sku', 'size_weight_dict']

    weight_by_sku['size_weight_info'] = weight_by_sku['size_weight_dict'].apply(
        lambda x: json.dumps(x, sort_keys=True)
    )

    df = df.merge(weight_by_sku[['base_sku', 'size_weight_info']], on='base_sku', how='left')

    base_descriptions = df.groupby('base_sku')['Description'].first().reset_index()
    df = df.merge(base_descriptions, on='base_sku', how='left', suffixes=('', '_base'))

    df['Body HTML'] = df.apply(
        lambda row: description_to_html(
            row['Description_base'],
            row['base_sku'],
            row['size_weight_info']
        ),
        axis=1
    )

    df = df.drop(['temp_weight', 'base_sku', 'size_weight_info', 'Description_base', 'last_part_number', 'mm_size'], axis=1)

    df_shopify = df[shopify_columns]

    # Write output
    current_datetime = datetime.now()
    output_dir = './BVDG-VET/ready-to-import'
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(
        output_dir,
        f'updated-shopify_import-product-feed-{product_category}-{current_datetime.strftime("%Y%m%d")}.csv'
    )
    df_shopify.to_csv(output_path, index=False)

    print(f"✓ Output: {output_path} ({len(df_shopify)} rows)")

    # Move input to archive
    destination_folder = './BVDG-VET/processed-imports/'
    os.makedirs(destination_folder, exist_ok=True)
    destination_path = os.path.join(destination_folder, os.path.basename(input_path))

    try:
        shutil.move(input_path, destination_path)
        print(f"✓ Archived input: {destination_path}")
    except OSError as e:
        print(f"Warning: Error moving input file to archive: {e}")
        raise

    return output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python product-customization-script.py <category_csv> [--vet-medicine]")
        sys.exit(1)

    vet_medicine = '--vet-medicine' in sys.argv
    output = run(sys.argv[1], vet_medicine=vet_medicine)
    print(f"Done: {output}")

