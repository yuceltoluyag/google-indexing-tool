import configparser
import csv
from bing_indexnow_api_tool import submit_urls
from datetime import datetime

def run_bing_submission():
    config = configparser.ConfigParser()
    config.read('config.ini')
    csv_file = config.get('DEFAULT', 'CSV_FILE')

    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader)
        data = list(reader)

    url_col_index = header.index('url')
    bing_col_index = header.index('bing_last_successful_submission')

    urls_to_submit = []
    indices_to_update = []
    for i, row in enumerate(data):
        if not row[bing_col_index].strip():
            urls_to_submit.append(row[url_col_index])
            indices_to_update.append(i)

    if urls_to_submit:
        print("Submitting URLs to Bing IndexNow...")
        status_code, response_text = submit_urls(urls_to_submit)
        print(f'Bing IndexNow Submission Status Code: {status_code}')
        print(f'Bing IndexNow Response: {response_text}')

        if status_code in [200, 202]:
            submission_time = datetime.now().isoformat()
            for i in indices_to_update:
                data[i][bing_col_index] = submission_time
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(header)
                writer.writerows(data)
            print("CSV file updated with submission times.")

    else:
        print("No new URLs to submit to Bing.")

if __name__ == '__main__':
    run_bing_submission()
