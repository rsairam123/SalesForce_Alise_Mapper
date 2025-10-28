import pandas as pd
import couchdb
import time

# ------------------------------
# CouchDB Connection Settings
# ------------------------------
COUCHDB_URL = "http://admin:admin123@9.20.195.22:5984/"
DB_NAME = "user_aliases"
EXCEL_FILE = "AccountMapping.xlsx"

# ------------------------------
# Connect to CouchDB
# ------------------------------
print("🔗 Connecting to CouchDB...")
couch = couchdb.Server(COUCHDB_URL)
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)
print(f"✅ Connected to database: '{DB_NAME}'")

# ------------------------------
# Read Excel safely (preserve all special chars)
# ------------------------------
try:
    df = pd.read_excel(EXCEL_FILE, dtype=str)  # Read all as string
    df.fillna("", inplace=True)
except Exception as e:
    print(f"❌ Error reading Excel file: {e}")
    exit()

total_rows = len(df)
print(f"📘 Found {total_rows} rows in Excel file.\n")

# ------------------------------
# Upload Data with Progress Updates
# ------------------------------
start_time = time.time()
count = 0
skipped = 0

for i, row in df.iterrows():
    user_name = str(row.get("Account Name", "")).strip()
    salesforce_name = str(row.get("Salesforce Account Name", "")).strip()

    if not user_name or not salesforce_name:
        skipped += 1
        continue

    # Use CouchDB Mango Query for faster lookups
    query = {"selector": {"user_name": {"$eq": user_name}}}
    result = db.find(query)
    existing_doc = next(iter(result), None)

    if existing_doc:
        current_sf = existing_doc.get("salesforce_name", "")
        if current_sf.lower() != salesforce_name.lower():
            conflicts = existing_doc.get("conflicts", [])
            if salesforce_name not in conflicts:
                conflicts.append(salesforce_name)
            existing_doc["conflicts"] = conflicts
        existing_doc["salesforce_name"] = salesforce_name
        db.save(existing_doc)
    else:
        db.save({
            "user_name": user_name,
            "salesforce_name": salesforce_name,
            "conflicts": []
        })
    count += 1

    # Show progress every 10 records or at end
    if count % 10 == 0 or count == total_rows:
        elapsed = time.time() - start_time
        print(f"➡️  Uploaded {count}/{total_rows} records... ({elapsed:.1f}s elapsed)")

# ------------------------------
# Summary
# ------------------------------
elapsed_total = time.time() - start_time
print("\n✅ Upload complete!")
print(f"📊 Total processed: {total_rows}")
print(f"📈 Successfully uploaded: {count}")
print(f"⚠️ Skipped invalid rows: {skipped}")
print(f"⏱️ Total time taken: {elapsed_total:.2f} seconds")
