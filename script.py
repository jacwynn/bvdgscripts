import pandas as pd
from datetime import datetime

# Get the current date and time
current_datetime = datetime.now()

# Load your CSV
df = pd.read_csv('./BVDG-VET/vet-med-data-feed.csv')
# df = pd.read_csv('./BVDG-VET/best-sellers-vet-med-feed.csv')

df['Handle'] = df['Description'].str.replace(' ', '-').str.replace('/', '-') + '-' + df['Item'].str.replace(' ', '-')
df['Title'] = df['Description']
df['Description'] = df['ListOfSpecs']
df['Vendor'] = 'BVDandG'
df['Type'] = df['Item_Type'].str.split(': ').str[1]
df['Tags'] = df['Categories'].fillna('').str.replace(r'\\|;', ', ').str.split(', ').apply(lambda x: ', '.join(sorted(set(x)))).str.strip(', ')
df['Published'] = 'TRUE'
df['Variant SKU'] = df['Item']
df['Variant Grams'] = df['Weight']
df['Variant Inventory Tracker'] = 'shopify'
df['Variant Inventory Qty'] = df['Qty_Avail']

# df['Variant Price'] = df['Price'] - I don't think we need a price at this point
df['Variant Compare At Price'] = df['MSRP']

image_columns = ['Image{}Link'.format(i) for i in range(1, 10)]
df['Image Src'] = df[image_columns].apply(lambda x: '; '.join(x.dropna().astype(str)), axis=1)
# df['base_image'] = df['base_image'].apply(lambda x: 'https://google.com' + str(x))

shopify_columns = [
    'Handle', 'Title', 'Description', 'Vendor', 'Type', 'Tags', 'Published', 'Variant SKU', 'Variant Inventory Tracker', 'Variant Inventory Qty', 'Variant Compare At Price', 'Variant Grams', 'Image Src'
]
df_shopify = df[shopify_columns]

# df_shopify.to_csv('./BVDG-VET/root-data-feed-filtered-{}.csv'.format(current_datetime.strftime('%Y%m%d')), index=False)
df_shopify.to_csv('./BVDG-VET/root-vet-med-data-feed-{}.csv'.format(current_datetime.strftime('%Y%m%d')), index=False)
