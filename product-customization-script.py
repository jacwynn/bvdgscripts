import pandas as pd
import shutil
import os
import re
import numpy as np
import json
from datetime import datetime

def description_to_html(description, sku, size_weight_info):
    # Split the description into key-value pairs
    items = description.split('|')
    key_value_pairs = [item.split(':', 1) for item in items if ':' in item]

    # Define a regex pattern to identify measurement-related entries
    measurement_pattern = re.compile(r'\b(length|width|height|size|mm|cm|in)\b', re.IGNORECASE)

    # Start the HTML string with a div that sets up a grid layout
    html = '<div class="product-information" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;" data-size-weight-info=\'{}\'>'.format(
        size_weight_info.replace("'", "\\'")  # Escape single quotes in the JSON
    )

    html += '<div class="sku">SKU: {}</div>'.format(sku)

   # Loop through key-value pairs and add them to the HTML string
    for key, value in key_value_pairs:
        # Check if the key or value contains measurement-related terms
        if not measurement_pattern.search(key) and not measurement_pattern.search(value):
            combined = '{}: {}'.format(key.strip().replace("_", " "), value.strip())
            # Skip rendering if it's an average weight
            if 'average weight' not in key.lower():
                html += '<div>{}</div>'.format(combined)

    html += '<div class="average-weight"></div>'


    # Close the div
    html += '</div>'
    return html

