import pandas as pd
from datetime import datetime
import sys

def run(input_path):
    """
    Transform raw vendor feed into Shopify root format.

    Args:
        input_path: path to raw vendor CSV

    Returns:
        path to output CSV
    """
    try:
        df = pd.read_csv(input_path, encoding='latin1')
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    except Exception as e:
        raise ValueError(f"Error reading input file: {e}")

    print(f"Processing {len(df)} rows...")

    df['Handle'] = df['Description'].str.replace(' ', '-').str.replace('/', '-') + '-' + df['Item'].str.replace(' ', '-')
    df['Title'] = df['Description']
    df['Description'] = df['ListOfSpecs'] + '|Average Weight: ' + df['Weight'].astype(str) + 'GM'
    df['Vendor'] = 'BVDandG'
    df['Type'] = df['Item_Type'].str.split(': ').str[1]

    specs_tags = df['ListOfSpecs'].fillna('').str.split('|').apply(
        lambda x: [item.split(':')[1].strip() if ':' in item else item.strip() for item in x]
    )
    df['Tags'] = df.apply(
        lambda row: ', '.join(sorted(set(
            (row['Categories'].replace(';', ',').replace('\\', ',').split(',') if pd.notna(row['Categories']) else []) +
            (specs_tags.loc[row.name] if isinstance(specs_tags.loc[row.name], list) else [])
        ))).strip(', '),
        axis=1
    )

    df['Published'] = 'TRUE'
    df['Variant SKU'] = df['Item']
    df['Variant Grams'] = df['Weight']
    df['Variant Inventory Tracker'] = 'shopify'
    df['Variant Inventory Qty'] = df['Qty_Avail']
    df['Variant Compare At Price'] = df['MSRP']

    image_columns = ['Image{}Link'.format(i) for i in range(1, 10)]
    df['Image Src'] = df[image_columns].apply(lambda x: '; '.join(x.dropna().astype(str)), axis=1)

    shopify_columns = [
        'Handle', 'Title', 'Description', 'Vendor', 'Type', 'Tags', 'Published', 'Variant SKU',
        'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Compare At Price', 'Variant Grams', 'Image Src'
    ]
    df_shopify = df[shopify_columns]

    current_datetime = datetime.now()
    output_path = './BVDG-VET/root-vet-med-data-feed-{}.csv'.format(current_datetime.strftime('%Y%m%d'))
    df_shopify.to_csv(output_path, index=False)

    print(f"✓ Output: {output_path} ({len(df_shopify)} rows)")
    return output_path


if __name__ == '__main__':
    if len(sys.argv) > 1:
        output = run(sys.argv[1])
        print(f"Done: {output}")
    else:
        # Default behavior for backwards compatibility
        output = run('./BVDG-VET/vet-med-data-feed.csv')
        print(f"Done: {output}")
