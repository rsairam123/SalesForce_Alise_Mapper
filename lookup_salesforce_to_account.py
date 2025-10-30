import sys
import requests
from requests.auth import HTTPBasicAuth

COUCHDB_URL = "http://127.0.0.1:5984/"
DB_NAME = "user_aliases"
USERNAME = "admin"
PASSWORD = "21951a05g1"
TIMEOUT = 30.0
a = ""


def ensure_full_commit():
    """Force CouchDB to commit recent writes."""
    url = f"{COUCHDB_URL}/_ensure_full_commit"
    try:
        r = requests.post(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=TIMEOUT)
        if r.status_code == 201:
            print("✅ CouchDB full commit ensured.")
        else:
            print(f"⚠️ Commit request returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"⚠️ Commit failed: {e}")


def fetch_all_docs():
    """Fetch all documents including newly added or updated ones."""
    url = f"{COUCHDB_URL}/{DB_NAME}/_all_docs?include_docs=true"
    r = requests.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=TIMEOUT)
    r.raise_for_status()
    return [row["doc"] for row in r.json().get("rows", []) if "doc" in row]


def fetch_aliases_by_salesforce(sf_name: str):
    """Find documents where salesforce_name exactly matches the input (case-sensitive)."""
    if not sf_name.strip():
        return []

    sf_name_norm = sf_name.strip()

    # Fetch all docs live (ensures latest data)
    docs = fetch_all_docs()

    print("\n🗂️ All documents in DB:")
    for d in docs:
        print(f"- salesforce_name: {d.get('salesforce_name')} | user_name: {d.get('user_name')}")

    # Exact case-sensitive match
    aliases = [
        d["user_name"]
        for d in docs
        if d.get("salesforce_name", "").strip() == sf_name_norm
    ]

    print(f"\n🔍 [DEBUG] Matches for '{sf_name_norm}': {aliases}")
    return aliases


def main():
    if len(sys.argv) > 1:
        sf_input = " ".join(sys.argv[1:])
    else:
        sf_input = input("Enter Salesforce Account Name for lookup: ").strip()

    if not sf_input:
        print("Salesforce Account Name is required.")
        sys.exit(1)

    ensure_full_commit()

    try:
        results = fetch_aliases_by_salesforce(sf_input)
    except requests.HTTPError as http_err:
        print(f"HTTP error: {http_err}")
        sys.exit(2)
    except Exception as err:
        print(f"Error: {err}")
        sys.exit(3)

    if not results:
        print(f"\n No Account Name mapping found for Salesforce Account Name: '{sf_input}'.")
    else:
        print("\n✅ Mapped Account Name(s):")
        for name in results:
            print(f"- {name}")

if __name__ == "__main__":
    main()