def create_custom_metafields(df):
    """
    Creates custom metafield columns based on the Description field.
    Each specification in the Description becomes a custom metafield.
    """
    def parse_description(description):
        if pd.isna(description):
            return {}
        items = description.split('|')
        specs = {}
        
        # Define material-related patterns
        material_patterns = {
            'material_primary': r'(?:material|metal|primary)\s*:\s*primary\s*:\s*([^,]+)',
            'material_primary_color': r'(?:color|colour)\s*:\s*([^,]+)',
            'material_primary_purity': r'(?:purity|karat|kt|k)\s*:\s*([^,]+)'
        }
        
        # Process each item
        for item in items:
            if ':' in item:
                key, value = item.split(':', 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                
                # Handle material-related fields
                if 'material' in key or 'metal' in key:
                    for field, pattern in material_patterns.items():
                        if re.search(pattern, item, re.IGNORECASE):
                            specs[field] = re.search(pattern, item, re.IGNORECASE).group(1).strip()
                
                # Handle other fields
                specs[key] = value
        
        return specs

    # Parse all descriptions
    specs_list = df['Description'].apply(parse_description)
    
    # Define all required metafields
    required_metafields = [
        'stone_type', 'chain_type', 'material_primary_color', 'material_primary_purity',
        'material_primary', 'clasp_connector', 'stone_color', 'stone_weight',
        'stone_shape', 'earring_type', 'earring_closure', 'plating',
        'plating_color', 'stone_clarity', 'stone_creation_method',
        'head_type', 'finish', 'gender', 'coating', 'feature',
        'stone_treatment', 'average_weight', 'weight'
    ]
    
    # Create metafield columns for each specification
    for key in required_metafields:
        # Create the metafield column name
        metafield_col = 'Metafield: custom.' + key + ' [single_line_text_field]'
        
        # Add the column to the dataframe
        df[metafield_col] = specs_list.apply(lambda x: x.get(key, ''))
    
    # Copy average_weight value to weight
    df['Metafield: custom.weight [single_line_text_field]'] = df['Metafield: custom.average_weight [single_line_text_field]']
    
    return df

# Get the current date and time
current_datetime = datetime.now()

product_category = 'pendant-and-charms' # update this based on the category of the data feed (i.e "pendant-and-charms", "bracelets", "earrings", "necklaces", "chains", "anklets", "rings" etc)

# Load your CSV
csv_file_path = './BVDG-VET/{}-product-feed.csv'.format(product_category)
df = pd.read_csv(csv_file_path)
# Regex pattern that removes the measurements from the handle
remove_inch_and_mm_pattern = re.compile(r"\d+\.?\d*-?in-|\d*-?inch-|\d+\.?\d*mm-|\.+")
remove_measurements_from_title_pattern = re.compile(r'\d*\.?\d+\s*(inch|in|mm)')

# Extract the last segment of the size as it represents the Size (length) product option
last_part = df['Handle'].str.split('-').str[-1]
last_part_number = pd.to_numeric(last_part, errors='coerce')

# Extract the mm from the handle to use for Size (millimeter) product option
mm_size = df['Handle'].str.extract(r'(\d*\.?\d+mm)')[0]

# TODO: update Hanle to account for names with apostrophes (i.e "Children's")
df['Handle'] = df['Handle'].apply(lambda x: '-'.join(x.split('-')[:-1]))
df['Handle'] = df['Handle'] = df['Handle'].replace(remove_inch_and_mm_pattern, "", regex=True)

df['Title'] = df['Title'].replace(remove_measurements_from_title_pattern, "", regex=True)
# Remove extra whitespaces and trim the title
df['Title'] = df['Title'].replace(r'\s+', ' ', regex=True).str.strip()

# df['Body HTML'] = df['Description'].apply(description_to_html) --- we no longer need this
# df['Body HTML'] = df.apply(lambda row: description_to_html(row['Description'], row['Variant SKU']), axis=1)

#df['Vendor'] = 'Quality Gold' # This means the product is completed and ready to import #Only set if importing non-vet med products
df['Vendor'] = df['Vendor'].apply(lambda x: x + ' - Vet Medicine' if x else 'Vet Medicine') # Only set this if importing vet med related products
df['Type'] = df['Type']
df['Tags'] = df['Tags']
# df['Option1 Name'] = 'Size (Length)'
# df['Option1 Value'] = last_part_number.astype(int).astype(str) + 'in'
df['last_part_number'] = last_part_number
df['Option1 Name'] = df.apply(lambda row: '' if pd.isna(row['last_part_number']) else 'Size (Length)', axis=1)
df['Option1 Value'] = last_part_number.apply(lambda x: str(int(x)) + 'in' if np.isfinite(x) else '')
df['mm_size'] = mm_size
df['Option2 Name'] = df.apply(lambda row: '' if pd.isna(row['mm_size']) else 'Size (Width)', axis=1)
df['Option2 Value'] = mm_size
df['Variant SKU'] = df['Variant SKU']
df['Variant Grams'] = df['Variant Grams']
df['Variant Inventory Tracker'] = 'shopify'
df['Variant Inventory Qty'] = df['Variant Inventory Qty']

## Possible come back to this if new calculation doesn't work as expected
# df['Variant Price'] = pd.to_numeric(df['Variant Price'], errors='coerce') * 4 #List price
# df['Variant Compare At Price'] = pd.to_numeric(df['Variant Compare At Price'], errors='coerce') * 4 #MSRP

df['Variant Compare At Price'] = pd.to_numeric(df['Variant Compare At Price'], errors='coerce')
df['Variant Compare At Price'] = df['Variant Compare At Price']
df['Variant Price'] = df['Variant Compare At Price'] * 0.7 # 70% of MSRP (30% discount)

df['Variant Price'] = df['Variant Price'].round(2)
df['Variant Compare At Price'] = df['Variant Compare At Price'].round(2)

df['Image Src'] = df['Image Src']

# Add this line after loading the CSV and before creating df_shopify
df = create_custom_metafields(df)

# Update shopify_columns to include metafield columns
metafield_columns = [col for col in df.columns if col.startswith('Metafield:')]
shopify_columns = [
    'Handle', 'Title', 'Body HTML', 'Vendor', 'Type', 'Tags', 'Published', 'Variant SKU', 'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Compare At Price', 'Variant Price', 'Variant Grams', 'Image Src', 'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value'
]
shopify_columns.extend(metafield_columns)

# Before creating df_shopify
df['temp_weight'] = df['Metafield: custom.average_weight [single_line_text_field]'].str.replace('GM', '').str.strip()

# Extract the base SKU (everything before the last hyphen)
df['base_sku'] = df['Variant SKU'].str.rsplit('-', 1).str[0]

# Create a dictionary for each base SKU where length is key and weight is value
def create_size_weight_dict(group):
    # Create a dictionary with sorted keys to ensure consistent ordering
    size_weight_dict = {}
    for _, row in group.iterrows():
        size = row['Option1 Value']
        weight = row['temp_weight']
        if pd.notna(size) and pd.notna(weight):  # Only add if both size and weight are valid
            size_weight_dict[size] = weight
    
    # Sort the dictionary by size to ensure consistent ordering
    return dict(
        sorted(
            ((k, v) for k, v in size_weight_dict.items() if k and k.replace('in', '').strip()),
            key=lambda x: float(x[0].replace('in', ''))
        )
    )

# Group by base SKU and create the JSON object
weight_by_sku = df.groupby('base_sku').apply(create_size_weight_dict).reset_index()
weight_by_sku.columns = ['base_sku', 'size_weight_dict']

# Convert the dictionary to a JSON string, ensuring consistent formatting
weight_by_sku['size_weight_info'] = weight_by_sku['size_weight_dict'].apply(
    lambda x: json.dumps(x, sort_keys=True)
)

# Merge the collected weights back to the original dataframe
df = df.merge(weight_by_sku[['base_sku', 'size_weight_info']], on='base_sku', how='left')

# Get the first description for each base SKU to ensure consistency
base_descriptions = df.groupby('base_sku')['Description'].first().reset_index()
df = df.merge(base_descriptions, on='base_sku', how='left', suffixes=('', '_base'))

# Update the Body HTML generation to include size-weight info
df['Body HTML'] = df.apply(
    lambda row: description_to_html(
        row['Description_base'],
        row['base_sku'],
        row['size_weight_info']
    ), 
    axis=1
)

# Clean up temporary columns
df = df.drop(['temp_weight', 'base_sku', 'size_weight_info', 'Description_base'], axis=1)

df_shopify = df[shopify_columns]

df_shopify.to_csv('./BVDG-VET/ready-to-import/updated-shopify_import-product-feed-{}-{}.csv'.format(product_category, current_datetime.strftime('%Y%m%d')), index=False)


destination_folder = './BVDG-VET/processed-imports/'
if not os.path.exists(destination_folder):
    os.makedirs(destination_folder)

file_name = os.path.basename(csv_file_path)

destination_path = os.path.join(destination_folder, file_name)

try:
    shutil.move(csv_file_path, destination_path)
    print("The updated shopify file can be found in the ready-to-import folder.")
    print("The file was successfully parsed and moved to the process-imports folder.")
except OSError as e:
    print("Error")

