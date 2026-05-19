# Google & Bing Indexing API Tools

This project is a modern, object-oriented Python CLI utility designed to manage search engine indexation (Google Indexing API, Google Search Console URL Inspection API, and Bing IndexNow API). It parses your Pelican blog articles, tracks index status in a local CSV database, and automates submissions while enforcing daily limits and cooldown periods.

## System Architecture

The tool is structured as a modular Python package located in `src/indexing_tool/`:
- `config.py`: Configuration loading and parsing using Pydantic.
- `models.py`: Pydantic data schemas representing article records and cooldown rules.
- `csv_manager.py`: Encapsulated database operations on `article_links.csv`.
- `google_client.py`: Client wrappers for Search Console and Google Indexing API.
- `bing_client.py`: Batch IndexNow client wrapper.
- `pelican_exporter.py`: Exporter extracting published post URLs.
- `orchestrator.py`: Business logic layer directing workflows.
- `main.py`: The single CLI entry point for the entire application.

## Configuration (`config.ini`)

Before executing commands, configure your settings in `config.ini`:

```ini
[PELICAN]
ARTICLES_PATH = content/articles
SITE_URL = https://yourdomain.com/

[DEFAULT]
CSV_FILE = article_links.csv
SERVICE_ACCOUNT_FILE = service-account.json
LOG_FILE = indexing.log

[API]
URL = https://indexing.googleapis.com/v3/urlNotifications:publish
REQUEST_DELAY_SECONDS = 10
COOLDOWN_DAYS = 3

[BING]
API_KEY = your_indexnow_api_key
KEY_LOCATION = https://yourdomain.com/your_indexnow_api_key.txt
```

- **COOLDOWN_DAYS**: Number of days to shield a page from being re-submitted to Google Indexing API if it is not yet indexed.

## Installation & Setup

### 1. Common Setup

a. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

b. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 2. Google API Setup

a. **Enable the Indexing API:** Go to the [Google Cloud Console](https://console.cloud.google.com/apis/library/indexing.googleapis.com) and enable the Indexing API.

b. **Create a Service Account:** Go to the [Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts) and create a new service account.

c. **Generate a JSON Key:** From the service account's "Manage keys" section, create a new JSON key. Save it as `service-account.json` (or reference its name under `SERVICE_ACCOUNT_FILE` in `config.ini`) and place it in the project root.

d. **Grant Access in Google Search Console:** In your site's [Google Search Console](https://search.google.com/search-console/users), add the service account's email address as a user with **Owner** permission.

e. **Enable the Search Console API:** For the indexing status checker CLI tool to work, also go to the [Google Search Console API](https://console.developers.google.com/apis/api/searchconsole.googleapis.com/overview) and enable it for the same Google Cloud project.

### 3. Bing IndexNow Setup

a. **Generate an API Key:** You can generate a key using Bing Webmaster Tools or by simply creating a UUID. The key should be a hexadecimal string.

b. **Create the Key File:** Create a text file in the root of your project. The name of the file must be your API key with a `.txt` extension (e.g., `your_api_key.txt`). The content of this file must be the API key itself.

c. **Host the Key File:** This key file must be publicly accessible on your web server at the root. For example: `https://yourdomain.com/your_api_key.txt`.

d. **Update config.ini:** Set the `API_KEY` and `KEY_LOCATION` in the `[BING]` section of your `config.ini` file.

## 🚀 Step-by-Step Workflow for Beginners

If you are running the project for the first time, you should run the commands in the following sequence:

### Step 1: Export Pelican Articles to the CSV Database
First, scan your published articles and add them to your tracking database (`article_links.csv`):
```bash
python main.py export
```
*This command creates or updates the `article_links.csv` file in the project root.*

### Step 2: Query Existing Pages' Google Index Status (Bulk Inspection)
To avoid wasting Google API quotas, perform a bulk check to query which pages are already indexed by Google:
```bash
python main.py inspect --bulk --limit 100
```
*This marks already-indexed pages as `PASS`, shielding them from being scanned or submitted again in subsequent steps.*

### Step 3: Submit New URLs to Bing IndexNow
Submit all your new or updated URLs to Bing in a single batch request:
```bash
# Preview the submission (optional dry-run):
python main.py bing --dry-run

# Perform the actual submission:
python main.py bing
```
*Since Bing IndexNow supports batch submissions, all pending URLs are sent efficiently in a single API call.*

### Step 4: Run the Smart Google Indexing Workflow (Daily Routine)
Detect non-indexed pages and submit only the pending ones (status `NEUTRAL`/`FAIL`) to the Google Indexing API, respecting the cooldown rules:
```bash
# Run a dry-run simulation:
python main.py smart --dry-run --limit 10

# Start the live status check and submission loop:
python main.py smart --limit 50
```
*This command checks GSC status, submits pending pages to the Indexing API, and initiates a 3-day cooldown timer for submitted pages to prevent repeated checks and conserve API quotas.*

---

## CLI Usage Guide

All actions are performed via `main.py`.

### 1. Export Pelican Articles
Find all published posts in the Pelican articles folder and append new ones to the CSV:
```bash
python main.py export
```

### 2. Inspect Google Index Status
Query Search Console for actual index status of pages:

- **Single URL Check**:
  ```bash
  python main.py inspect --url https://yuceltoluyag.github.io/my-post/
  ```
- **Newest N URLs Check**:
  ```bash
  python main.py inspect --newest 10
  ```
- **Bulk Check**:
  Inspects pending (non-indexed) URLs up to the limit (default 100):
  ```bash
  python main.py inspect --bulk --limit 50
  ```

### 3. Smart Google Indexing (Recommended)
This workflow inspects the status of pending URLs, and only triggers Google Indexing API submissions for pages that are not yet indexed (`NEUTRAL`/`FAIL`), while honoring the defined cooldown days.

- **Simulation (Dry Run)**:
  ```bash
  python main.py smart --dry-run --limit 10
  ```
- **Submit Indexing API**:
  ```bash
  python main.py smart --limit 20
  ```

### 4. Bing IndexNow Submission
Submit all new URLs (that haven't been submitted to Bing yet) in a single batch:

- **Simulation (Dry Run)**:
  ```bash
  python main.py bing --dry-run
  ```
- **Execute Submission**:
  ```bash
  python main.py bing
  ```

---

## API Limits and Responsibility

**IMPORTANT:** You are responsible for using these tools in accordance with the terms of service of each search engine.

- **Google Indexing API:** Has a daily usage quota of **200 URLs per day**. The script submits URLs one by one to respect this.
- **Bing IndexNow API:** Allows up to **10,000 URLs per submission**. Our script sends all new URLs in a single batch.

**Warning:** Do not modify the scripts to bypass these limits or submit URLs excessively. Abusing the APIs by sending too many requests or submitting URLs that have not changed can lead to your site being temporarily or permanently flagged as spam by the search engines. **The responsibility for proper use and any consequences of misuse lies entirely with you.**
