import os
import csv
import argparse
import logging
import configparser
from datetime import datetime
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration & Logging Setup ---
config = configparser.ConfigParser()
config.read('config.ini')

SERVICE_ACCOUNT_FILE = config.get('DEFAULT', 'SERVICE_ACCOUNT_FILE')
CSV_FILE = config.get('DEFAULT', 'CSV_FILE')
SITE_URL = config.get('PELICAN', 'SITE_URL', fallback='https://yuceltoluyag.github.io/')
LOG_FILE = 'google_index_check.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_search_console_service():
    """Authenticates using the service account and returns the Search Console service client."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logging.error(f"Credentials file '{SERVICE_ACCOUNT_FILE}' not found.")
        return None
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('searchconsole', 'v1', credentials=credentials, cache_discovery=False)
        return service
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return None

def inspect_url(service, url):
    """Inspects a single URL using the Google Search Console API."""
    request_body = {
        'siteUrl': SITE_URL,
        'inspectionUrl': url,
        'languageCode': 'tr'
    }
    try:
        response = service.urlInspection().index().inspect(body=request_body).execute()
        result = response.get('inspectionResult', {})
        
        # Parse relevant fields
        index_status = result.get('indexStatusResult', {})
        verdict = index_status.get('verdict', 'UNKNOWN')
        coverage_state = index_status.get('coverageState', 'No data')
        last_crawl = index_status.get('lastCrawlTime', 'Never')
        robots_state = index_status.get('robotsTxtState', 'UNKNOWN')
        indexing_state = index_status.get('indexingState', 'UNKNOWN')
        google_canonical = index_status.get('googleCanonical', 'None')
        
        return {
            'success': True,
            'verdict': verdict,
            'coverage_state': coverage_state,
            'last_crawl': last_crawl,
            'robots_state': robots_state,
            'indexing_state': indexing_state,
            'google_canonical': google_canonical
        }
    except HttpError as error:
        error_details = error.reason
        if error.resp.status == 403:
            logging.error("403 Forbidden: Please ensure the 'Google Search Console API' is enabled in your Google Cloud Project "
                          "and that your Service Account has sufficient permissions in Google Search Console for this property.")
        else:
            logging.error(f"API Error inspecting {url}: {error}")
        return {'success': False, 'error': error_details}
    except Exception as e:
        logging.error(f"Error inspecting {url}: {e}")
        return {'success': False, 'error': str(e)}

def read_csv_data():
    """Reads the CSV file and returns the header and rows."""
    if not os.path.exists(CSV_FILE):
        logging.error(f"CSV file '{CSV_FILE}' not found.")
        return [], []
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
            rows = [row for row in reader]
            return header, rows
        except StopIteration:
            return [], []

def write_csv_data(header, rows):
    """Writes back the data to CSV."""
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description="Check Google Indexation status of URLs using the Search Console URL Inspection API.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--url', help="Check indexing status of a single specific URL.")
    group.add_argument('--newest', type=int, help="Check indexation status for N newest URLs in the CSV.")
    group.add_argument('--bulk', action='store_true', help="Check indexation status for all URLs that have not been checked or are pending.")
    
    args = parser.parse_args()
    
    service = get_search_console_service()
    if not service:
        logging.critical("Could not initialize Google Search Console client. Exiting.")
        return

    if args.url:
        print(f"\n[INFO] Inspecting URL: {args.url}")
        res = inspect_url(service, args.url)
        if res['success']:
            print("-" * 50)
            print(f"Status: [{res['verdict']}]")
            print(f"Details: {res['coverage_state']}")
            print(f"Last Crawl Time: {res['last_crawl']}")
            print(f"Robots.txt Status: {res['robots_state']}")
            print(f"Indexing Allowed: {res['indexing_state']}")
            print(f"Google Canonical: {res['google_canonical']}")
            print("-" * 50)
        else:
            print(f"[ERROR] Failed to inspect URL: {res.get('error')}")
            
    else:
        header, rows = read_csv_data()
        if not header:
            return
        
        # Ensure target columns exist
        if 'google_index_status' not in header:
            header.append('google_index_status')
        if 'google_index_details' not in header:
            header.append('google_index_details')
        if 'google_last_crawl' not in header:
            header.append('google_last_crawl')
            
        url_idx = header.index('url')
        status_idx = header.index('google_index_status')
        details_idx = header.index('google_index_details')
        crawl_idx = header.index('google_last_crawl')
        
        # Adjust rows to match new headers length if needed
        for row in rows:
            while len(row) < len(header):
                row.append('')
                
        to_inspect = []
        if args.newest:
            # Filter valid URLs
            valid_rows = [(i, r) for i, r in enumerate(rows) if r[url_idx].startswith('http')]
            to_inspect = valid_rows[-args.newest:]
            logging.info(f"Checking indexation status for the {len(to_inspect)} newest URLs...")
        elif args.bulk:
            # Check rows that don't have google_index_status or have failed/unknown/error
            to_inspect = [(i, r) for i, r in enumerate(rows) if r[url_idx].startswith('http') and (not r[status_idx] or r[status_idx] in ['UNKNOWN', 'FAIL', 'ERROR'])]
            # Limit bulk checks to 100 per run to respect Search Console quota easily
            to_inspect = to_inspect[:100]
            logging.info(f"Checking indexation status for {len(to_inspect)} pending URLs (bulk limit 100)...")

        if not to_inspect:
            logging.info("No URLs to check.")
            return
            
        success_count = 0
        for count, (original_index, row) in enumerate(to_inspect):
            url = row[url_idx]
            logging.info(f"[{count+1}/{len(to_inspect)}] Inspecting {url}...")
            res = inspect_url(service, url)
            if res['success']:
                rows[original_index][status_idx] = res['verdict']
                rows[original_index][details_idx] = res['coverage_state']
                rows[original_index][crawl_idx] = res['last_crawl']
                success_count += 1
                
                logging.info(f"  -> Result: [{res['verdict']}] | {res['coverage_state']}")
            else:
                rows[original_index][status_idx] = 'ERROR'
                rows[original_index][details_idx] = res.get('error', 'API error')
                logging.error(f"  -> Failed: {res.get('error')}")
                # If we hit configuration errors, let's stop immediately
                if "403" in str(res.get('error')) or "Search Console API has not been used" in str(res.get('error')):
                    logging.error("Exiting due to API permissions/configuration error.")
                    break
                    
            # Small delay to respect API quota
            time.sleep(1)
            
        write_csv_data(header, rows)
        logging.info(f"Completed checking. Successfully updated {success_count} records in CSV.")

if __name__ == '__main__':
    main()
