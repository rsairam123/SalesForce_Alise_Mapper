import os
import re
import pytz
import glob
import shutil
import logging
import smtplib
import requests
import warnings
import subprocess
import pandas as pd
from datetime import datetime
from collections import Counter
from email.message import EmailMessage
from requests.auth import HTTPBasicAuth
# Import the Salesforce->Account alias lookup module

from Fetching_Primary_account import fetch_primary_name

# Setup logging
log_dir = "/Users/Administrator/Desktop/RPA/smart_triage/RPA_Bot/logs"
os.makedirs(log_dir, exist_ok=True)

for old_log in glob.glob(os.path.join(log_dir, "smart_triage_log_*.txt")):
    try:
        os.remove(old_log)
    except Exception as e:
        print(f"Failed to delete old log file {old_log}: {e}")

log_filename = f"smart_triage_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
log_filepath = os.path.join(log_dir, log_filename)

env = os.environ.copy()
env["SMART_TRIAGE_LOG_FILE"] = log_filepath

logging.basicConfig(
    filename=log_filepath,
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

log = logging.getLogger()

# Step 1: Read Excel by index
def read_xlsx(file_path):
    warnings.filterwarnings("ignore")
    return pd.read_excel(file_path, engine="openpyxl", skiprows=1)

# Step 2: Auto-detect ignore words
def build_ignore_words(account_names):
    word_counter = Counter()
    suffix_counter = Counter()
    for name in account_names:
        words = re.split(r'\W+', name.lower())
        word_counter.update(words)
        for word in words[-3:]:
            if word:
                suffix_counter[word] += 1
    total_names = len(account_names)
    ignore_words = set()
    for word, count in word_counter.items():
        if not word:
            continue
        frequency = count / total_names
        if len(word) <= 3 or frequency > 0.4:
            ignore_words.add(word)
    for word, count in suffix_counter.items():
        if count > 2:
            ignore_words.add(word)
    return ignore_words

# Step 3: Clean keywords
def clean_keywords(text, ignore_words):
    words = re.split(r'\W+', text.lower())
    return [word for word in words if word and word not in ignore_words]

# Step 4: Smart account matching (kept for reference but no longer used for final alias mapping)
# The final Account Name will come from CouchDB alias lookup via alias_lookup.fetch_aliases_by_salesforce
# This function can still be used for logging/debug if needed.
def match_account_name_smart(excel_name, couchdb_names, ignore_words):
    excel_keywords = clean_keywords(excel_name, ignore_words)
    if not excel_keywords:
        return [], [], "Skipped (No valid keywords)"
    primary_keyword = excel_keywords[0]
    matched_accounts, keywords_matched = [], []
    match_status = "Skipped (No valid keywords)"
    for couch_name in couchdb_names:
        couch_keywords = clean_keywords(couch_name, ignore_words)
        matched = set(excel_keywords).intersection(couch_keywords)
        if not matched:
            continue
        matched_accounts.append(couch_name)
        keywords_matched.append(list(matched))
        match_status = "Closest Match" if primary_keyword in matched else "Tentative Match"
    if not matched_accounts:
        match_status = "Skipped (No familiar keywords)"
    return matched_accounts, keywords_matched, match_status

# CouchDB utilities
def recreate_db(couchdb_url, db_name, username, password):
    """Deletes and recreates a CouchDB database cleanly."""
    db_url = f"{couchdb_url}/{db_name}"
    response = requests.get(db_url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200:
        print(f"Database '{db_name}' already exists. Deleting for a clean start...")
        delete_response = requests.delete(db_url, auth=HTTPBasicAuth(username, password))
        if delete_response.status_code in (200, 202):
            print(f"Database '{db_name}' deleted successfully.")
        else:
            raise Exception(f"Failed to delete database '{db_name}': {delete_response.status_code}, {delete_response.text}")
    
    create_response = requests.put(db_url, auth=HTTPBasicAuth(username, password))
    if create_response.status_code in (200, 201):
        print(f"Database '{db_name}' recreated successfully.")
    else:
        raise Exception(f"Failed to recreate database '{db_name}': {create_response.status_code}, {create_response.text}")

def create_db_if_not_exists(couchdb_url, db_name, username, password):
    url = f"{couchdb_url}/{db_name}"
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    if response.status_code == 404:
        requests.put(url, auth=HTTPBasicAuth(username, password))
    elif response.status_code != 200:
        log.error(f"Error accessing DB: {response.text}")

def fetch_all_account_names(couchdb_url, username, password):
    url = f"{couchdb_url}/per_account_distribution_sheet_master/_all_docs?include_docs=true"
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    account_names = []
    if response.status_code == 200:
        for row in response.json()['rows']:
            doc = row.get('doc', {})
            name = doc.get('Account Name', '').strip()
            if name:
                account_names.append(name)
    return account_names

def check_case_exists(couchdb_url, db_name, username, password, case_number):
    url = f"{couchdb_url}/{db_name}/_find"
    query = {"selector": {"Case Number": case_number}}
    response = requests.post(url, json=query, auth=HTTPBasicAuth(username, password))
    if response.status_code == 200 and response.json()['docs']:
        return response.json()['docs'][0]
    return None

def insert_or_update_record(couchdb_url, db_name, username, password, record):
    case_number = record.get('Case Number')
    existing = check_case_exists(couchdb_url, db_name, username, password, case_number)
    if existing:
        record.update({"_rev": existing["_rev"], "_id": existing["_id"]})
        url = f"{couchdb_url}/{db_name}/{existing['_id']}"
        requests.put(url, json=record, auth=HTTPBasicAuth(username, password))
        log.info(f"Updated: {case_number}")
    else:
        url = f"{couchdb_url}/{db_name}"
        requests.post(url, json=record, auth=HTTPBasicAuth(username, password))
        log.info(f"Inserted: {case_number}")

def insert_record(couchdb_url, db_name, username, password, record):
    """Inserts a new record (no updates)."""
    url = f"{couchdb_url}/{db_name}"
    response = requests.post(url, json=record, auth=HTTPBasicAuth(username, password))
    if response.status_code in (200, 201):
        print(f"Inserted: {record.get('Case Number')}")
    else:
        print(f"Failed to insert {record.get('Case Number')}: {response.status_code} {response.text}")

def process_files(folder_path, couchdb_url, db_name, username, password):
    #create_db_if_not_exists(couchdb_url, db_name, username, password)
    recreate_db(couchdb_url, db_name, username, password)
    couch_account_names = fetch_all_account_names(couchdb_url, username, password)
    ignore_words = build_ignore_words(couch_account_names)
    #print(f"Auto-detected ignore words: {sorted(ignore_words)}")
    archive_dir = os.path.join(folder_path, "Processed RPA case files")
    os.makedirs(archive_dir, exist_ok=True)

    found_files = [f for f in os.listdir(folder_path) if f.endswith(".xlsx") and not f.startswith("~$")]
    if not found_files:
        print("No RPA extracted files in the target folder to process.")
        return

    for file_name in found_files:
        if not re.match(r"SCBN New PER-[\w\- ]+\.xlsx$", file_name, re.IGNORECASE):
            #log.warning(f"Skipping unmatched pattern file: {file_name}")
            continue

        log.info(f"Processing case file: {file_name}")
        file_path = os.path.join(folder_path, file_name)
        file_processed_successfully = True

        try:
            df = read_xlsx(file_path)
            for index, row in df.iterrows():
                try:
                    case_number = str(row.iloc[11]).strip()
                    alias_account_name = str(row.iloc[1]).strip()
                    contact_name = str(row.iloc[10]).strip()
                    subject = str(row.iloc[2]).strip()
                    status = str(row.iloc[9]).strip()
                    date_opened = str(row.iloc[3]).strip()
                    mission_team = str(row.iloc[13]).strip()
                    severity = str(row.iloc[12]).strip()

                    log.info(f"Looking up primary name for Salesforce Account Name: '{alias_account_name}'")

                    # Use the Fetching_Primary_account.fetch_primary_name with the alias_account_name from Excel
                    try:
                        primary_account_name = fetch_primary_name(alias_account_name)  # expected to return/print the primary name
                    except Exception as err:
                        log.error(f"Primary name fetch error for '{alias_account_name}': {err}")
                        primary_account_name = None

                    if not primary_account_name or not str(primary_account_name).strip():
                        log.warning(f"No primary name found for Salesforce Account Name: '{alias_account_name}'. Skipping row.")
                        continue

                    log.info(f"Primary name resolved. Using Account Name: '{primary_account_name}' from Salesforce '{alias_account_name}'")

                    cleaned_record = {
                        "Case Number": case_number,
                        "Account Name": primary_account_name,
                        "Subject": subject,
                        "Severity": severity,
                        "Contact Name": contact_name,
                        "Date/Time Opened": date_opened,
                        "Mission Team": mission_team,
                        "Status": status,
                        "Match Info": {
                            "Matched Accounts": primary_account_name,
                            "Match Type": "Exact Match"
                        }
                    }
                    


                    if primary_account_name != "Sterling Commerce, Inc. - Single Sign On - EMEA":
                        insert_or_update_record(couchdb_url, db_name, username, password, cleaned_record)
                except Exception as e:
                    log.exception(f"Error processing row {index + 2}: {e}")
                    file_processed_successfully = False
        except Exception as file_err:
            log.exception(f"Error processing file '{file_name}': {file_err}")
            file_processed_successfully = False

        try:
            subprocess.run(["python3", "per_leave_update.py"], check=True) ####
            log.info("Called per_leave_update.py successfully.")
            subprocess.run(["python3", "per_account_sme.py"], check=True)
            log.info("Called per_account_sme.py successfully.")
            subprocess.run(["python3", "per_time_spent.py"], check=True)
            log.info("Called per_time_spent.py successfully.")

            if file_processed_successfully:
                subprocess.run(["python3", "model.py"], check=True, env=env)
                log.info("Called model.py successfully.")
                archive_path = os.path.join(archive_dir, file_name)
                shutil.move(file_path, archive_path)
                log.info(f"Successfully processed and moved to archive: {file_name}")
        except subprocess.CalledProcessError as e:
            log.error(f"Script failed: {e}")
    else:
        log.info(f"No RPA extracted files in the target folder to process")

    # Close log handlers
    for handler in log.handlers:
        handler.close()
        log.removeHandler(handler)

    # Email logic replaced with print
    log_files = glob.glob(os.path.join(log_dir, "smart_triage_log_*.txt"))
    if log_files:
        print("Sending the email")
        sender = "Smart Triage <no-reply@ibm.com>"
        #recipients = ["lavanya.m8@ibm.com"]
        #cc = ["lavanya.m8@ibm.com"]
        recipients = ["nabanuri@in.ibm.com"]
        cc = ["raghavkrishnamurthy@in.ibm.com", "pgupta06@in.ibm.com"]
        subject = f"Smart Triage Log File Run Details - {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %I:%M %p')}"
        body = "***This is an automatically generated email, please do not reply***"

        def send_mail(sender, to_list, cc_list, subject, body, attachments, smtp_server='na.relay.ibm.com'):
            msg = EmailMessage()
            msg["From"] = sender
            msg["To"] = ", ".join(to_list)
            msg["Cc"] = ", ".join(cc_list)
            msg["Subject"] = subject
            msg.set_content(body)
            for file_path in attachments:
                with open(file_path, 'rb') as f:
                    msg.add_attachment(f.read(), maintype="text", subtype="plain", filename=os.path.basename(file_path))
            with smtplib.SMTP(smtp_server, 25) as server:
                server.send_message(msg)

        try:
            send_mail(sender, recipients, cc, subject, body, log_files)
            for file in log_files:
                shutil.move(file, os.path.join(log_dir, os.path.basename(file)))
            print("Email sent and log files archived.")
        except Exception as e:
            print(f"Error sending email or moving logs: {e}")
    else:
        print("No log files found to send.")

if __name__ == "__main__":
    couchdb_url = "http://9.20.195.22:5984"
    db_name = "per_cases_to_triage_master"
    username = "admin"
    password = "admin123"
    folder_path = "/Users/Administrator/Downloads/"

    process_files(folder_path, couchdb_url, db_name, username, password) ####