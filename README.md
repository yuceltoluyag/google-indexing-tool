# Google & Bing Indexing API Tools

This project contains a set of Python scripts to interact with the Google Indexing API and the Bing IndexNow API. It allows you to notify both search engines of new, updated, or deleted pages on your site.

## Files

- `google_indexing_api_tool.py`: A command-line tool to send indexing requests to the Google API.
- `bing_indexnow_api_tool.py`: A module for sending indexing requests to the Bing IndexNow API.
- `run_bing_submission.py`: A script to execute the Bing submission process.
- `export_article_links.py`: A script to export article links from a Pelican blog system to a CSV file.
- `config.ini`: The configuration file for the project.
- `article_links.csv`: A CSV file containing the links to be indexed. It tracks submission status for both Google and Bing.
- `service-account.json`: Service account credentials for authenticating with the Google API. **Note:** This file should be kept private.
- `your-api-key.txt`: Your Bing API key file. The name is your key. **Note:** This file should be kept private.
- `indexing.log`: Log file for recording submission activities.

## Configuration

Before running the scripts, you need to set up the `config.ini` file:

- **[DEFAULT]**: Contains paths for `SERVICE_ACCOUNT_FILE`, `CSV_FILE`, and `LOG_FILE`.
- **[API]**: `URL` for the Google Indexing API and `REQUEST_DELAY_SECONDS` to avoid hitting rate limits.
- **[PELICAN]**: `ARTICLES_PATH` (path to your Pelican content) and `SITE_URL` for constructing links.
- **[BING]**: Contains your `API_KEY` and `KEY_LOCATION` URL for the Bing IndexNow API.

## Setup

### 1. Common Setup

a.  **Create a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

b.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

### 2. Google API Setup

a. **Enable the Indexing API:** - Go to the [Google Cloud Console](https://console.cloud.google.com/apis/library/indexing.googleapis.com) and enable the Indexing API.

b. **Create a Service Account:** - Go to the [Service Accounts page](https://console.cloud.google.com/iam-admin/serviceaccounts) and create a new service account.

c. **Generate a JSON Key:** - From the service account's "Manage keys" section, create a new JSON key. Rename the downloaded file to `service-account.json` and place it in the project root.

d. **Grant Access in Google Search Console:** - In your site's [Google Search Console](https://search.google.com/search-console/users), add the service account's email address as a user with **Owner** permission.

### 3. Bing IndexNow Setup

a. **Generate an API Key:** - You can generate a key using Bing Webmaster Tools or by simply creating a UUID. The key should be a hexadecimal string.

b. **Create the Key File:** - Create a text file in the root of your project. The name of the file must be your API key with a `.txt` extension (e.g., `acf21962677a48049a6a234640504902.txt`).
   - The content of this file must be the API key itself.

c. **Host the Key File:** - This key file must be publicly accessible on your web server at the root. For example: `https://your-site.com/your-api-key.txt`.

d. **Update `config.ini`:** - Set the `API_KEY` and `KEY_LOCATION` in the `[BING]` section of your `config.ini` file.

## Usage

### Step 1: Generate URL List

Run the `export_article_links.py` script. This will find all your published articles and create/update the `article_links.csv` file. This file has columns to track submission status for both Google and Bing.

```bash
python export_article_links.py
```

### Step 2: Submit URLs

You can now submit the new URLs to Google and/or Bing.

**To submit to Google:**

This script submits URLs one by one, with a delay between each, as required by the Google API.

```bash
# To publish/update URLs
python google_indexing_api_tool.py PUBLISH

# To remove URLs
python google_indexing_api_tool.py DELETED
```

**To submit to Bing:**

This script submits all new URLs in a single batch request, which is the preferred method for the IndexNow protocol.

```bash
python run_bing_submission.py
```

The scripts will only submit URLs that have not been successfully submitted before and will log their progress to the console and to the `indexing.log` file.

## API Limits and Responsibility

**IMPORTANT:** You are responsible for using these tools in accordance with the terms of service of each search engine.

-   **Google Indexing API:** Has a daily usage quota of **200 URLs per day**. The script submits URLs one by one to respect this.
-   **Bing IndexNow API:** Allows up to **10,000 URLs per submission**. Our script sends all new URLs in a single batch.

**Warning:** Do not modify the scripts to bypass these limits or submit URLs excessively. Abusing the APIs by sending too many requests or submitting URLs that have not changed can lead to your site being temporarily or permanently flagged as spam by the search engines. **The responsibility for proper use and any consequences of misuse lies entirely with you.**
