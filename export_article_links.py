import os
import csv
import configparser

def export_article_links():
    config = configparser.ConfigParser()
    config.read('config.ini')

    articles_path = config.get('PELICAN', 'ARTICLES_PATH')
    site_url = config.get('PELICAN', 'SITE_URL')
    csv_file = config.get('DEFAULT', 'CSV_FILE')

    # 1. Read all existing URLs from the CSV into a set to prevent duplicates.
    existing_urls = set()
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Skip header
            if header:
                try:
                    url_index = [h.lower().strip() for h in header].index('url')
                    for row in reader:
                        if len(row) > url_index:
                            existing_urls.add(row[url_index].strip())
                except ValueError:
                    print("CSV file is missing 'url' column.")
                    return

    # 2. Find all new articles (both Turkish and English) and collect them.
    new_rows_to_append = []
    for root, dirs, files in os.walk(articles_path):
        for filename in files:
            if filename.endswith('.md') or filename.endswith('.rst'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'Status: published' in content:
                        is_english = os.path.basename(root) == 'en' or \
                                     filename.endswith('.en.md') or \
                                     filename.endswith('.en.rst')

                        # Generate slug
                        slug = os.path.splitext(filename)[0]
                        if slug.endswith('.en'):
                            slug = slug[:-3]

                        # Construct the URL based on language
                        if is_english:
                            article_link = f'{site_url}en/{slug}/'
                        else:
                            article_link = f'{site_url}{slug}/'

                        # 3. If the URL is not already in the CSV, add it to our list.
                        if article_link not in existing_urls:
                            # New rows have empty submission statuses
                            new_rows_to_append.append([article_link, '', ''])

    # 4. Append the new rows to the CSV file.
    if new_rows_to_append:
        with open(csv_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(new_rows_to_append)
        print(f'Successfully appended {len(new_rows_to_append)} new article links to {csv_file}')
    else:
        print('No new articles to add.')

if __name__ == '__main__':
    export_article_links()