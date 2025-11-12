import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
import csv
import os
from datetime import datetime
import time
import configparser
import argparse
import logging

# --- Configuration & Logging Setup ---
config = configparser.ConfigParser()
config.read('config.ini')

SERVICE_ACCOUNT_FILE = config.get('DEFAULT', 'SERVICE_ACCOUNT_FILE')
CSV_FILE = config.get('DEFAULT', 'CSV_FILE')
LOG_FILE = config.get('DEFAULT', 'LOG_FILE')
API_URL = config.get('API', 'URL')
REQUEST_DELAY_SECONDS = config.getint('API', 'REQUEST_DELAY_SECONDS')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Helper Functions ---

def check_files():
    """Checks for the existence of necessary files."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logging.error(f"'{SERVICE_ACCOUNT_FILE}' not found. Please ensure the file is in the root directory.")
        return False
    if not os.path.exists(CSV_FILE):
        logging.error(f"'{CSV_FILE}' not found. Please ensure the file is in the root directory.")
        return False
    return True

def read_csv_data():
    """Reads the CSV file and returns the header and data."""
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
            if header[0].lower().strip().replace(' ', '_') != 'url':
                header = ['url', 'last_successful_submission']
                file.seek(0)
                data = [row for row in reader]
            else:
                data = [row for row in reader]

            processed_data = []
            for row in data:
                if not row: continue
                while len(row) < 2:
                    row.append('')
                processed_data.append(row)

            return header, processed_data
        except StopIteration:
            return ['url', 'last_successful_submission'], []

def write_csv_data(header, data):
    """Writes data to the CSV file."""
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(data)

def process_urls(notification_type, header, data):
    """Processes URLs, sends them to the API, and updates the CSV."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/indexing'])
        authed_session = AuthorizedSession(credentials)
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return

    url_col_index = header.index('url')
    status_col_index = header.index('last_successful_submission')

    submitted_count = 0
    submission_limit = 200

    for i, row in enumerate(data):
        if submitted_count >= submission_limit:
            logging.info(f"Submission limit of {submission_limit} reached for this run. Remaining URLs will be processed next time.")
            break

        url = row[url_col_index].strip()
        last_submission = row[status_col_index].strip()

        if not url.startswith('http'):
            logging.warning(f"Skipping invalid entry: {url}")
            continue

        if last_submission:
            # This URL has been processed before, so we skip it.
            continue

        logging.info(f"Submitting URL ({submitted_count + 1}/{submission_limit}): {url}")
        content = {'url': url, 'type': notification_type}
        
        try:
            response = authed_session.post(API_URL, json=content)
            status_code = response.status_code
            response_json = response.json()

            if status_code == 200:
                submission_time = datetime.now().isoformat()
                data[i][status_col_index] = submission_time
                submitted_count += 1
                logging.info(f"  -> Success (200): URL submission successful. Updated CSV record.")
                write_csv_data(header, data) # Save after each success
            else:
                error_message = response_json.get('error', {}).get('message', 'Unknown error')
                logging.error(f"  -> Failed ({status_code}): {error_message}")
                if status_code == 429:
                    logging.error("  -> Rate limit exceeded (429). Stopping for this run.")
                    break # Stop processing immediately

        except Exception as e:
            logging.error(f"  -> An error occurred during submission: {e}")
        
        time.sleep(REQUEST_DELAY_SECONDS)

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit URLs to the Google Indexing API.")
    parser.add_argument(
        "operation",
        choices=['PUBLISH', 'DELETED'],
        help="The operation type: PUBLISH for URL_UPDATED or DELETED for URL_DELETED."
    )
    args = parser.parse_args()

    notification_type = "URL_UPDATED" if args.operation == "PUBLISH" else "URL_DELETED"

    if check_files():
        header, data = read_csv_data()
        
        if 'last_successful_submission' not in header:
            header.append('last_successful_submission')

        process_urls(notification_type, header, data)
        write_csv_data(header, data)
        logging.info("\nProcessing complete.")