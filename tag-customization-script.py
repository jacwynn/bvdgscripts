import pandas as pd
from datetime import datetime

# Get the current date and time
current_datetime = datetime.now()

# Load your CSV
df = pd.read_csv('./BVDG-VET/tags-vet-med.csv')

df['Handle'] = df['Handle']
df['Title'] = df['Title']
df['Tags'] = df['Tags'].apply(lambda x: x + ', Vet Med' if x else 'Vet Med')
df['Vendor'] = df['Vendor'].apply(lambda x: x + ' - Vet Medicine' if x else 'Vet Medicine')

shopify_columns = [
    'Handle', 'Title', 'Tags', 'Vendor'
]
df_shopify = df[shopify_columns]

df_shopify.to_csv('./BVDG-VET/updated-tags-vet-med-{}.csv'.format(current_datetime.strftime('%Y%m%d')), index=False)