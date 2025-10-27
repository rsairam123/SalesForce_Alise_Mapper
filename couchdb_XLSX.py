import pandas as pd
import couchdb

# ------------------------------
# CouchDB Connection Settings
# ------------------------------
COUCHDB_URL = "http://admin:21951a05g1@127.0.0.1:5984/"
DB_NAME = "user_aliases"
EXCEL_FILE = "AccountMapping.xlsx"

# ------------------------------
# Connect to CouchDB
# ------------------------------
couch = couchdb.Server(COUCHDB_URL)
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)

# ------------------------------
# Read Excel safely (preserve all special chars)
# ------------------------------
try:
    df = pd.read_excel(EXCEL_FILE, dtype=str)  # Read everything as string
    df.fillna("", inplace=True)  # Replace NaN with empty string
except Exception as e:
    print(f"❌ Error reading Excel file: {e}")
    exit()

count = 0
for _, row in df.iterrows():
    user_name = str(row.get("Account Name", "")).strip()
    salesforce_name = str(row.get("Salesforce Account Name", "")).strip()

    if not user_name or not salesforce_name:
        print(f"⚠️ Skipping invalid row: {row.to_dict()}")
        continue

    # ------------------------------
    # Check if user_name already exists
    # ------------------------------
    existing_doc = None
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("user_name", "").strip().lower() == user_name.lower():
            existing_doc = doc
            break

    if existing_doc:
        current_sf = existing_doc.get("salesforce_name")
        if current_sf and current_sf.lower() != salesforce_name.lower():
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

print(f"✅ Successfully uploaded {count} records to CouchDB '{DB_NAME}'!")
