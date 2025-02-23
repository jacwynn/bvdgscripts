import pandas as pd
import re

# Read the original CSV
df = pd.read_csv('./BVDG-VET/vet-med-data-feed-filtered.csv', encoding='latin1')

# Define a list of animal names you want to match
animal_names = ['animal', 'dog', 'cat']

# Create a regex pattern from the animal names
animal_pattern = '|'.join(r'\b{}\b'.format(re.escape(animal)) for animal in animal_names)

# Function to check if categories contain animal names
def has_animal_category(categories):
    if pd.isna(categories):
        return False
    return bool(re.search(animal_pattern, categories, re.IGNORECASE))

# Filter the DataFrame to keep only rows with animal categories
df_filtered = df[df['Categories'].apply(has_animal_category)]

# Process the Categories column for the filtered DataFrame
def process_categories(categories):
    if pd.isna(categories):
        return ''
    animal_categories = [cat.strip() for cat in re.split(r'\\|;|,', categories) 
                         if re.search(animal_pattern, cat, re.IGNORECASE)]
    return ', '.join(sorted(set(animal_categories)))

# Apply the processing to the Tags column
df_filtered['Tags'] = df_filtered['Categories'].apply(process_categories)

# Save the filtered DataFrame to a new CSV
df_filtered.to_csv('filtered_animal_categories.csv', index=False, encoding='utf-8')

# Print the number of rows in the original and filtered DataFrames
print("Original CSV rows: {}".format(len(df)))
print("Filtered CSV rows: {}".format(len(df_filtered)))
