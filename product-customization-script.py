import pandas as pd
import shutil
import os
import re
import numpy as np
from datetime import datetime

def description_to_html(description, sku):
    # Split the description into key-value pairs
    items = description.split('|')
    key_value_pairs = [item.split(':', 1) for item in items if ':' in item]

    # Define a regex pattern to identify measurement-related entries
    measurement_pattern = re.compile(r'\b(length|width|height|size|mm|cm|in)\b', re.IGNORECASE)

    # Start the HTML string with a div that sets up a grid layout
    html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">'

    html += '<div class="sku">SKU: {}</div>'.format(sku);

    # Loop through key-value pairs and add them to the HTML string
    for key, value in key_value_pairs:
        # Check if the key or value contains measurement-related terms
        if not measurement_pattern.search(key) and not measurement_pattern.search(value):
            combined = '{}: {}'.format(key.strip(), value.strip())
            html += '<div>{}</div>'.format(combined)

    # Close the div
    html += '</div>'
    return html

# Get the current date and time
current_datetime = datetime.now()

product_category = 'rings' # update this based on the category of the data feed (i.e "pendant-and-charms", "bracelets", "anklets", etc)
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
df['Body HTML'] = df.apply(lambda row: description_to_html(row['Description'], row['Variant SKU']), axis=1)

df['Vendor'] = 'Quality Gold' # This means the product is completed and ready to import
df['Vendor'] = df['Vendor'].apply(lambda x: x + ' - Vet Medicine' if x else 'Vet Medicine') # Only set this if importing vet med related products
df['Type'] = df['Type']
df['Tags'] = df['Tags']
# df['Option1 Name'] = 'Size (Length)'
# df['Option1 Value'] = last_part_number.astype(int).astype(str) + 'in'
df['last_part_number'] = last_part_number
df['Option1 Name'] = df.apply(lambda row: '' if pd.isna(row['last_part_number']) else 'Size (Length)', axis=1)
df['Option1 Value'] = last_part_number.apply(lambda x: str(int(x)) + 'in' if np.isfinite(x) else '')
df['mm_size'] = mm_size
df['Option2 Name'] = df.apply(lambda row: '' if pd.isna(row['mm_size']) else 'Size (Millimeter)', axis=1)
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

shopify_columns = [
    'Handle', 'Title', 'Body HTML', 'Vendor', 'Type', 'Tags', 'Published', 'Variant SKU', 'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Compare At Price', 'Variant Price', 'Variant Grams', 'Image Src', 'Option1 Name', 'Option1 Value', 'Option2 Name', 'Option2 Value'
]
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

