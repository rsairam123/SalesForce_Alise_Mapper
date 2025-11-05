import pandas as pd
import time
from Fetching_Primary_account import fetch_primary_name

# Path to your Excel file
INPUT_FILE = "AccountMapping.xlsx"

# Load Excel file
df = pd.read_excel(INPUT_FILE)



# Ensure there’s a column named 'salesforce account name'
if 'Salesforce Account Name' not in df.columns:
    raise KeyError("The Excel file must contain a column named 'salesforce account name'")

# Loop through each alias and test fetch
for alias_name in df['Salesforce Account Name']:
    print(f"\n🔹 Testing alias: {alias_name}")
    fetch_primary_name(alias_name)
    time.sleep(0.5) 
