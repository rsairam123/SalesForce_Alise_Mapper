import requests
from requests.auth import HTTPBasicAuth

COUCHDB_URL = "http://9.20.195.22:5984"
DB_NAME = "user_aliases"
USERNAME = "admin"
PASSWORD = "admin123"

# ✅ Fetch Primary Account Name using Alias Account Name (returns instead of prints)
def fetch_primary_name(alias_name: str):
    alias_name = alias_name.strip()
    if not alias_name:
        return None

    url = f"{COUCHDB_URL}/{DB_NAME}/_find"
    query = {
        "selector": {"salesforce_name": alias_name},
        "fields": ["user_name"]
    }

    try:
        response = requests.post(url, json=query, auth=HTTPBasicAuth(USERNAME, PASSWORD))
        response.raise_for_status()
        result = response.json()

        docs = result.get("docs", [])
        if not docs:
            return None

        # ✅ Return the primary account name
        primary_name = docs[0].get("user_name", "").strip()
        return primary_name if primary_name else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching primary name for '{alias_name}': {e}")
        return None


# ✅ Run interactively only if this file is executed directly
if __name__ == "__main__":
    alias_account_name = input("Enter the Alias Account Name: ").strip()
    primary = fetch_primary_name(alias_account_name)
    if primary:
        print(f"Primary_Name: {primary}")
    else:
        print("No match found.")
