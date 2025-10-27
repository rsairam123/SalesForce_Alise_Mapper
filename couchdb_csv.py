import csv
import couchdb

COUCHDB_URL = "http://admin:21951a05g1@127.0.0.1:5984/"
DB_NAME = "user_aliases"
CSV_FILE = "AccountMapping.csv"

couch = couchdb.Server(COUCHDB_URL)
if DB_NAME in couch:
    db = couch[DB_NAME]
else:
    db = couch.create(DB_NAME)

def read_csv_safely(file_path):
    """Try to read the CSV with UTF-8; fallback to ISO-8859-1 if needed."""
    try:
        f = open(file_path, newline='', encoding='utf-8')
        csv.Sniffer().sniff(f.read(1024))  # test encoding
        f.seek(0)
        return f, csv.DictReader(f)
    except UnicodeDecodeError:
        print("⚠️ UTF-8 decode failed, retrying with ISO-8859-1 encoding...")
        f = open(file_path, newline='', encoding='ISO-8859-1')
        return f, csv.DictReader(f)

file, reader = read_csv_safely(CSV_FILE)
count = 0

for row in reader:
    user_name = row.get("Account Name", "").strip()
    salesforce_name = row.get("Salesforce Account Name", "").strip()

    if not user_name or not salesforce_name:
        print(f"⚠️ Skipping invalid row: {row}")
        continue

    existing_doc = None
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("user_name", "").lower() == user_name.lower():
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

file.close()
print(f"✅ Successfully uploaded {count} records to CouchDB '{DB_NAME}'!")
